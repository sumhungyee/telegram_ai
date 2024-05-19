from src.app.agents import *
from src.app.utils import *

import json

from telebot.types import InputFile
from queue import Queue


import threading
import os


COMMANDS = ["/startchat", "/startcode", "/cont", "/setsystemprompt"]

bot = load_bot()
queue = Queue()
event = threading.Event()
def answer_from_queue():
    while not event.is_set():
        if queue.qsize() >= 1:
            conversation, reply_type, id = queue.get()
            execute_task(bot, conversation, reply_type, id)

answerer=threading.Thread(target=answer_from_queue)
answerer.start()
    
def get_conversation(path='./app/data/conversation.json'):
    with open(path) as f:
        data = json.load(f)
    return data

def store_truncated_conversation(data, path='./app/data/conversation.json'):
    new_data = truncate(data, bot.tok, get_llama3_prompt_template_per_msg)
    with open(path, 'w') as f:
        json.dump(new_data, f)


@bot.message_handler(commands = ["startchat"])
def start_chat(msg):
    msg.text = msg.text[len(COMMANDS[0]):]
        

    data = get_conversation()
    new = data[:1]
    block = {
        "role": "user", "content": msg.text
    }
    new.append(block)
    store_truncated_conversation(new)
  
    queue.put((new, ReplyTypes.TEXT, msg.chat.id))
  

@bot.message_handler(commands = ["cont"])
def continue_chat(msg):
    msg.text = msg.text[len(COMMANDS[2]):]

    data = get_conversation()
    block = {
        "role": "user", "content": msg.text
    }
    data.append(block)
    store_truncated_conversation(data)

    queue.put((data, ReplyTypes.TEXT, msg.chat.id))



@bot.message_handler(commands = ["setsystemprompt"])
def set_system_prompt(msg):
   
    edited = "I, the user am unhappy with your current personality and wants to change the system prompt. Say your last words. After your next reply, your new system prompt will be:"
    new_prompt = msg.text[len(COMMANDS[3]):]
    msg.text = edited + new_prompt

    data = get_conversation()
    block = {
        "role": "user", "content": msg.text
    }
    data.append(block)
    queue.put((data, ReplyTypes.TEXT, msg.chat.id))
    new_data = [
        {
            "role": "system", "content": new_prompt
        }
    ]
    store_truncated_conversation(new_data)


bot.infinity_polling(timeout = 10, long_polling_timeout=5)