import gc
import torch


def clear_cache():
    gc.collect()
    with torch.no_grad():
        torch.cuda.empty_cache()
   
   

