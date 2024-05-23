import time
import torch
import telebot
import gc
import json
import logging
import os

from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler
from jinja2 import Template
from telebot.types import ReplyParameters

from exllamav2 import (
    ExLlamaV2,
    ExLlamaV2Config,
    ExLlamaV2Cache_8bit,
    ExLlamaV2Tokenizer,
)

from exllamav2.generator import (
    ExLlamaV2StreamingGenerator,
    ExLlamaV2Sampler
)

# INITIALISE LOGGER
def create_logger():
    load_dotenv()
    path = os.getenv('LOGGERPATH')
    logger = logging.getLogger(__name__)
    handler = RotatingFileHandler(path, maxBytes=2000000, backupCount=5)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(fmt='%(asctime)s: %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    return logger
logger = create_logger()

# FUNCTIONS
def clear_gpu_cache():
    gc.collect()
    with torch.no_grad():
        torch.cuda.empty_cache()
    logger.info("GPU cache cleared")

class ReplyTypes:
    CODE = "code"
    TEXT = "text"
    NEWTEXT = "newtext"
    RESET = "reset"

def load_bot():
    start = time.time()
    logger.info("Bot loading...")
    bot = telebot.TeleBot(os.getenv('APIKEY'))
    bot.llm = Llama3()
    logger.info(f"Bot loaded in {round(time.time() - start, 3)} seconds")
    return bot

class Llama3:

    def __init__(self):
        load_dotenv()
        self.config = ExLlamaV2Config()
        self.config.model_dir = os.getenv('LLMPATH')
        self.config.prepare()
        self.config.max_batch_size = batch_size = 1
        self.model = ExLlamaV2(self.config)
        self.cache = ExLlamaV2Cache_8bit(self.model, lazy = True, batch_size = batch_size)
        self.model.load_autosplit(self.cache)
        self.tokenizer = ExLlamaV2Tokenizer(self.config)
        self.settings = ExLlamaV2Sampler.Settings()
        self.settings.temperature = 0.85
        self.settings.top_k = 50
        self.settings.top_p = 0.8
        self.settings.token_repetition_penalty = 1.05
        self.stop_conditions = [128009, self.tokenizer.eos_token_id]

    def start_generator(self, input_ids):
        start = time.time()
        self.generator = ExLlamaV2StreamingGenerator(self.model, self.cache, self.tokenizer)
        clear_gpu_cache()
        self.generator.warmup()
        self.generator.set_stop_conditions(self.stop_conditions)
        self.generator.begin_stream_ex(input_ids, self.settings,  decode_special_tokens=True)
        logger.info(f"Generator initialised in {round(time.time() - start, 3)} seconds")
        return self.generator
    
    def apply_prompt_template(self, messages, role="assistant"):
        template = Template(
            "{% set loop_messages = messages %}{% for message in loop_messages %}{% set content = '<|start_header_id|>' + message['role'] + '<|end_header_id|>\n\n'+ message['content'] | trim + '<|eot_id|>' %}{% if loop.index0 == 0 %}{% set content = '<|begin_of_text|>' + content %}{% endif %}{{ content }}{% endfor %}{{ '<|start_header_id|>' + role + '<|end_header_id|>\n\n' }}"
            )
        return template.render(messages=messages, role=role)

def send_message_wrapper(bot, msg, content):
    try:
        bot.send_message(msg.chat.id, content,  reply_parameters=ReplyParameters(
            message_id=msg.id, chat_id=msg.chat.id, allow_sending_without_reply=True),  parse_mode="Markdown")
    except Exception as e:
        logger.warning("Message failed to send with Markdown. Trying non-markdown.")
        bot.send_message(msg.chat.id, content,  reply_parameters=ReplyParameters(
            message_id=msg.id, chat_id=msg.chat.id, allow_sending_without_reply=True))


def send_chunked_response_from_prompt(bot, input_ids, msg, max_new_tokens = 1024, Chunk_size = 512) -> str:
    
    generator = bot.llm.start_generator(input_ids)
    clear_gpu_cache()
    all_chunks = []
    output = []
    generated_tokens = 0
    while True:
        chunk, eos, _ = generator.stream()
        generated_tokens += 1
        print(chunk, end = "")
        output.append(chunk)
        
        if generated_tokens > 0 and generated_tokens % Chunk_size == 0:
            completed = "".join(output)
            all_chunks.append(completed)
            send_message_wrapper(bot, msg, completed)
            output = []

        if eos or generated_tokens == max_new_tokens:
            completed = "".join(output)
            if completed:
                all_chunks.append(completed)
                send_message_wrapper(bot, msg, completed)
            break
    
    
    return "".join(all_chunks)

def get_conversation_block_from_reply_type(reply_type, msg):
    if reply_type == ReplyTypes.TEXT:
        conv = get_conversation(msg)
        
        block = {
            "role": "user", "content": msg.text
        }
        conv.append(block)
    elif reply_type == ReplyTypes.NEWTEXT:
        conv = get_conversation(msg)[0:1]
        block = {
            "role": "user", "content": msg.text
        }
        conv.append(block)

    elif reply_type == ReplyTypes.RESET:
        assert("role" in msg.__dict__ and msg.role)
        edited = "I, the user am unhappy with your current personality and wants to change the system prompt. \
            Say your last words. After your next reply, your new system prompt will be:"
        artificial_prompt = edited + msg.text
        conv = get_conversation(msg)
        block = {
            "role": "user", "content": artificial_prompt
        }
        conv.append(block)
    return conv


def execute_task(bot, msg, reply_type, max_len=8100):
    logger.info(f"Begin execution of task type {reply_type}")
    # time to reply
    start = time.time()
    conversation = get_conversation_block_from_reply_type(reply_type, msg)
    desired_role = get_role(msg)
    stringified_conversation = bot.llm.apply_prompt_template(conversation, role=desired_role)
    input_ids = bot.llm.tokenizer.encode(stringified_conversation)
    while len(input_ids) >= max_len:
        logger.info("Conversation too long, truncating conversation.")
        conversation = conversation[0:1] + conversation[2:]
        stringified_conversation = bot.llm.apply_prompt_template(conversation)
        input_ids = bot.llm.tokenizer.encode(stringified_conversation)

    final = send_chunked_response_from_prompt(bot, input_ids, msg)
    
    reply = {
        "role": f"{desired_role}", "content": final
    }
    conversation.append(reply)
    if reply_type == ReplyTypes.RESET:
        new_conversation = [
            {
                "role": "system", "content": msg.text
            }
        ]
        store_conversation(msg, new_conversation)
    else:
        store_conversation(msg, conversation)
    store_role(msg, desired_role)
    logger.info(f"Task executed in {round(time.time() - start, 3)} seconds.")

def get_default_empty_conv():
    return [
        {
        "role": "system",
        "content": "You are a helpful AI assistant."
        }
    ]

def get_conversation(msg, path='./app/data/conversations.json'):
    if not os.path.exists(path):
        logger.info(f"Creating conversations.json file.")
        with open(path, "w") as f:
            json.dump({}, f, indent=4)

    with open(path) as f:
        data = json.load(f)
        chat_id = str(msg.chat.id)
        if chat_id not in data:
            logger.info(f"User does not exist, retrieving default conversation.")
            data[chat_id] = get_default_empty_conv()
    
    conv = data[chat_id]
    logger.info(f"Conversation retrieved successfully for id {msg.chat.id}")
    return conv

def store_conversation(msg, conv, path='./app/data/conversations.json'):
    logger.info(f"Storing conversation for id {msg.chat.id}")
    with open(path) as f:
        data = json.load(f)
    chat_id = str(msg.chat.id)
    data[chat_id] = conv
    with open(path, 'w') as f:
        json.dump(data, f, indent=4)
    logger.info(f"Conversation for id {msg.chat.id} stored successfully.")


def get_role(msg, path='./app/data/roles.json'):
        
    if not os.path.exists(path):
        logger.info(f"Creating roles.json file.")
        with open(path, "w") as f:
            json.dump({}, f, indent=4)

    if "role" in msg.__dict__ and msg.role:
        return msg.role
    
    with open(path) as f:
        data = json.load(f)
        chat_id = str(msg.chat.id)
        if chat_id not in data:
            logger.info(f"User does not exist, retrieving default role.")
            data[chat_id] = "assistant"
    desired_role = data[chat_id]
    logger.info(f"Desired role retrieved successfully for id {msg.chat.id}")
    return desired_role


def store_role(msg, role, path='./app/data/roles.json'):
    logger.info(f"Storing role for id {msg.chat.id}")
    with open(path) as f:
        data = json.load(f)
    chat_id = str(msg.chat.id)
    data[chat_id] = role
    with open(path, 'w') as f:
        json.dump(data, f, indent=4)
    logger.info(f"Desired role for id {msg.chat.id} stored successfully.")