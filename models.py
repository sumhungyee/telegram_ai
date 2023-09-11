

import gc
import torch
import torch.nn as nn

from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler


def clear_cache():
    gc.collect()
    with torch.no_grad():
        torch.cuda.empty_cache()
   

# Extracted from diffusers' scripts: 
# https://github.com/huggingface/diffusers/blob/1997614aa9525ef0f49858ac409540fdf2f02e9d/scripts/convert_lora_safetensor_to_diffusers.py#L48
# https://towardsdatascience.com/improving-diffusers-package-for-high-quality-image-generation-a50fff04bdd4

from safetensors.torch import load_file
def load_lora(
    pipeline
    ,lora_path
    ,lora_weight=0.8
):
    if not lora_path.strip():
        return pipeline
    
    state_dict = load_file(lora_path)
    LORA_PREFIX_UNET = 'lora_unet'
    LORA_PREFIX_TEXT_ENCODER = 'lora_te'

    alpha = lora_weight
    visited = []

    # directly update weight in diffusers model
    for key in state_dict:
        
        # as we have set the alpha beforehand, so just skip
        if '.alpha' in key or key in visited:
            continue
            
        if 'text' in key:
            layer_infos = key.split('.')[0].split(LORA_PREFIX_TEXT_ENCODER+'_')[-1].split('_')
            curr_layer = pipeline.text_encoder
        else:
            layer_infos = key.split('.')[0].split(LORA_PREFIX_UNET+'_')[-1].split('_')
            curr_layer = pipeline.unet

        # find the target layer
        temp_name = layer_infos.pop(0)
        while len(layer_infos) > -1:
            try:
                curr_layer = curr_layer.__getattr__(temp_name)
                if len(layer_infos) > 0:
                    temp_name = layer_infos.pop(0)
                elif len(layer_infos) == 0:
                    break
            except Exception:
                if len(temp_name) > 0:
                    temp_name += '_'+layer_infos.pop(0)
                else:
                    temp_name = layer_infos.pop(0)
        
        # org_forward(x) + lora_up(lora_down(x)) * multiplier
        pair_keys = []
        if 'lora_down' in key:
            pair_keys.append(key.replace('lora_down', 'lora_up'))
            pair_keys.append(key)
        else:
            pair_keys.append(key)
            pair_keys.append(key.replace('lora_up', 'lora_down'))
        
        # update weight
        if len(state_dict[pair_keys[0]].shape) == 4:
            weight_up = state_dict[pair_keys[0]].squeeze(3).squeeze(2).to(torch.float32)
            weight_down = state_dict[pair_keys[1]].squeeze(3).squeeze(2).to(torch.float32)
            curr_layer.weight.data += alpha * torch.mm(weight_up, weight_down).unsqueeze(2).unsqueeze(3)
        else:
            weight_up = state_dict[pair_keys[0]].to(torch.float32)
            weight_down = state_dict[pair_keys[1]].to(torch.float32)
            curr_layer.weight.data += alpha * torch.mm(weight_up, weight_down)
            
        # update visited list
        for item in pair_keys:
            visited.append(item)
            
        
        
    del state_dict, curr_layer, weight_up, weight_down, pair_keys, visited, layer_infos
    clear_cache()
        
    return pipeline


def load_diffuser(model_path, lora_path):
    pipe = StableDiffusionPipeline.from_pretrained(model_path, torch_dtype=torch.float32)

    pipe.safety_checker = None
    pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
    pipe = load_lora(pipeline=pipe, lora_path=lora_path)
    return pipe


