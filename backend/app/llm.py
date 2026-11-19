import json
from openai import OpenAI
from openai import APIConnectionError, APITimeoutError, AuthenticationError, BadRequestError, RateLimitError
from .config import NEXUS_API_KEY, NEXUS_BASE_URL, NEXUS_MODEL


def ask_json(system: str, prompt: str) -> dict:
    if not NEXUS_API_KEY:
        raise RuntimeError("NEXUS_API_KEY missing. Add your Nexus key to the .env file in the BLINDSPOT_AI main folder.")
    try:
        client = OpenAI(api_key=NEXUS_API_KEY, base_url=NEXUS_BASE_URL, timeout=240.0, max_retries=2)
        response = client.chat.completions.create(
            model=NEXUS_MODEL,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        raw = response.choices[0].message.content
        if not raw:
            raise RuntimeError("Nexus API returned an empty response. Please retry.")
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise RuntimeError("AI response must be a JSON object. Please retry.")
        return result
    except AuthenticationError as exc:
        raise RuntimeError("Nexus API authentication failed. Check the API key in your local .env file.") from exc
    except RateLimitError as exc:
        raise RuntimeError("Nexus API rate limit or quota reached. Check your Nexus account and try again later.") from exc
    except APITimeoutError as exc:
        raise RuntimeError("Nexus API request timed out. Please retry.") from exc
    except APIConnectionError as exc:
        raise RuntimeError("Cannot connect to Nexus API. Check your internet connection and Nexus base URL.") from exc
    except BadRequestError as exc:
        raise RuntimeError(f"Nexus API rejected the request. Check the model name and API settings. Details: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError("AI returned invalid JSON. Please retry the analysis.") from exc
