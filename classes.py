class ReplyTypes:
    TEXT = "text"
    CODE = "code"
    DIFFUSER = "dif"

class Reply:

    PLATYPUS ="""
    ### Instruction: {prompt}
    
    ### Response:"""
    CODER = """
    Below is an instruction that describes a programming task. 
    Write a response that appropriately completes the request and provide code in markdown format.
    
    ### Instruction: {prompt}
    
    ### Response:
    """

    DIFFUSER = "{prompt}"

    def __init__(self, msg, mode):
        self.msg = msg
        self.mode = mode
        if mode == ReplyTypes.TEXT:
            self.context = Reply.PLATYPUS
        elif mode == ReplyTypes.CODE:
            self.context = Reply.CODER
        else:
            self.context = Reply.DIFFUSER

    def get_prompt(self, text):
        return self.context.format(prompt=text)
        



