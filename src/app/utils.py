
import torch
import telebot
import gc
import os
from jinja2 import Template

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

def load_bot():
    bot = telebot.TeleBot(os.getenv('APIKEY'))
    bot.mode = bot.llm = bot.tok = bot.settings = bot.cache = None
    return bot


def load_llama3(mode) -> tuple:
    config = ExLlamaV2Config()
    config.model_dir = os.getenv('LLMPATH')
    config.prepare()
    config.max_batch_size = batch_size = 1
    llm = ExLlamaV2(config)
    cache = ExLlamaV2Cache_8bit(llm, lazy = True, batch_size = batch_size)
    llm.load_autosplit(cache)
    tokenizer = ExLlamaV2Tokenizer(config)

    settings = ExLlamaV2Sampler.Settings()
    settings.temperature = 0.85
    settings.top_k = 50
    settings.top_p = 0.8
    settings.token_repetition_penalty = 1.05

    return mode, llm, tokenizer, settings, cache, [128009, tokenizer.eos_token_id]

def task_delegator(reply_type)  -> tuple:
    if reply_type == ReplyTypes.TEXT:
        return load_llama3(reply_type)
    elif reply_type == ReplyTypes.CODE:
        return None # to be updated
    else:
        raise Exception
    
def send_chunked_response_from_prompt(bot, stringified_conversation, stop_conditions, id, max_new_tokens = 4096, Chunk_size = 512):
    generator = ExLlamaV2StreamingGenerator(bot.llm, bot.cache, bot.tok)
    input_ids = bot.tok.encode(stringified_conversation)
    prompt_tokens = input_ids.shape[-1] # stats, to be implemented later
    generator.warmup()
    generator.set_stop_conditions(stop_conditions)
    generator.begin_stream_ex(input_ids, bot.settings,  decode_special_tokens=True)

    output = []
    generated_tokens = 0
    while True:
        chunk, eos, _ = generator.stream()
        generated_tokens += 1
        print(chunk, end = "")
        output.append(chunk)
        if generated_tokens > 0 and generated_tokens % Chunk_size == 0:
            bot.send_message(id, "".join(output),  reply_parameters=id)
            output = []

        if eos or generated_tokens == max_new_tokens:
            bot.send_message(id, "".join(output), reply_parameters=id)
            break


    

def execute_task(bot, conversation, reply_type, id):
    # bot.mode, bot.llm, bot.tok, bot.settings, bot.cache
    if bot.mode != reply_type:
        bot.mode, bot.llm, bot.tok, bot.settings, bot.cache, stop_conditions = task_delegator(reply_type)
        clear_cache()
    # time to reply
    stringified_conversation = apply_llama3_prompt_template(conversation)

    send_chunked_response_from_prompt(bot, stringified_conversation, stop_conditions, id)
  
 

def apply_llama3_prompt_template(messages):
    template = Template("{% for message in messages %}{{'<|im_start|>' + message['role'] + '\n' + message['content'] + '<|im_end|>' + '\n'}}{% endfor %}{{ '<|im_start|>assistant\n' }}")
    return template.render(messages=messages)

def get_llama3_prompt_template_per_msg():
    approx_template = Template("{{'<|im_start|>' + message['role'] + '\n' + message['content'] + '<|im_end|>' + '\n'}}{{ '<|im_start|>assistant\n' }}")
    return approx_template

def truncate(messages, tokenizer, prompt_template_per_msg_function, maxlen=8192):
    tokenized = list(map(lambda message: tokenizer.encode(prompt_template_per_msg_function().render(message=message)), messages))
    pointer = 1
    while len([x for msg in tokenized for x in msg]) >= maxlen:
        pointer += 1
        tokenized = tokenized[0:1] + tokenized[2:]
    return messages[0:1] + messages[pointer:]
