"""OpenAI-compatible Chat Completions client."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict

import aiohttp

from .config import ModelConfig


class OpenAICompatibleClient:
    """Call any endpoint that follows /chat/completions semantics."""

    def __init__(self, model_config: ModelConfig):
        self.model_config = model_config

    async def complete(self, system_prompt: str, user_input: str) -> Dict[str, Any]:
        """Send one chat completion request."""
        config = self.model_config
        url = f"{config.base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {config.resolved_api_key()}",
            "Content-Type": "application/json",
            **config.headers,
        }

        body: Dict[str, Any] = {
            "model": config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input},
            ],
        }

        if config.temperature is not None:
            body["temperature"] = config.temperature
        if config.max_tokens is not None:
            body["max_tokens"] = config.max_tokens
        if config.extra_body:
            body.update(config.extra_body)

        timeout = aiohttp.ClientTimeout(total=config.timeout_seconds)
        started_at = datetime.now()
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, headers=headers, json=body) as response:
                text = await response.text()
                elapsed = (datetime.now() - started_at).total_seconds()
                if response.status >= 400:
                    raise RuntimeError(f"HTTP {response.status}: {text}")
                data = json.loads(text)

        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        content = message.get("content") or ""

        return {
            "model_name": config.name,
            "provider": config.provider,
            "requested_model": config.model,
            "response_model": data.get("model"),
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "answer": content,
            "finish_reason": choice.get("finish_reason"),
            "usage": data.get("usage", {}),
            "latency_seconds": elapsed,
            "raw_response_id": data.get("id"),
        }
