# Codecraft Community Bot

A Discord bot designed to enhance community engagement and management for Codecraft.


## Installation

1. Clone the repository 
```bash
git clone https://github.com/BrahimChatri/CodeCraft-Community-Bot.git
```
2. Install dependencies: 
    - Using pip :
    ```bash 
    pip install -r requirements.txt 
    ```
    - Using uv package manager (recommended)
    ```bash
    uv sync 
    ```
3. Create  `.env` file and fill following values:
```bash 
TOKEN="remplace with ur bot token get from https://discord.com/developers/applications"
TARGET_CHANNEL_ID = channel id  
alx_backend_role_id = role id 
alx_frontend_role_id = role id
```
4. start bot: 
```bash 
uv run main.py
```

## License

This project is licensed under the MIT License.

---

*For more information, visit the [Discord.js documentation](https://discord.js.org/)*