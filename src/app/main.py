from app.agents import *
from app.utils import *

import time
from telebot.types import InputFile
from queue import Queue


import threading
import re


COMMANDS = ["/newchat ", "/chat ", "/setsystemprompt ", "/toolchat "]
load_dotenv()
bot = load_bot()
queue = Queue()
event = threading.Event()
def answer_from_queue():
    while not event.is_set():
        if queue.qsize() >= 1:
            reply_type, msg = queue.get()
            execute_task(bot, msg, reply_type)
            time.sleep(0.1)

answerer=threading.Thread(target=answer_from_queue)
answerer.start()


@bot.message_handler(commands = ["chat"])
def start_chat(msg):
    msg.text = msg.text[len(COMMANDS[1]):]
    queue.put((ReplyTypes.TEXT, msg))

  
@bot.message_handler(commands = ["newchat"])
def start_chat(msg):
    msg.text = msg.text[len(COMMANDS[0]):]
    queue.put((ReplyTypes.NEWTEXT, msg))

# @bot.message_handler(commands = ["toolchat"])
# def start_chat(msg):
#     msg.text = msg.text[len(COMMANDS[3]):]
#     queue.put((ReplyTypes.TOOLTEXT, msg))

@bot.message_handler(func = lambda message: message.text.startswith(COMMANDS[2][:-1]))
def set_system_prompt(msg):
    cmd = re.match(f"{COMMANDS[2][:-1]}([\w_]*)", msg.text, re.IGNORECASE).group()
    array = cmd.split("_")
    if len(array) > 1 and array[-1]:
        desired_role = array[-1]
    else:
        desired_role = "assistant"

    msg.role = desired_role
    msg.text = msg.text[len(cmd) + 1:] # msg.text will be used to create the new system prompt.

    queue.put((ReplyTypes.RESET, msg)) # CHANGE THIS
   


bot.infinity_polling(timeout = 10, long_polling_timeout=5)