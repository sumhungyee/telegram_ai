from app.agents import *
from app.utils import *

import json

from telebot.types import InputFile
from queue import Queue


import threading
import os


COMMANDS = ["/newchat ", "/chat ", "/setsystemprompt "]
load_dotenv()
bot = load_bot()
queue = Queue()
event = threading.Event()
def answer_from_queue():
    while not event.is_set():
        if queue.qsize() >= 1:
            conversation, reply_type, msg = queue.get()
            execute_task(bot, conversation, msg, reply_type)

answerer=threading.Thread(target=answer_from_queue)
answerer.start()


@bot.message_handler(commands = ["chat"])
def start_chat(msg):
    msg.text = msg.text[len(COMMANDS[1]):]

    conv = get_conversation(msg)
    
    block = {
        "role": "user", "content": msg.text
    }
    conv.append(block)

    queue.put((conv, ReplyTypes.TEXT, msg))

  
@bot.message_handler(commands = ["newchat"])
def start_chat(msg):
    msg.text = msg.text[len(COMMANDS[0]):]

    conv = get_conversation(msg)[0:1]
    
    block = {
        "role": "user", "content": msg.text
    }
    conv.append(block)

    queue.put((conv, ReplyTypes.TEXT, msg))


@bot.message_handler(commands = ["setsystemprompt"])
def set_system_prompt(msg):
   
    edited = "I, the user am unhappy with your current personality and wants to change the system prompt. Say your last words. After your next reply, your new system prompt will be:"
    msg.text = msg.text[len(COMMANDS[2]):] # msg.text will be used to create the new system prompt.
    artificial_prompt = edited + msg.text

    conv = get_conversation(msg)
    block = {
        "role": "user", "content": artificial_prompt
    }
    conv.append(block)
    queue.put((conv, ReplyTypes.RESET, msg)) # CHANGE THIS
   


bot.infinity_polling(timeout = 10, long_polling_timeout=5)