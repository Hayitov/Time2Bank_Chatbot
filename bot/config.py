import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


@dataclass
class Config:
    """Application configuration loaded from environment variables."""

    openai_api_key: str
    telegram_bot_token: str
    admin_chat_id: int
    doc_path: Path
    embedding_model: str = "text-embedding-3-large"
    qa_model: str = "gpt-4o"
    translation_model: str = "gpt-4o-mini"
    top_k: int = 4
    max_context_chars: int = 1500
    db_path: Path = Path("data/bot.db")
    embeddings_cache: Path = Path("data/embeddings.pkl")

    @classmethod
    def load(cls) -> "Config":
        load_dotenv()

        openai_api_key = os.getenv("OPENAI_API_KEY")
        telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        admin_chat_id = int(os.getenv("ADMIN_CHAT_ID", "807908681"))

        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY is required.")
        if not telegram_bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required.")

        doc_path = Path(os.getenv("DOC_PATH", "Time2Bank.docx")).expanduser()
        embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
        qa_model = os.getenv("QA_MODEL", "gpt-4o")
        translation_model = os.getenv("TRANSLATION_MODEL", "gpt-4o-mini")
        top_k = int(os.getenv("TOP_K", "4"))
        max_context_chars = int(os.getenv("MAX_CONTEXT_CHARS", "1500"))
        db_path = Path(os.getenv("DB_PATH", "data/bot.db"))
        embeddings_cache = Path(os.getenv("EMBEDDINGS_CACHE", "data/embeddings.pkl"))

        return cls(
            openai_api_key=openai_api_key,
            telegram_bot_token=telegram_bot_token,
            admin_chat_id=admin_chat_id,
            doc_path=doc_path,
            embedding_model=embedding_model,
            qa_model=qa_model,
            translation_model=translation_model,
            top_k=top_k,
            max_context_chars=max_context_chars,
            db_path=db_path,
            embeddings_cache=embeddings_cache,
        )
