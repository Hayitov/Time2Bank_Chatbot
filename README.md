# Time2Bank Telegram QA Bot

Multilingual Telegram bot for Q&A over the Time2Bank project DOCX. Users pick Uzbek/Russian/English, questions are translated to Uzbek for retrieval, and answers are translated back. The bot stores user stats and can export them to Excel for the admin.

## Features
- Language selection (Uzbek, Russian, English) with consistent replies in the chosen language.
- Translates user questions to Uzbek, runs retrieval-augmented generation on `Time2Bank.docx`, and translates answers back.
- Detailed answers with follow-up prompt.
- SQLite persistence for users and questions; `/stat` (admin only) exports `stats.xlsx`.
- Embeddings cached on disk; rebuilt automatically if the DOCX changes.

## Configuration
1. Copy `.env.example` to `.env` and fill in secrets (already done locally):
   - `OPENAI_API_KEY` (ChatGPT token)
   - `TELEGRAM_BOT_TOKEN` (bot token)
   - `ADMIN_CHAT_ID` (already set to `807908681`)
   - Paths and model settings can stay at defaults.
2. Place `Time2Bank.docx` in the project root (same folder as `docker-compose.yml`).

## Local Run (without Docker)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m bot
```

## Docker Run
```bash
docker compose build
docker compose up -d   # runs persistently
docker compose logs -f # view logs
docker compose down    # stop
```
The `data/` folder is mounted to persist the SQLite DB, embeddings cache, and exported stats.

## Transferring to the Server
Server path: `/root/Chatbot` on `root@46.101.202.97`.

1. From your local machine, sync the project (including `.env` and `Time2Bank.docx`):
   ```bash
   rsync -av --delete /Users/a1/chatbot/ root@46.101.202.97:/root/Chatbot/
   ```
   or:
   ```bash
   scp -r /Users/a1/chatbot/* root@46.101.202.97:/root/Chatbot/
   ```
2. SSH into the server and run:
   ```bash
   cd /root/Chatbot
   docker compose build
   docker compose up -d
   ```

## Admin Stats
- Command: `/stat` (admin chat ID: `807908681`).
- Returns an `stats.xlsx` file with user info and question counts (stored under `data/`).

## Notes
- Embeddings are generated on first run (or when the DOCX changes) and cached at `data/embeddings.pkl`.
- QA model defaults to `gpt-4o` for accuracy; adjust via `QA_MODEL` in `.env` if desired.
# Chatbot
# Chatbot
# Chatbot
# Time2Bank_Chatbot
# Time2Bank_Chatbot
