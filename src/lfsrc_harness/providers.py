"""Provider-neutral AI model plugins for cloud and local runtimes."""

from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Iterator
from typing import Any, Protocol

import httpx
from pydantic import BaseModel, Field, SecretStr


class Message(BaseModel):
    role: str
    content: str


class ModelRequest(BaseModel):
    messages: list[Message] = Field(min_length=1)
    temperature: float = Field(default=0.2, ge=0, le=2)
    max_tokens: int = Field(default=2048, gt=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ModelResponse(BaseModel):
    text: str
    finish_reason: str | None = None
    usage: TokenUsage = Field(default_factory=TokenUsage)
    raw: dict[str, Any] = Field(default_factory=dict)


class ProviderConfig(BaseModel):
    name: str
    base_url: str
    model: str
    api_key_env: str | None = None
    api_key: SecretStr | None = Field(default=None, exclude=True, repr=False)
    timeout_seconds: float = Field(default=120, gt=0)
    headers: dict[str, str] = Field(default_factory=dict)


class ModelProvider(Protocol):
    config: ProviderConfig

    def generate(self, request: ModelRequest) -> ModelResponse: ...

    def stream(self, request: ModelRequest) -> Iterator[str]: ...

    def health(self) -> bool: ...


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, ModelProvider] = {}

    def register(self, provider: ModelProvider) -> None:
        name = provider.config.name
        if name in self._providers:
            raise ValueError(f"provider {name!r} is already registered")
        self._providers[name] = provider

    def get(self, name: str) -> ModelProvider:
        return self._providers[name]

    def list(self) -> list[str]:
        return sorted(self._providers)


class _HttpProvider:
    def __init__(self, config: ProviderConfig, *, client: httpx.Client | None = None) -> None:
        self.config = config
        self.client = client or httpx.Client(timeout=config.timeout_seconds)

    def stream(self, request: ModelRequest) -> Iterator[str]:
        yield self.generate(request).text

    def generate(self, request: ModelRequest) -> ModelResponse:
        raise NotImplementedError

    def health(self) -> bool:
        try:
            response = self.client.get(
                self.config.base_url, timeout=min(self.config.timeout_seconds, 5)
            )
            return response.status_code < 500
        except httpx.HTTPError:
            return False

    def _api_key(self) -> str | None:
        if self.config.api_key is not None:
            return self.config.api_key.get_secret_value()
        if self.config.api_key_env is None:
            return None
        value = os.environ.get(self.config.api_key_env)
        if not value:
            raise RuntimeError(
                f"required secret environment variable is not set: {self.config.api_key_env}"
            )
        return value


class OpenAICompatibleProvider(_HttpProvider):
    """Covers compatible cloud gateways and local servers such as vLLM/LM Studio."""

    def generate(self, request: ModelRequest) -> ModelResponse:
        headers = dict(self.config.headers)
        key = self._api_key()
        if key:
            headers["Authorization"] = f"Bearer {key}"
        response = self.client.post(
            f"{self.config.base_url.rstrip('/')}/chat/completions",
            headers=headers,
            json={
                "model": self.config.model,
                "messages": [message.model_dump() for message in request.messages],
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
            },
            timeout=self.config.timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
        choice = data["choices"][0]
        return ModelResponse(
            text=str(choice["message"]["content"]),
            finish_reason=choice.get("finish_reason"),
            usage=TokenUsage.model_validate(data.get("usage", {})),
            raw=data,
        )


class AnthropicProvider(_HttpProvider):
    def generate(self, request: ModelRequest) -> ModelResponse:
        key = self._api_key()
        messages = [
            message.model_dump() for message in request.messages if message.role != "system"
        ]
        system = "\n".join(
            message.content for message in request.messages if message.role == "system"
        )
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }
        if system:
            payload["system"] = system
        response = self.client.post(
            f"{self.config.base_url.rstrip('/')}/v1/messages",
            headers={
                **self.config.headers,
                "x-api-key": key or "",
                "anthropic-version": "2023-06-01",
            },
            json=payload,
            timeout=self.config.timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
        text = "".join(item.get("text", "") for item in data.get("content", []))
        usage = data.get("usage", {})
        prompt = int(usage.get("input_tokens", 0))
        completion = int(usage.get("output_tokens", 0))
        return ModelResponse(
            text=text,
            finish_reason=data.get("stop_reason"),
            usage=TokenUsage(
                prompt_tokens=prompt,
                completion_tokens=completion,
                total_tokens=prompt + completion,
            ),
            raw=data,
        )


class GeminiProvider(_HttpProvider):
    def generate(self, request: ModelRequest) -> ModelResponse:
        key = self._api_key()
        contents = [
            {
                "role": "model" if message.role == "assistant" else "user",
                "parts": [{"text": message.content}],
            }
            for message in request.messages
            if message.role != "system"
        ]
        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": request.temperature,
                "maxOutputTokens": request.max_tokens,
            },
        }
        system = "\n".join(
            message.content for message in request.messages if message.role == "system"
        )
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
        response = self.client.post(
            f"{self.config.base_url.rstrip('/')}/v1beta/models/{self.config.model}:generateContent",
            params={"key": key or ""},
            headers=self.config.headers,
            json=payload,
            timeout=self.config.timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
        candidate = data["candidates"][0]
        text = "".join(part.get("text", "") for part in candidate["content"]["parts"])
        usage = data.get("usageMetadata", {})
        return ModelResponse(
            text=text,
            finish_reason=candidate.get("finishReason"),
            usage=TokenUsage(
                prompt_tokens=int(usage.get("promptTokenCount", 0)),
                completion_tokens=int(usage.get("candidatesTokenCount", 0)),
                total_tokens=int(usage.get("totalTokenCount", 0)),
            ),
            raw=data,
        )


class OllamaProvider(_HttpProvider):
    def generate(self, request: ModelRequest) -> ModelResponse:
        headers = dict(self.config.headers)
        key = self._api_key()
        if key:
            headers["Authorization"] = f"Bearer {key}"
        response = self.client.post(
            f"{self.config.base_url.rstrip('/')}/api/chat",
            headers=headers,
            json={
                "model": self.config.model,
                "messages": [message.model_dump() for message in request.messages],
                "stream": False,
                "options": {"temperature": request.temperature, "num_predict": request.max_tokens},
            },
            timeout=self.config.timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
        prompt = int(data.get("prompt_eval_count", 0))
        completion = int(data.get("eval_count", 0))
        return ModelResponse(
            text=str(data["message"]["content"]),
            finish_reason="stop" if data.get("done", True) else None,
            usage=TokenUsage(
                prompt_tokens=prompt,
                completion_tokens=completion,
                total_tokens=prompt + completion,
            ),
            raw=data,
        )


class CliProvider:
    def __init__(self, config: ProviderConfig, *, command: list[str]) -> None:
        if not command:
            raise ValueError("CLI provider command must not be empty")
        self.config = config
        self.command = command

    def generate(self, request: ModelRequest) -> ModelResponse:
        completed = subprocess.run(
            self.command,
            input=request.model_dump_json(),
            capture_output=True,
            text=True,
            timeout=self.config.timeout_seconds,
            check=False,
            shell=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or "CLI provider failed")
        data = json.loads(completed.stdout)
        return ModelResponse(text=str(data["text"]), raw=data)

    def stream(self, request: ModelRequest) -> Iterator[str]:
        yield self.generate(request).text

    def health(self) -> bool:
        return bool(self.command)
