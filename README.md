# telegram_ai (@isthisbotabot)
This project is a spiritual successor of an older project: [Telegram_ai_gptq](https://github.com/sumhungyee/telegram_ai_gptq).
Telegram_AI provides an AI-powered Telegram bot, optimised for local usage. Supports Image generation using Stable Diffusion v1.5.
Powered by large language models for general tasks, as well as programming tasks.

# Installation Guide
1. Ensure your computer has a dedicate GPU with at least 8GB of VRAM and ensure CUDA Toolkit (>=11.8) is installed.
2. Navigate to a specific location on your computer, and clone the repository.
  ```
  git clone https://github.com/sumhungyee/telegram_ai.git
  ```
3. Download the desired models off HuggingFace onto your computer and edit `config.ini`.
  To download, navigate to a directory of your choice. Then, perform the following operations.
  Recommended code LLM: [Deepseek-6.7b](https://arxiv.org/pdf/2401.14196.pdf)
  ```
  git clone https://huggingface.co/TheBloke/deepseek-coder-6.7B-instruct-GPTQ -b gptq-4bit-32g-actorder_True
  ```
  Recommended chat LLM: [Mistral-7b](https://arxiv.org/abs/2310.06825)
  ```
  git clone https://huggingface.co/TheBloke/dolphin-2.2.1-mistral-7B-GPTQ -b gptq-4bit-32g-actorder_True
  ```
4. Edit `config.ini` and enter the paths of these models into the appropriate field. For example, `C:\...\dolphin-2.2.1-mistral-7B-GPTQ`
5. Run `main.py`.


# Samples :
![image](https://github.com/sumhungyee/telegram_ai/assets/113227987/607812c8-9180-40f9-8240-c90c90430968)
![image](https://github.com/sumhungyee/telegram_ai/assets/113227987/85fbee65-87ad-4ea3-941a-8a32e87caaf5)


