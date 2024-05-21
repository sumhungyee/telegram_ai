
import torch
import telebot
from telebot.types import ReplyParameters
import gc
import json
import os
from jinja2 import Template
from dotenv import load_dotenv

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

def clear_cache():
    gc.collect()
    with torch.no_grad():
        torch.cuda.empty_cache()

class ReplyTypes:
    CODE = "code"
    TEXT = "text"
    RESET = "reset"

def load_bot():
    
    bot = telebot.TeleBot(os.getenv('APIKEY'))
    bot.llm = Llama3()
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
        self.generator = ExLlamaV2StreamingGenerator(self.model, self.cache, self.tokenizer)
        clear_cache()
        self.generator.warmup()
        self.generator.set_stop_conditions(self.stop_conditions)
        
        self.generator.begin_stream_ex(input_ids, self.settings,  decode_special_tokens=True)
        return self.generator
    
    def apply_prompt_template(self, messages):
        template = Template("{% for message in messages %}{{'<|im_start|>' + message['role'] + '\n' + message['content'] + '<|im_end|>' + '\n'}}{% endfor %}{{ '<|im_start|>assistant\n' }}")
        return template.render(messages=messages)



def send_chunked_response_from_prompt(bot, input_ids, msg, max_new_tokens = 4096, Chunk_size = 512) -> str:
    
    generator = bot.llm.start_generator(input_ids)
    clear_cache()

    output = []
    generated_tokens = 0
    while True:
        chunk, eos, _ = generator.stream()
        generated_tokens += 1
        print(chunk, end = "")
        output.append(chunk)
        if generated_tokens > 0 and generated_tokens % Chunk_size == 0:
            bot.send_message(msg.chat.id, "".join(output),  reply_parameters=ReplyParameters(message_id=msg.id, chat_id=msg.chat.id, allow_sending_without_reply=True, parse_mode="Markdown" ))
            output = []

        if eos or generated_tokens == max_new_tokens:
            bot.send_message(msg.chat.id, "".join(output), reply_parameters=ReplyParameters(message_id=msg.id, chat_id=msg.chat.id, allow_sending_without_reply=True, parse_mode="Markdown"))
            break
    return "".join(output)


def execute_task(bot, conversation, msg, reply_type, max_len=8100):
    
    # time to reply
    stringified_conversation = bot.llm.apply_prompt_template(conversation)
    input_ids = bot.llm.tokenizer.encode(stringified_conversation)
    while len(input_ids) >= max_len:
        conversation = conversation[0:1] + conversation[2:]
        stringified_conversation = bot.llm.apply_prompt_template(conversation)
        input_ids = bot.llm.tokenizer.encode(stringified_conversation)

    final = send_chunked_response_from_prompt(bot, input_ids, msg)
    reply = {
        "role": "assistant", "content": final
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

def get_default_empty_conv():
    return [
        {
        "role": "system",
        "content": "You are an intelligent assistant who tries its best in assisting the user"
        }
    ]

def get_conversation(msg, path='./app/data/sysprompt.json'):
    with open(path) as f:
        data = json.load(f)
        chat_id = str(msg.chat.id)
        if chat_id not in data:
            data[chat_id] = get_default_empty_conv()
        
    return data[chat_id]

def store_conversation(msg, conv, path='./app/data/sysprompt.json'):
    with open(path) as f:
        data = json.load(f)
    chat_id = str(msg.chat.id)
    data[chat_id] = conv
    with open(path, 'w') as f:
        json.dump(data, f, indent=4)