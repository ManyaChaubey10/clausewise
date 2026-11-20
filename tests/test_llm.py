from types import SimpleNamespace
from unittest.mock import patch

import pytest

from config import GEMINI_API_VERSION
from modules.llm import AnalysisError, _gemini_schema, generate_json


def test_gemini_schema_removes_unsupported_keyword_recursively():
    schema = {"type": "object", "additionalProperties": False, "properties": {
        "items": {"type": "array", "items": {"type": "object", "additionalProperties": False}}
    }}
    result = _gemini_schema(schema)
    assert "additionalProperties" not in result
    assert "additionalProperties" not in result["properties"]["items"]["items"]
    assert schema["additionalProperties"] is False


def test_generate_json_uses_v1beta_and_validates_json(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    schema = {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]}
    seen = {}

    class FakeClient:
        def __init__(self, **kwargs):
            seen["client"] = kwargs
            self.models = SimpleNamespace(generate_content=self.generate_content)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def generate_content(self, **kwargs):
            seen["request"] = kwargs
            return SimpleNamespace(text='{"ok": true}')

    with patch("modules.llm.genai.Client", FakeClient):
        assert generate_json("return ok", schema) == {"ok": True}

    assert seen["client"]["http_options"].api_version == GEMINI_API_VERSION == "v1beta"
    assert seen["client"]["http_options"].retry_options.attempts == 1
    assert seen["request"]["config"].response_mime_type == "application/json"


def test_generate_json_rejects_malformed_json(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    calls = {"count": 0}

    class FakeClient:
        def __init__(self, **kwargs):
            def generate_content(**kwargs):
                calls["count"] += 1
                return SimpleNamespace(text="not json")
            self.models = SimpleNamespace(generate_content=generate_content)

        def __enter__(self): return self
        def __exit__(self, *args): return False

    with patch("modules.llm.genai.Client", FakeClient):
        with pytest.raises(AnalysisError, match="required JSON structure"):
            generate_json("return JSON", {"type": "object"})
    assert calls["count"] == 1


def test_generate_json_does_not_retry_schema_validation_failures(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    calls = {"count": 0}

    class FakeClient:
        def __init__(self, **kwargs):
            def generate_content(**kwargs):
                calls["count"] += 1
                return SimpleNamespace(text='{"ok": "not a boolean"}')
            self.models = SimpleNamespace(generate_content=generate_content)

    with patch("modules.llm.genai.Client", FakeClient):
        with pytest.raises(AnalysisError, match="required JSON structure"):
            generate_json("return JSON", {
                "type": "object",
                "properties": {"ok": {"type": "boolean"}},
                "required": ["ok"],
            })
    assert calls["count"] == 1


@pytest.mark.parametrize("status", [400, 401, 403])
def test_generate_json_does_not_retry_permanent_api_errors(monkeypatch, status):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    calls = {"count": 0}

    class FakeAPIError(Exception):
        message = "Bad request"

        def __init__(self, code):
            self.code = code

    class FakeClient:
        def __init__(self, **kwargs):
            def generate_content(**kwargs):
                calls["count"] += 1
                raise FakeAPIError(status)
            self.models = SimpleNamespace(generate_content=generate_content)

    with patch("modules.llm.errors.APIError", FakeAPIError), \
            patch("modules.llm.genai.Client", FakeClient), \
            patch("modules.llm.time.sleep") as sleep:
        with pytest.raises(AnalysisError, match=f"HTTP {status}") as error:
            generate_json("return JSON", {"type": "object"})
    assert calls["count"] == 1
    sleep.assert_not_called()
    assert "Bad request" not in str(error.value)


@pytest.mark.parametrize("status", [429, 500, 502, 503, 504])
def test_generate_json_retries_transient_api_errors(monkeypatch, status):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    calls = {"count": 0}

    class FakeAPIError(Exception):
        def __init__(self, code):
            self.code = code
            self.message = "temporarily unavailable"
            self.response = SimpleNamespace(headers={"Retry-After": "0.25"})

    class FakeClient:
        def __init__(self, **kwargs):
            def generate_content(**kwargs):
                calls["count"] += 1
                if calls["count"] == 1:
                    raise FakeAPIError(status)
                return SimpleNamespace(text='{"ok": true}')
            self.models = SimpleNamespace(generate_content=generate_content)

    with patch("modules.llm.errors.APIError", FakeAPIError), \
            patch("modules.llm.genai.Client", FakeClient), \
            patch("modules.llm.random.uniform", return_value=0.1), \
            patch("modules.llm.time.sleep") as sleep:
        assert generate_json("return ok", {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]}) == {"ok": True}

    assert calls["count"] == 2
    sleep.assert_called_once_with(0.25)


def test_generate_json_stops_after_three_transient_failures(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    calls = {"count": 0}

    class FakeAPIError(Exception):
        code = 503
        message = "temporary service error"

    class FakeClient:
        def __init__(self, **kwargs):
            def generate_content(**kwargs):
                calls["count"] += 1
                raise FakeAPIError()
            self.models = SimpleNamespace(generate_content=generate_content)

    with patch("modules.llm.errors.APIError", FakeAPIError), \
            patch("modules.llm.genai.Client", FakeClient), \
            patch("modules.llm.random.uniform", return_value=0), \
            patch("modules.llm.time.sleep") as sleep:
        with pytest.raises(AnalysisError, match="temporarily busy or unavailable after 3 attempts") as error:
            generate_json("return JSON", {"type": "object"})

    assert calls["count"] == 3
    assert sleep.call_count == 2
    assert "test-key" not in str(error.value)


def test_generate_json_retries_temporary_network_errors(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    calls = {"count": 0}

    class FakeClient:
        def __init__(self, **kwargs):
            def generate_content(**kwargs):
                calls["count"] += 1
                if calls["count"] == 1:
                    raise ConnectionError("temporary connection failure")
                return SimpleNamespace(text='{"ok": true}')
            self.models = SimpleNamespace(generate_content=generate_content)

    with patch("modules.llm.genai.Client", FakeClient), \
            patch("modules.llm.random.uniform", return_value=0), \
            patch("modules.llm.time.sleep") as sleep:
        assert generate_json("return ok", {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]}) == {"ok": True}

    assert calls["count"] == 2
    sleep.assert_called_once_with(0)
