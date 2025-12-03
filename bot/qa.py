import logging
from textwrap import shorten
from typing import List

import numpy as np
from openai import AsyncOpenAI

from .config import Config
from .embeddings import EmbeddingIndex

logger = logging.getLogger(__name__)


class QAEngine:
    def __init__(self, config: Config, index: EmbeddingIndex, client: AsyncOpenAI):
        self.config = config
        self.index = index
        self.client = client

    async def _embed_query(self, question: str) -> np.ndarray:
        response = await self.client.embeddings.create(model=self.config.embedding_model, input=question)
        return np.array(response.data[0].embedding, dtype=np.float32)

    async def answer(self, question_uzbek: str) -> str:
        """Answer a question in Uzbek using retrieval-augmented generation."""
        query_embedding = await self._embed_query(question_uzbek)
        top_contexts = self.index.top_k(query_embedding, k=self.config.top_k)

        context_blocks: List[str] = []
        for i, (chunk, score) in enumerate(top_contexts, start=1):
            context_blocks.append(f"Bo'lak {i} (score {score:.3f}):\n{chunk}")

        context_text = "\n\n".join(context_blocks)
        if not context_text:
            context_text = "Hujjatdan mos keladigan ma'lumot topilmadi."

        system_prompt = (
            "Siz Time2Bank loyihasi bo'yicha savollarga javob beruvchi yordamchisiz. "
            "Faqat berilgan kontekstdan foydalaning va javobni o'zbek tilida aniq hamda batafsil yozing. "
            "Agar kontekstda ma'lumot bo'lmasa, rostini ayting va to'qimang."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    f"Kontekst:\n{context_text}\n\n"
                    f"Savol: {question_uzbek}\n\n"
                    "Ko'rsatilgan kontekstga tayanib javob bering."
                ),
            },
        ]

        response = await self.client.chat.completions.create(
            model=self.config.qa_model,
            messages=messages,
            temperature=0.2,
        )
        answer = response.choices[0].message.content.strip()
        logger.debug("Answered question: %s", shorten(question_uzbek, 120))
        return answer
