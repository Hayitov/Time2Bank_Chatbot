import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path

from openai import AsyncOpenAI
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from .config import Config
from .embeddings import EmbeddingIndex, build_or_load_embeddings
from .qa import QAEngine
from .storage import BotStorage
from .translation import LANGUAGE_SETTINGS, TranslationService

logger = logging.getLogger(__name__)


@dataclass
class Services:
    config: Config
    translator: TranslationService
    qa_engine: QAEngine
    storage: BotStorage


def language_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton("O'zbek 🇺🇿", callback_data="lang_uz"),
            InlineKeyboardButton("Русский 🇷🇺", callback_data="lang_ru"),
            InlineKeyboardButton("English 🇬🇧", callback_data="lang_en"),
        ]
    ]
    return InlineKeyboardMarkup(buttons)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    services: Services = context.bot_data["services"]
    user = update.effective_user
    await services.storage.upsert_user(
        chat_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        language=None,
    )
    await update.message.reply_text(
        "Tilni tanlang / Выберите язык / Choose language:",
        reply_markup=language_keyboard(),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Boshlash uchun /start buyrug'ini bosing va tilni tanlang.")


async def handle_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    services: Services = context.bot_data["services"]
    query = update.callback_query
    await query.answer()
    code = query.data.replace("lang_", "")
    context.user_data["language"] = code

    user = update.effective_user
    await services.storage.upsert_user(
        chat_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        language=code,
    )
    message = LANGUAGE_SETTINGS[code]["selected"]
    await query.edit_message_text(message, reply_markup=None)


async def handle_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    services: Services = context.bot_data["services"]
    language = context.user_data.get("language")

    if not language or language not in LANGUAGE_SETTINGS:
        await update.message.reply_text(
            "Iltimos, tilni tanlang / Пожалуйста, выберите язык / Please choose a language:",
            reply_markup=language_keyboard(),
        )
        return

    user_question = update.message.text
    try:
        uz_question = await services.translator.to_uzbek(user_question, source_language=language)
        uz_answer = await services.qa_engine.answer(uz_question)
        if language != "uz":
            answer = await services.translator.translate(uz_answer, target_language=language, source_language="uz")
        else:
            answer = uz_answer

        await services.storage.increment_question_count(update.effective_user.id)
        await services.storage.record_question(update.effective_user.id, user_question, answer)

        await update.message.reply_text(answer)
        await update.message.reply_text(LANGUAGE_SETTINGS[language]["ask_more"])
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to answer question: %s", exc)
        await update.message.reply_text("Uzr, hozircha javob bera olmadim. Qayta urinib ko'ring.")


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    services: Services = context.bot_data["services"]
    if update.effective_user.id != services.config.admin_chat_id:
        await update.message.reply_text("Sizga ruxsat berilmagan.")
        return

    file_path = Path("data/stats.xlsx")
    await services.storage.export_stats(file_path)
    with file_path.open("rb") as f:
        await update.message.reply_document(document=f, filename="stats.xlsx")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Update '%s' caused error: %s", update, context.error)


async def _build_index(config: Config) -> EmbeddingIndex:
    client = AsyncOpenAI(api_key=config.openai_api_key)
    return await build_or_load_embeddings(config, client)


def build_application() -> Application:
    config = Config.load()
    logging.info("Loading embeddings from %s", config.doc_path)
    index = asyncio.run(_build_index(config))

    runtime_client = AsyncOpenAI(api_key=config.openai_api_key)
    translator = TranslationService(config=config, client=runtime_client)
    qa_engine = QAEngine(config=config, index=index, client=runtime_client)
    storage = BotStorage(config.db_path)
    services = Services(config=config, translator=translator, qa_engine=qa_engine, storage=storage)

    application = ApplicationBuilder().token(config.telegram_bot_token).build()
    application.bot_data["services"] = services

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stat", stats))
    application.add_handler(CallbackQueryHandler(handle_language_selection, pattern="^lang_"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_question))
    application.add_error_handler(error_handler)
    return application


def run_bot() -> None:
    application = build_application()
    # Ensure a fresh event loop is set before running polling (required on Python 3.11+).
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    application.run_polling()
