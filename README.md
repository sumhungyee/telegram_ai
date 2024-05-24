# telegram_ai
This project is a spiritual successor of an older project: [Telegram_ai_gptq](https://github.com/sumhungyee/telegram_ai_gptq).
Telegram_AI provides an AI-powered Telegram bot, optimised for local usage. Supports web browsing question-answering as well as memory capabilities.
Powered by Llama 3.

# Installation Guide
### Step 1
Ensure your computer has a dedicated GPU with at least 8GB of VRAM and ensure CUDA Toolkit (>=11.8) is installed. Also ensure that you have [Docker](https://www.docker.com/products/docker-desktop/) installed.

### Step 2
Navigate to a specific location on your computer, and clone the repository.
  ```
  git clone https://github.com/sumhungyee/telegram_ai.git
  cp sample.env .env
  ```
Fill in the parameters in `.env`.

### Step 3
Navigate into the repository at `/telegram_ai`
```
git clone -b 5bpw https://huggingface.co/royallab/L3-8B-Instruct-abliterated-v3-exl2 ./src/models
docker compose up --build
```
This installation will take some time.

# User Guide:
## Available commands
1. `/newchat` - Starts a new `conversation` with the telegram bot. This conversation is unique to each telegram chat id.
2. `/chat` - Continue a `conversation`.
3. `/setsystemprompt`_<ROLE> - Change the system prompt and starts a new `conversation` with a new manually-inscribed role as <ROLE>. This is optional and `/setsystemprompt` is equivalent to `setsystemprompt_assistant`
4. `/toolchat` - (Experimental) Continue a `conversation` with web search enabled.

## Sample Images
![image](https://github.com/sumhungyee/telegram_ai/assets/113227987/8a4208f9-915d-49c0-9a79-404aa8f67f57)
![image](https://github.com/sumhungyee/telegram_ai/assets/113227987/52bbd264-55a8-412a-8189-afce2a9e3843)

