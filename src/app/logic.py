import time
import telebot
import json
import os

from app.agents import *
from app.utils import *


from telebot.types import ReplyParameters

# FUNCTIONS


def load_bot():
    start = time.time()
    logger.info("Bot loading...")
    bot = telebot.TeleBot(os.getenv('APIKEY'))
    bot.llm = Llama3()
    logger.info(f"Bot loaded in {round(time.time() - start, 3)} seconds")
    return bot


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
            print()
            break
    
    
    return "".join(all_chunks)

def get_conversation_block_from_reply_type(reply_type, msg):
    if reply_type != ReplyTypes.RESET:

        conv = get_conversation(msg) if reply_type not in (ReplyTypes.NEWTOOLTEXT, ReplyTypes.NEWTEXT) else get_conversation(msg)[0:1]
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
    
    else:
        raise Exception("Unknown reply type!")

    return conv


def execute_task(bot, msg, reply_type, max_len=8100):
    logger.info(f"Begin execution of task type {reply_type}")
    # time to reply
    start = time.time()
    conversation = get_conversation_block_from_reply_type(reply_type, msg)
    desired_role = get_role(msg)
    
    # Truncate long conversations
    stringified_conversation = bot.llm.apply_prompt_template(conversation, role=desired_role)
    input_ids = bot.llm.tokenizer.encode(stringified_conversation)
    input_ids, conversation = truncate_conversation(input_ids, conversation, bot.llm)

    assert(conversation[-1]["role"] == "user")
 
    # Perform websearch if needed
    if reply_type in (ReplyTypes.TOOLTEXT, ReplyTypes.NEWTOOLTEXT):
        logger.info(repr(f"Websearch needed for request: {msg.text}"))
        adapted_conversation = search_generate_pipeline(bot.llm, conversation)
        stringified_adapted_conversation = bot.llm.apply_prompt_template(adapted_conversation, role=desired_role)
        input_ids = bot.llm.tokenizer.encode(stringified_adapted_conversation)
        input_ids, _ = truncate_conversation(input_ids, adapted_conversation, bot.llm)
        
    # send message
    final = send_chunked_response_from_prompt(bot, input_ids, msg)
    
    # storing changes
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