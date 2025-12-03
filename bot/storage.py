import asyncio
import sqlite3
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook


class BotStorage:
    """Simple SQLite storage for users and question counts."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    chat_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    language TEXT,
                    question_count INTEGER DEFAULT 0,
                    created_at TEXT,
                    updated_at TEXT
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER,
                    question TEXT,
                    answer TEXT,
                    asked_at TEXT,
                    FOREIGN KEY(chat_id) REFERENCES users(chat_id)
                );
                """
            )
            conn.commit()

    async def upsert_user(
        self, chat_id: int, username: str | None, first_name: str | None, last_name: str | None, language: str | None
    ) -> None:
        await asyncio.to_thread(self._upsert_user, chat_id, username, first_name, last_name, language)

    def _upsert_user(
        self, chat_id: int, username: str | None, first_name: str | None, last_name: str | None, language: str | None
    ) -> None:
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO users (chat_id, username, first_name, last_name, language, question_count, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 0, ?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET
                    username=excluded.username,
                    first_name=excluded.first_name,
                    last_name=excluded.last_name,
                    language=COALESCE(excluded.language, users.language),
                    updated_at=excluded.updated_at;
                """,
                (chat_id, username, first_name, last_name, language, now, now),
            )
            conn.commit()

    async def increment_question_count(self, chat_id: int) -> None:
        await asyncio.to_thread(self._increment_question_count, chat_id)

    def _increment_question_count(self, chat_id: int) -> None:
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE users
                SET question_count = question_count + 1,
                    updated_at = ?
                WHERE chat_id = ?;
                """,
                (now, chat_id),
            )
            conn.commit()

    async def record_question(self, chat_id: int, question: str, answer: str) -> None:
        await asyncio.to_thread(self._record_question, chat_id, question, answer)

    def _record_question(self, chat_id: int, question: str, answer: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO questions (chat_id, question, answer, asked_at)
                VALUES (?, ?, ?, ?);
                """,
                (chat_id, question, answer, datetime.utcnow().isoformat()),
            )
            conn.commit()

    async def export_stats(self, path: Path) -> Path:
        return await asyncio.to_thread(self._export_stats, path)

    def _export_stats(self, path: Path) -> Path:
        with self._connect() as conn:
            users = conn.execute(
                """
                SELECT chat_id, username, first_name, last_name, language, question_count, created_at, updated_at
                FROM users
                ORDER BY updated_at DESC;
                """
            ).fetchall()

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Users"
        headers = ["chat_id", "username", "first_name", "last_name", "language", "question_count", "created_at", "updated_at"]
        sheet.append(headers)
        for row in users:
            sheet.append([row[h] for h in headers])

        path.parent.mkdir(parents=True, exist_ok=True)
        workbook.save(path)
        return path
