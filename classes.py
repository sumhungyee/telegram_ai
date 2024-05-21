import configparser

def get_config():
    config = configparser.ConfigParser(allow_no_value=True)
    config.read("./settings/config.ini")
    return config

class ReplyTypes:
    TEXT = "text"
    CODE = "code"
    DIFFUSER = "dif"

class Reply:

    MISTRAL = '''<|im_start|>system
{system_prompt}<|im_end|>
<|im_start|>user
{{prompt}}<|im_end|>
<|im_start|>assistant
'''
    CODER = '''You are an AI programming assistant, utilizing the Deepseek Coder model, developed by Deepseek Company, and you only answer questions related to computer science. For politically sensitive questions, security and privacy issues, and other non-computer science questions, you will refuse to answer.
### Instruction:
{prompt}
### Response:
'''

    DIFFUSER = "{prompt}"

    def __init__(self, msg, mode):
        self.msg = msg
        self.mode = mode
        if mode == ReplyTypes.TEXT:
            file = open("settings/system_prompt.txt")
            read_file = file.read()
            file.close()
            self.context = Reply.MISTRAL.format(system_prompt=read_file)
            
        elif mode == ReplyTypes.CODE:
            self.context = Reply.CODER
        else:
            self.context = Reply.DIFFUSER

    def get_prompt(self, text):
        return self.context.format(prompt=text)
        



