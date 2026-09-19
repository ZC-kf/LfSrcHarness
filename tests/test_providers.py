import sys

import httpx

from lfsrc_harness.providers import (
    AnthropicProvider,
    CliProvider,
    GeminiProvider,
    Message,
    ModelRequest,
    OllamaProvider,
    OpenAICompatibleProvider,
    ProviderConfig,
    ProviderRegistry,
)


def request() -> ModelRequest:
    return ModelRequest(messages=[Message(role="user", content="hello")])


def test_openai_compatible_provider_uses_environment_secret(monkeypatch) -> None:
    seen: dict[str, object] = {}

    def handler(http_request: httpx.Request) -> httpx.Response:
        seen["authorization"] = http_request.headers.get("authorization")
        seen["path"] = http_request.url.path
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "answer"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3},
            },
        )

    monkeypatch.setenv("FIXTURE_API_KEY", "runtime-secret")
    provider = OpenAICompatibleProvider(
        ProviderConfig(
            name="deepseek-compatible",
            base_url="https://provider.invalid/v1",
            model="fixture-model",
            api_key_env="FIXTURE_API_KEY",
        ),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    result = provider.generate(request())

    assert result.text == "answer"
    assert result.usage.total_tokens == 3
    assert seen == {"authorization": "Bearer runtime-secret", "path": "/v1/chat/completions"}
    assert "runtime-secret" not in provider.config.model_dump_json()


def test_anthropic_gemini_and_ollama_native_wire_formats(monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_KEY", "a")
    monkeypatch.setenv("GEMINI_KEY", "g")

    def handler(http_request: httpx.Request) -> httpx.Response:
        if "anthropic" in http_request.url.host:
            assert http_request.headers["x-api-key"] == "a"
            return httpx.Response(200, json={"content": [{"type": "text", "text": "anthropic"}]})
        if "gemini" in http_request.url.host:
            assert http_request.url.params["key"] == "g"
            return httpx.Response(
                200,
                json={"candidates": [{"content": {"parts": [{"text": "gemini"}]}}]},
            )
        return httpx.Response(200, json={"message": {"content": "ollama"}})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    anthropic = AnthropicProvider(
        ProviderConfig(
            name="anthropic",
            base_url="https://anthropic.invalid",
            model="claude-fixture",
            api_key_env="ANTHROPIC_KEY",
        ),
        client=client,
    )
    gemini = GeminiProvider(
        ProviderConfig(
            name="gemini",
            base_url="https://gemini.invalid",
            model="gemini-fixture",
            api_key_env="GEMINI_KEY",
        ),
        client=client,
    )
    ollama = OllamaProvider(
        ProviderConfig(
            name="ollama",
            base_url="http://ollama.invalid",
            model="local-fixture",
        ),
        client=client,
    )

    assert anthropic.generate(request()).text == "anthropic"
    assert gemini.generate(request()).text == "gemini"
    assert ollama.generate(request()).text == "ollama"


def test_cli_provider_supports_local_harness_process() -> None:
    code = (
        "import json,sys; data=json.load(sys.stdin); "
        "print(json.dumps({'text': data['messages'][0]['content']}))"
    )
    provider = CliProvider(
        ProviderConfig(name="local-cli", base_url="cli://local", model="fixture"),
        command=[sys.executable, "-c", code],
    )

    result = provider.generate(request())

    assert result.text == "hello"


def test_provider_registry_selects_configured_provider() -> None:
    registry = ProviderRegistry()
    provider = CliProvider(
        ProviderConfig(name="local", base_url="cli://local", model="fixture"),
        command=[sys.executable, "-c", 'print(\'{"text":"ok"}\')'],
    )
    registry.register(provider)

    assert registry.get("local") is provider
    assert registry.list() == ["local"]


def test_local_ollama_gateway_can_require_api_key() -> None:
    from pydantic import SecretStr

    def handler(http_request: httpx.Request) -> httpx.Response:
        assert http_request.headers["authorization"] == "Bearer local-gateway-key"
        return httpx.Response(200, json={"message": {"content": "ready"}})

    provider = OllamaProvider(
        ProviderConfig(
            name="local-gateway", base_url="http://127.0.0.1:11434",
            model="local-model", api_key=SecretStr("local-gateway-key"),
        ),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert provider.generate(request()).text == "ready"
    assert "local-gateway-key" not in provider.config.model_dump_json()
