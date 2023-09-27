import telebot
from ctransformers import AutoModelForCausalLM
from models import *
import torch
from telebot.types import InputFile
from classes import *
import configparser
import threading
import io
from queue import Queue
config = configparser.ConfigParser(allow_no_value=True)
config.read("./config.ini")
COMMANDS = ["/chat", "/code", "/dream"]
MAX_LEN = int(config["BOT"]["MAXLEN"])
TELEGRAM_MAX_MESSAGE_LENGTH = 4096
bot = telebot.TeleBot(config["BOT"]["APIKEY"])
bot.curr_mode = None
bot.llm = None
bot.diffuser = load_diffuser(\
    config["IMGGEN"]["PATH"], \
        config["IMGGEN"]["LORAPATH"])

queue = Queue()
event = threading.Event()
def answer_from_queue():
 
    while not event.is_set():
        if queue.qsize() >= 1:
            task = queue.get()
            
            execute_task(bot, task)
            


answerer=threading.Thread(target=answer_from_queue)
answerer.start()

def generate_image(bot, task):
    bot.llm = None
    clear_cache()
    bot.diffuser.to("cuda")
    processed = task.msg.text.split("|")
    prompt = processed[0]
    neg_prompt = None if len(processed) == 1 else processed[1]

    image = bot.diffuser(\
        prompt=prompt, negative_prompt=neg_prompt, num_inference_steps=60, \
            height=512, width=512, num_images_per_prompt=1).images[0]

    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='PNG')
    
    img_byte_arr = img_byte_arr.getvalue()
    file = io.BytesIO(img_byte_arr)
    try:
        bot.reply_to(task.msg, f"Positive prompt: {prompt}, \nNegative prompt: {neg_prompt}")
    except telebot.apihelper.ApiTelegramException as e:
        bot.send_message(task.msg.chat.id, f"Positive prompt: {prompt}, \nNegative prompt: {neg_prompt}")
        
    bot.send_photo(photo=InputFile(file), chat_id=task.msg.chat.id, reply_to_message_id=task.msg, has_spoiler=True)
    bot.curr_mode = ReplyTypes.DIFFUSER

def generate_text(bot, task):
    bot.llm = None
    clear_cache()
    if task.mode == ReplyTypes.TEXT:
        bot.llm = AutoModelForCausalLM.from_pretrained(\
            config["TEXTLLM"]["PATH"], model_type="llama", gpu_layers=25, stop=["###"],
            temperature = 0.7, max_new_tokens = 1200, context_length=4096)
        
    else:
        bot.llm = AutoModelForCausalLM.from_pretrained(\
            config["CODELLM"]["PATH"], 
            model_type="llama", gpu_layers=25, temperature = 0.3, max_new_tokens = 1200,
            context_length=4096)
        
       
    bot.curr_mode = task.mode     
    msg_length = len(task.msg.text)
    if  msg_length > MAX_LEN:
        bot.reply_to(
            task.msg, f"Message is too long, please reduce the length of your prompt to <={MAX_LEN} characters. Currently {msg_length} characters.")
        return None

    
    generated = bot.llm(task.get_prompt(task.msg.text))
    replies = [generated[i: i+TELEGRAM_MAX_MESSAGE_LENGTH] for i in range(0, len(generated), TELEGRAM_MAX_MESSAGE_LENGTH)]
    
    reply_text_with_exceptions(replies, task)
   

def reply_text_with_exceptions(replies, task):
    if not replies:   # handle empty messages without throwing exceptions
        bot.reply_to(task.msg, "This message is empty")
    else:
        try:
            for reply in replies:
                bot.reply_to(task.msg, reply, parse_mode="Markdown")

        except telebot.apihelper.ApiTelegramException as e:
            try:
                for reply in replies:
                    bot.reply_to(task.msg, reply)
            except telebot.apihelper.ApiTelegramException as f:
                for reply in replies:
                    bot.send_message(task.msg.chat.id, reply)
            except Exception as g:
                pass



def execute_task(bot, task: Reply):
    if bot.curr_mode != task.mode:
        if bot.curr_mode == ReplyTypes.DIFFUSER:
            bot.diffuser.to("cpu")
            generate_text(bot, task)

        elif task.mode == ReplyTypes.DIFFUSER: 
            generate_image(bot, task)
        else:
            bot.diffuser.to("cpu")
            generate_text(bot, task)
    else:
        if task.mode == ReplyTypes.DIFFUSER:
            generate_image(bot, task)
        else:
            bot.diffuser.to("cpu")
            generate_text(bot, task)
            

def add_to_queue(msg, reply_type):  
    if f"/chat{config['BOT']['BOTNAME']}" not in msg.text or msg.text.strip() in COMMANDS:
        msg.text = msg.text[len("/chat "):]
        queue.put(Reply(msg, reply_type)) 
        #print(Reply(msg, reply_type).msg)


@bot.message_handler(commands = ["chat"])
def chat(msg):
    add_to_queue(msg, ReplyTypes.TEXT)

@bot.message_handler(commands = ["code"])
def code(msg):
    add_to_queue(msg, ReplyTypes.CODE)

@bot.message_handler(commands = ["dream"])
def diffuse(msg):
    add_to_queue(msg, ReplyTypes.DIFFUSER)


bot.infinity_polling(timeout = 10, long_polling_timeout=5)