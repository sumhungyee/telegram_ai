# telegram_ai (@isthisbotabot)
This project is a spiritual successor of an older project: [Telegram_ai_gptq](https://github.com/sumhungyee/telegram_ai_gptq).
Telegram_AI provides an AI-powered Telegram bot, optimised for local usage. Supports Image generation using Stable Diffusion v1.5.
Powered by large language models for general tasks, as well as programming tasks.

# Installation Guide
> [!NOTE]  
> This installation guide will be updated and streamlined by incorporating shell scripting, similar to [Telegram_ai_gptq](https://github.com/sumhungyee/telegram_ai_gptq).
### Step 1
Ensure your computer has a dedicate GPU with at least 8GB of VRAM and ensure CUDA Toolkit (>=11.8) is installed.

### Step 2
Navigate to a specific location on your computer, and clone the repository.
  ```
  git clone https://github.com/sumhungyee/telegram_ai.git
  ```
### Step 3a
Download the desired models off HuggingFace onto your computer and edit `config.ini`.
  To download, navigate to a directory of your choice. Then, perform the following operations.
  Recommended code LLM: [Deepseek-6.7b](https://arxiv.org/pdf/2401.14196.pdf)
  ```
  git clone https://huggingface.co/TheBloke/deepseek-coder-6.7B-instruct-GPTQ -b gptq-4bit-32g-actorder_True
  ```
  Recommended chat LLM: [Mistral-7b](https://arxiv.org/abs/2310.06825)
  ```
  git clone https://huggingface.co/TheBloke/dolphin-2.2.1-mistral-7B-GPTQ -b gptq-4bit-32g-actorder_True
  ```
### Step 3b  
Instructions regarding this step will be updated in the future.
  
### Step 4
Edit `config.ini` and enter the paths of these models into the appropriate field. For example, `C:\...\dolphin-2.2.1-mistral-7B-GPTQ`
### Step 5
Run `main.py`.

# User Guide :
### Scenario 1. User wants to chat with LLM.
![0e7cb1d1-d198-457e-80ab-fc9df4a38c0d](https://github.com/sumhungyee/telegram_ai/assets/113227987/d22938da-13f0-4ddb-87fb-7421afd341c1)
### Scenario 2. User wants help in programming tasks.
![b3d0233b-f562-44f6-82fa-2ff5be47e310](https://github.com/sumhungyee/telegram_ai/assets/113227987/553cdcb5-3cf4-46e9-b27c-b7bc2e49c46e)
### Scenario 3. User wants to generate an image.
![6e5fc858-d2a7-4b1d-b088-d25fde962f58](https://github.com/sumhungyee/telegram_ai/assets/113227987/c1fa8d97-0cd0-47b0-a289-cde6518660ed)
### Scenario 4. User wants to generate an image without certain features (insert negative prompts)
![01c3b311-6779-470f-bfd0-a1494024bbaa](https://github.com/sumhungyee/telegram_ai/assets/113227987/1481d350-c7d2-4f60-bc14-026a004a7f69)
### Scenario 5. User wants to change system prompt.
![image](https://github.com/sumhungyee/telegram_ai/assets/113227987/d2b34f6a-fec7-4570-aef6-6aa3c3819394)


