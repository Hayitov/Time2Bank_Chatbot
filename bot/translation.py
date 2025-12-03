from dataclasses import dataclass
from typing import Dict

from openai import AsyncOpenAI

from .config import Config


LANGUAGE_SETTINGS: Dict[str, Dict[str, str]] = {
    "uz": {
        "label": "O'zbek",
        "ask_question": "Savolingizni loyiha haqida yozing.",
        "ask_more": "Yana savollaringiz bormi?",
        "choose_language": "Iltimos, tilni tanlang:",
        "selected": "Siz O'zbek tilini tanladingiz. Savolingizni yozing.",
    },
    "ru": {
        "label": "Русский",
        "ask_question": "Пожалуйста, задайте вопрос о проекте.",
        "ask_more": "Есть ли у вас другие вопросы?",
        "choose_language": "Пожалуйста, выберите язык:",
        "selected": "Вы выбрали русский язык. Задайте ваш вопрос о проекте.",
    },
    "en": {
        "label": "English",
        "ask_question": "Please ask your question about the project.",
        "ask_more": "Do you have any other questions?",
        "choose_language": "Please choose your language:",
        "selected": "You selected English. Ask your question about the project.",
    },
}


@dataclass
class TranslationService:
    config: Config
    client: AsyncOpenAI

    async def translate(
        self, text: str, target_language: str, source_language: str | None = None
    ) -> str:
        """Translate text using OpenAI to the desired language."""
        if not text.strip():
            return text
        if source_language and source_language == target_language:
            return text
        target_label = LANGUAGE_SETTINGS.get(target_language, {}).get("label", target_language)
        messages = [
            {
                "role": "system",
                "content": (
                    f"You are a precise translator. Translate the user message to {target_label}. "
                    "Return only the translation without extra commentary."
                ),
            },
            {
                "role": "user",
                "content": text.strip(),
            },
        ]
        if source_language:
            messages.insert(
                1,
                {
                    "role": "system",
                    "content": f"The source language is {LANGUAGE_SETTINGS.get(source_language, {}).get('label', source_language)}.",
                },
            )
        response = await self.client.chat.completions.create(
            model=self.config.translation_model,
            messages=messages,
            temperature=0,
        )
        return response.choices[0].message.content.strip()

    async def to_uzbek(self, text: str, source_language: str | None) -> str:
        return await self.translate(text, target_language="uz", source_language=source_language)

