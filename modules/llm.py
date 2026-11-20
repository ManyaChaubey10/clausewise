"""Gemini JSON generation and schema validation shared by pipeline stages."""
import json
import os
import random
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from importlib import import_module
from pathlib import Path

from google import genai
from google.genai import errors
from google.genai import types
from jsonschema import validate
from jsonschema.exceptions import ValidationError

from config import GEMINI_API_VERSION, MODEL_NAME, PROMPTS_DIR


class AnalysisError(RuntimeError):
    """A model or structured-output stage failed."""


MAX_API_ATTEMPTS = 3
RETRYABLE_HTTP_STATUSES = {429, 500, 502, 503, 504}
BACKOFF_BASE_SECONDS = 0.5
BACKOFF_MAX_SECONDS = 8.0


def _retryable_network_errors() -> tuple[type[Exception], ...]:
    """Use stdlib and whichever optional HTTP transport the SDK has installed."""
    exception_types = [TimeoutError, ConnectionError]
    for module_name in ("httpx", "httpx2"):
        try:
            transport = import_module(module_name)
        except ImportError:
            continue
        for type_name in ("TimeoutException", "ConnectError"):
            exception_type = getattr(transport, type_name, None)
            if isinstance(exception_type, type) and issubclass(exception_type, Exception):
                exception_types.append(exception_type)
    return tuple(dict.fromkeys(exception_types))


RETRYABLE_NETWORK_ERRORS = _retryable_network_errors()


def load_prompt(filename: str) -> str:
    # Prompts are stored with visible escaped newlines for easy editing in demos.
    return (PROMPTS_DIR / filename).read_text(encoding="utf-8").replace("\\n", "\n")


def render_prompt(filename: str, **values) -> str:
    # Replace only named tokens; JSON examples in prompt text contain literal braces.
    prompt = load_prompt(filename)
    return re.sub(r"\{([a-z_]+)\}", lambda match: str(values.get(match.group(1), match.group(0))), prompt)


def generate_json(prompt: str, schema: dict) -> dict:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or api_key == "your_api_key_here":
        raise AnalysisError("Gemini API key is missing. Add GEMINI_API_KEY to your .env file.")
    try:
        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                api_version=GEMINI_API_VERSION,
                # Make this wrapper the sole retry layer; otherwise SDK-level
                # transport retries could exceed MAX_API_ATTEMPTS.
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )
        request_config = types.GenerateContentConfig(
            response_mime_type="application/json",
            # Gemini's response_schema supports a JSON Schema subset and rejects
            # additionalProperties. Keep strict validation locally below, while
            # sending only the supported schema fields to the API.
            response_schema=_gemini_schema(schema),
        )
        response = _generate_with_retry(client, prompt, request_config)
        raw = response.text or ""
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.I)
        result = json.loads(raw)
        validate(instance=result, schema=schema)
        return result
    except (json.JSONDecodeError, ValidationError) as exc:
        raise AnalysisError(f"Gemini returned output that did not match the required JSON structure: {exc}") from exc
    except AnalysisError:
        raise
    except Exception as exc:
        raise AnalysisError(f"Gemini analysis failed: {exc}") from exc


def _generate_with_retry(client, prompt: str, request_config):
    """Retry only known transient transport/API failures, at most three times."""
    for attempt in range(1, MAX_API_ATTEMPTS + 1):
        try:
            return client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=request_config,
            )
        except errors.APIError as exc:
            if exc.code not in RETRYABLE_HTTP_STATUSES:
                raise _permanent_api_error(exc) from exc
            if attempt == MAX_API_ATTEMPTS:
                raise AnalysisError(
                    "Gemini is temporarily busy or unavailable after "
                    f"{MAX_API_ATTEMPTS} attempts. Please try again shortly."
                ) from exc
            _wait_before_retry(attempt, exc)
        except RETRYABLE_NETWORK_ERRORS as exc:
            if attempt == MAX_API_ATTEMPTS:
                raise AnalysisError(
                    "Gemini could not be reached after "
                    f"{MAX_API_ATTEMPTS} attempts because of a temporary network problem. "
                    "Check your connection and try again."
                ) from exc
            _wait_before_retry(attempt)


def _wait_before_retry(attempt: int, error=None) -> None:
    """Use full-jitter exponential backoff, honoring Retry-After as a minimum."""
    ceiling = min(BACKOFF_MAX_SECONDS, BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)))
    delay = random.uniform(0, ceiling)
    retry_after = _retry_after_seconds(error) if error is not None else None
    if retry_after is not None:
        delay = max(delay, retry_after)
    time.sleep(delay)


def _retry_after_seconds(error) -> float | None:
    response = getattr(error, "response", None)
    headers = getattr(response, "headers", None)
    if not headers:
        return None
    value = headers.get("Retry-After")
    if value is None:
        return None
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        try:
            retry_at = parsedate_to_datetime(value)
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=timezone.utc)
            return max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())
        except (TypeError, ValueError, OverflowError):
            return None


def _permanent_api_error(exc) -> AnalysisError:
    status = getattr(exc, "code", None)
    status_text = f" (HTTP {status})" if status else ""
    if status in {401, 403}:
        message = f"Gemini authentication failed{status_text}. Check that GEMINI_API_KEY is valid."
    else:
        message = f"Gemini rejected the request{status_text}. Check the model and request configuration."
    return AnalysisError(message)


def _gemini_schema(schema: dict) -> dict:
    """Return a copy containing only the JSON Schema keywords Gemini accepts."""
    if isinstance(schema, list):
        return [_gemini_schema(item) for item in schema]
    if not isinstance(schema, dict):
        return schema
    return {
        key: _gemini_schema(value)
        for key, value in schema.items()
        if key != "additionalProperties"
    }
