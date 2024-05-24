import logging
import re
import os
import gc
import torch
import time
import json

from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler
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

def clear_gpu_cache():
    gc.collect()
    with torch.no_grad():
        torch.cuda.empty_cache()
    logger.info("GPU cache cleared")

def truncate_conversation(input_ids, conversation, llm, max_len=8100):
    while len(input_ids[0]) >= max_len:
        logger.info("Conversation too long, truncating conversation.")
        conversation = conversation[0:1] + conversation[2:]
        stringified_conversation = llm.apply_prompt_template(conversation)
        input_ids = llm.tokenizer.encode(stringified_conversation)
    return input_ids, conversation

def generate_quick(llm, input_ids, max_new_tokens=256):
    logger.info("Begin quick generation")
    generator = llm.start_generator(input_ids)
    clear_gpu_cache()
    output = []
    generated_tokens = 0
    while True:
        chunk, eos, _ = generator.stream()
        generated_tokens += 1
        print(chunk, end = "")
        output.append(chunk)
        if eos or generated_tokens == max_new_tokens:
            break
    print()
    return "".join(output)

def try_parse(function, **kwargs):
    
    string = function(**kwargs)
    pattern = r'^```(?:\w+)?\s*\n(.*?)(?=^```)```'
    pattern_2 = r'^```(?:\w+)?\s*\n(.*)'
    for pat in [pattern, pattern_2]:
        regex = re.findall(pat, string, re.DOTALL | re.MULTILINE)
     
        try:
            output = regex[0]
            return json.loads(output)
        except Exception as f:
            logger.error(repr(f"JSON decode error in try_parse: JSON string:{string}, pattern:{pat}"))
            continue
    return json.loads(string)
   

class Llama3:
    
    def __init__(self, temperature=0.3):
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
        self.settings.temperature = temperature
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
    
class ReplyTypes:
    TOOLTEXT = "tooltext"
    TEXT = "text"
    NEWTEXT = "newtext"
    RESET = "reset"