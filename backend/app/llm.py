
import json
import re

from openai import OpenAI
from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    RateLimitError,
)

from .config import NEXUS_API_KEY, NEXUS_BASE_URL, NEXUS_MODEL


def get_client():
    if not NEXUS_API_KEY:
        raise RuntimeError(
            "NEXUS_API_KEY missing. Check your main .env file."
        )

    return OpenAI(
        api_key=NEXUS_API_KEY,
        base_url=NEXUS_BASE_URL,
        timeout=240.0,
        max_retries=2,
    )


def handle_api_errors(exc):
    if isinstance(exc, AuthenticationError):
        raise RuntimeError("Nexus API authentication failed. Check your API key.") from exc
    if isinstance(exc, RateLimitError):
        raise RuntimeError("Nexus API quota or rate limit reached.") from exc
    if isinstance(exc, APITimeoutError):
        raise RuntimeError("Nexus API request timed out. Please retry.") from exc
    if isinstance(exc, APIConnectionError):
        raise RuntimeError("Cannot connect to Nexus API. Check internet connection.") from exc
    if isinstance(exc, BadRequestError):
        raise RuntimeError(f"Nexus API rejected the request: {exc}") from exc
    raise RuntimeError(f"AI request failed: {exc}") from exc


def parse_json_response(raw: str) -> dict:
    if not raw or not raw.strip():
        raise RuntimeError("Nexus API returned an empty response.")

    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        result = json.loads(cleaned)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()

    for index, char in enumerate(cleaned):
        if char == "{":
            try:
                result, _ = decoder.raw_decode(cleaned[index:])
                if isinstance(result, dict):
                    return result
            except json.JSONDecodeError:
                continue

    raise RuntimeError(
        "AI response did not contain valid JSON. Please retry the analysis."
    )


def ask_json(system: str, prompt: str) -> dict:
    try:
        client = get_client()

        response = client.chat.completions.create(
            model=NEXUS_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": system + "\nReturn ONLY one valid JSON object. "
                    "Do not include Markdown or explanations."
                },
                {
                    "role": "user",
                    "content": prompt
                },
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )

        raw = response.choices[0].message.content
        return parse_json_response(raw)

    except (
        AuthenticationError,
        RateLimitError,
        APITimeoutError,
        APIConnectionError,
        BadRequestError,
    ) as exc:
        handle_api_errors(exc)


def ask_text(system: str, prompt: str) -> str:
    """Generate a normal text response for the project chat assistant."""
    try:
        client = get_client()

        response = client.chat.completions.create(
            model=NEXUS_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )

        answer = response.choices[0].message.content

        if not answer or not answer.strip():
            raise RuntimeError("AI returned an empty answer.")

        return answer.strip()

    except (
        AuthenticationError,
        RateLimitError,
        APITimeoutError,
        APIConnectionError,
        BadRequestError,
    ) as exc:
        handle_api_errors(exc)
