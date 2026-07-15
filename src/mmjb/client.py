"""Minimal multi-model inference client (OpenAI-compatible chat completions)."""

from __future__ import annotations

import os
from typing import Any


class InferenceClient:
    """POST /v1/chat/completions-style calls; model id is gateway-specific."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float = 300.0,
    ) -> None:
        self.base_url = (base_url or os.environ.get("INFERENCE_API_URL", "")).rstrip("/")
        self.api_key = api_key or os.environ.get("INFERENCE_API_KEY", "")
        self.timeout = timeout
        if not self.base_url:
            raise ValueError("INFERENCE_API_URL (or base_url) is required for live calls")

    def chat(self, model: str, messages: list[dict[str, str]], **kwargs: Any) -> str:
        import requests  # lazy: dry-run needs no deps

        url = f"{self.base_url}/v1/chat/completions"
        # Some gateways use /api/v1/… — override with full chat path via env if needed
        if os.environ.get("INFERENCE_CHAT_PATH"):
            url = self.base_url.rstrip("/") + os.environ["INFERENCE_CHAT_PATH"]
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {
            "model": model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.2),
        }
        r = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
        r.raise_for_status()
        data = r.json()
        # OpenAI shape
        if "choices" in data:
            return data["choices"][0]["message"]["content"]
        # Generic text field
        if "text" in data:
            return str(data["text"])
        if "content" in data:
            return str(data["content"])
        raise RuntimeError(f"Unrecognized response keys: {list(data)[:12]}")
