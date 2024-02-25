from classes import ReplyTypes, Reply, get_config
from models import *
from telebot.types import InputFile
from transformers import AutoModelForCausalLM, AutoTokenizer
from queue import Queue

import telebot
import threading
import io

config = get_config()
COMMANDS = ["/chat", "/code", "/dream"]
MAX_LEN = int(config["BOT"]["MAXLEN"])
TELEGRAM_MAX_MESSAGE_LENGTH = 4096
bot = telebot.TeleBot(config["BOT"]["APIKEY"])
bot.curr_mode = bot.llm = bot.diffuser = bot.tok = None
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
    
    if bot.llm is not None:
        bot.llm.cpu()
    bot.llm = None
    bot.tok = None
    clear_cache()

    if bot.curr_mode != task.mode:
        bot.diffuser =  load_diffuser(\
            config["IMGGEN"]["PATH"], \
            config["IMGGEN"]["LORAPATH"])
        bot.diffuser.to("cuda")

    processed = task.msg.text.split("|")
    prompt = processed[0]
    neg_prompt = None if len(processed) == 1 else processed[1]

    image = bot.diffuser(\
        prompt=prompt, negative_prompt=neg_prompt, num_inference_steps=40, \
            height=512, width=512, num_images_per_prompt=1).images[0]

    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='PNG')
    
    img_byte_arr = img_byte_arr.getvalue()
    file = io.BytesIO(img_byte_arr)
    try:
        bot.reply_to(task.msg, f"Positive prompt: {prompt}, \nNegative prompt: {neg_prompt}")
    except telebot.apihelper.ApiTelegramException as e:
        bot.send_message(task.msg.chat.id, f"Positive prompt: {prompt}, \nNegative prompt: {neg_prompt}")

    photo_file = InputFile(file)
    bot.curr_mode = ReplyTypes.DIFFUSER
    try:
        bot.send_photo(task.msg.chat.id, photo_file, has_spoiler=True)
    except Exception as e:
        bot.send_message(task.msg.chat.id, f"Error sending image:\n```python\n{e}\n```", parse_mode="Markdown")
    

def generate_text(bot, task):
    bot.diffuser = None
    if bot.curr_mode != task.mode:
        print("Mounting llm...")
        if bot.llm is not None:
            bot.llm.cpu()
        bot.llm = None
        clear_cache()
        
        path = config["TEXTLLM"]["PATH"] if task.mode == ReplyTypes.TEXT else config["CODELLM"]["PATH"]
        bot.llm = AutoModelForCausalLM.from_pretrained(\
            path, device_map="cuda") 
        bot.tok = AutoTokenizer.from_pretrained(path)
       
       
    bot.curr_mode = task.mode     
    msg_length = len(task.msg.text)
    if  msg_length > MAX_LEN:
        bot.reply_to(
            task.msg, f"Message is too long, please reduce the length of your prompt to <={MAX_LEN} characters. Currently {msg_length} characters.")
        return None

    prompt_template = task.get_prompt(task.msg.text)
    input_ids = bot.tok(prompt_template, return_tensors='pt').input_ids.cuda()
    output = bot.llm.generate(
        inputs=input_ids,
        temperature=0.7, 
        do_sample=True, 
        top_p=0.95, 
        top_k=40, 
        repetition_penalty=1,
        max_new_tokens=2048,
        eos_token_id=bot.tok.eos_token_id,
        
    )

    generated = bot.tok.batch_decode(output[:, input_ids.shape[1]:], skip_special_tokens=True)[0]
    replies = [generated[i: i+TELEGRAM_MAX_MESSAGE_LENGTH] for i in range(0, len(generated), TELEGRAM_MAX_MESSAGE_LENGTH)]
    input_ids.cpu()
    del input_ids
    reply_text_with_exceptions(replies, task)
   

def reply_text_with_exceptions(replies, task):
    if not replies or not replies[0].strip():   # handle empty messages without throwing exceptions
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
    if task.mode == ReplyTypes.DIFFUSER:
        generate_image(bot, task)
    else:
        generate_text(bot, task)
    

def add_to_queue(msg, reply_type):
    short_cmd_length = 6
    if f"{config['BOT']['BOTNAME']}" not in msg.text or not (msg.text.strip() in COMMANDS):
        msg.text = msg.text[short_cmd_length:]
        queue.put(Reply(msg, reply_type))


@bot.message_handler(commands = ["chat"])
def chat(msg):
    add_to_queue(msg, ReplyTypes.TEXT)

@bot.message_handler(commands = ["code"])
def code(msg):
    add_to_queue(msg, ReplyTypes.CODE)

@bot.message_handler(commands = ["dream"])
def diffuse(msg):
    add_to_queue(msg, ReplyTypes.DIFFUSER)

@bot.message_handler(commands = ["setsystemprompt"])
def set_system_prompt(msg):
    long_cmd_length = len("/setSystemPrompt ")
    edited = "      I, the user am unhappy with your current personality and wants to change the system prompt. Say your last words. After your next reply, your new system prompt will be:"
    new_prompt = msg.text[long_cmd_length:]
    msg.text = edited + new_prompt
    add_to_queue(msg, ReplyTypes.TEXT)
    with open('settings/system_prompt.txt', 'w') as f:
        f.write(new_prompt)


bot.infinity_polling(timeout = 10, long_polling_timeout=5)