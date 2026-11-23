"""Groq API Large Language Model client wrapper (C-RAGSVC, FR-RAG-007, FR-RAG-008).

Provides low-temperature completion generation using Groq's high-speed LLaMA 3.1 8B instant model.
"""

from typing import Optional, AsyncGenerator
from groq import AsyncGroq, GroqError

from backend.app.core.config import get_settings
from backend.app.core.logging import logger
from backend.app.core.errors import ExternalServiceError

settings = get_settings()


class LLMClient:
    """Async client for Groq API text completions."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: int = 1024,
    ):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.model = model or settings.GROQ_MODEL
        self.temperature = temperature if temperature is not None else settings.RAG_LLM_TEMPERATURE
        self.max_tokens = max_tokens
        self._client: Optional[AsyncGroq] = None

    @property
    def client(self) -> AsyncGroq:
        """Lazy-loaded singleton AsyncGroq client."""
        if self._client is None:
            if not self.api_key or self.api_key.startswith("your_groq"):
                logger.warning("GROQ_API_KEY not configured. Running in offline/mock mode.")
            self._client = AsyncGroq(api_key=self.api_key or "mock-groq-key")
        return self._client

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Sends grounded prompt to Groq API with low temperature (0-0.3).

        Args:
            system_prompt: Grounding and anti-injection system directives.
            user_prompt: Structured prompt with XML context, history, and question.

        Returns:
            Concise text completion from the LLM.

        Raises:
            ExternalServiceError: If Groq API request fails and no fallback is active.
        """
        # Offline or unit-test fallback when no active Groq key is configured
        if not self.api_key or self.api_key.startswith("your_groq") or self.api_key == "mock-groq-key":
            logger.info("Generating mock grounded response (offline development mode)...")
            return self._mock_grounded_response(user_prompt)

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            answer = response.choices[0].message.content or ""
            return answer.strip()
        except GroqError as exc:
            logger.error("Groq API completion failed: %s", exc)
            raise ExternalServiceError("GroqLLM", f"LLM generation failed: {exc}")
        except Exception as exc:
            logger.error("Unexpected error during LLM generation: %s", exc)
            raise ExternalServiceError("GroqLLM", f"Unexpected error: {exc}")

    async def generate_stream(
        self, system_prompt: str, user_prompt: str
    ) -> AsyncGenerator[str, None]:
        """Streams completion tokens from Groq API or deterministic offline mock generator.

        Args:
            system_prompt: Grounding and anti-injection system directives.
            user_prompt: Structured prompt with XML context, history, and question.

        Yields:
            Individual token strings.

        Raises:
            ExternalServiceError: If Groq API streaming fails.
        """
        # Offline or unit-test fallback when no active Groq key is configured
        if not self.api_key or self.api_key.startswith("your_groq") or self.api_key == "mock-groq-key":
            logger.info("Generating mock streamed grounded response (offline development mode)...")
            mock_text = self._mock_grounded_response(user_prompt)
            words = mock_text.split(" ")
            for i, word in enumerate(words):
                chunk = word + (" " if i < len(words) - 1 else "")
                yield chunk
            return

        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=True,
            )
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except GroqError as exc:
            logger.error("Groq API streaming failed: %s", exc)
            raise ExternalServiceError("GroqLLM", f"LLM streaming failed: {exc}")
        except Exception as exc:
            logger.error("Unexpected error during LLM streaming: %s", exc)
            raise ExternalServiceError("GroqLLM", f"Unexpected error: {exc}")

    def _mock_grounded_response(self, user_prompt: str) -> str:
        """Deterministic simulation for unit testing when offline."""
        if "<no_context>" in user_prompt:
            return settings.RAG_INSUFFICIENT_CONTEXT_MESSAGE

        import re

        sources = re.findall(r'<source index="(\d+)"[^>]*>(.*?)</source>', user_prompt, re.DOTALL)
        if not sources:
            return settings.RAG_INSUFFICIENT_CONTEXT_MESSAGE

        q_match = re.search(r"<user_question>(.*?)</user_question>", user_prompt, re.DOTALL)
        question = q_match.group(1).lower() if q_match else ""
        q_words = set(re.findall(r"\b\w{4,}\b", question)) - {"what", "when", "where", "which", "would", "could", "should"}

        first_idx, first_text = sources[0]
        sentences = [s.strip() for s in re.split(r"[.\n]+", first_text) if len(s.strip()) > 15]

        best_sentence = None
        best_overlap = -1
        for s in sentences:
            s_words = set(re.findall(r"\b\w{4,}\b", s.lower()))
            overlap = len(q_words & s_words)
            if overlap > best_overlap:
                best_overlap = overlap
                best_sentence = s

        if best_sentence:
            return f"Based on the university regulations [Source {first_idx}], {best_sentence.strip()}."

        return (
            f"According to the provided university documents [Source {first_idx}], "
            f"the policy specifies: {first_text.strip()[:200]}."
        )


llm_client = LLMClient()
