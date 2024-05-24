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
To be added.


