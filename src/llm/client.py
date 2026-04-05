"""Ollama client wrapper for LLM inference."""

import asyncio
from typing import Optional, List

from ollama import AsyncClient

from src.utils.logger import get_logger
from src.utils.config import get_config

logger = get_logger(__name__)


class OllamaClient:
    """Wrapper for Ollama API client."""

    def __init__(self):
        """Initialize Ollama client."""
        config = get_config()
        self.timeout_seconds = config.llm.timeout
        logger.info(f"[LLM CLIENT] Initializing with timeout: {self.timeout_seconds}s")

        self.client = AsyncClient(
            host=config.llm.ollama_host,
            timeout=float(self.timeout_seconds),
        )

        self.ollama_host = config.llm.ollama_host.rstrip("/")
        self._semaphore = asyncio.Semaphore(config.llm.max_concurrent)

        # Model cache
        self._available_models_cache: Optional[List[str]] = None
        self._cache_timestamp: float = 0
        self._cache_ttl: float = 300

    async def _get_available_models(self) -> List[str]:
        """Get list of available Ollama models (cached)."""
        import time
        current_time = time.time()

        if self._available_models_cache is not None and (current_time - self._cache_timestamp) < self._cache_ttl:
            return self._available_models_cache

        try:
            response = await self.client.list()
            # Handle both old dict format and new object format
            models_list = []
            models_data = response.get("models", []) if isinstance(response, dict) else getattr(response, "models", [])
            for m in models_data:
                # Try different attribute/key names
                if isinstance(m, dict):
                    name = m.get("name") or m.get("model")
                else:
                    name = getattr(m, "name", None) or getattr(m, "model", None)
                if name:
                    models_list.append(name)
            self._available_models_cache = models_list
            self._cache_timestamp = current_time
            logger.debug(f"[LLM CLIENT] Cached {len(self._available_models_cache)} available models")
            return self._available_models_cache
        except Exception as e:
            logger.warning(f"[LLM CLIENT] Failed to list models: {e}")
            return self._available_models_cache or []

    async def _get_valid_model(self, requested_model: str) -> str:
        """Get a valid model, falling back if requested model isn't available."""
        available = await self._get_available_models()

        if not available:
            logger.warning("[LLM CLIENT] Cannot verify models - Ollama may not be running")
            return requested_model

        if requested_model in available:
            return requested_model

        # Try partial match
        for model in available:
            if requested_model.split(":")[0] == model.split(":")[0]:
                logger.warning(f"[LLM CLIENT] Model '{requested_model}' not found, using: '{model}'")
                return model

        # Fall back to first available
        fallback = available[0]
        logger.warning(f"[LLM CLIENT] Model '{requested_model}' not found! Falling back to: '{fallback}'")
        return fallback

    async def generate_text(
        self,
        prompt: str,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """Generate text using specified model.

        Args:
            prompt: User prompt
            model: Model name (uses default if not specified)
            system_prompt: Optional system prompt
            temperature: Sampling temperature

        Returns:
            Generated text response
        """
        config = get_config()
        requested_model = model or config.llm.model
        temperature = temperature if temperature is not None else config.llm.temperature

        model = await self._get_valid_model(requested_model)

        async with self._semaphore:
            try:
                logger.debug(f"Generating text with model: {model}")

                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})

                response = await self.client.chat(
                    model=model,
                    messages=messages,
                    options={
                        "temperature": temperature,
                        "seed": config.llm.seed,
                        "num_predict": 8192,
                    }
                )

                message = response.get("message", {})
                content = message.get("content", "")

                # Handle thinking models
                if "</think>" in content:
                    logger.info("[LLM] Found </think> tag, stripping thinking content")
                    content = content.split("</think>", 1)[1].strip()

                logger.debug(f"Generated {len(content)} characters")
                return content

            except Exception as e:
                logger.error(f"Failed to generate text: {e}")
                raise

    async def check_status(self) -> dict:
        """Check Ollama status and available models.

        Returns:
            Status dict with connection info and models
        """
        try:
            models = await self._get_available_models()
            return {
                "status": "connected",
                "host": self.ollama_host,
                "available_models": models,
                "model_count": len(models)
            }
        except Exception as e:
            return {
                "status": "disconnected",
                "host": self.ollama_host,
                "error": str(e)
            }

    async def pull_model(self, model: str) -> bool:
        """Pull a model from Ollama repository.

        Args:
            model: Model name

        Returns:
            True if successful
        """
        try:
            logger.info(f"Pulling model: {model}")
            await self.client.pull(model)
            logger.info(f"Model pulled successfully: {model}")
            # Invalidate cache
            self._available_models_cache = None
            return True
        except Exception as e:
            logger.error(f"Failed to pull model: {e}")
            return False
