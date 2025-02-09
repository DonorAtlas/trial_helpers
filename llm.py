"""
Module for making synchronous calls to OpenAI's API with rate limiting.
"""

import os
import json
from typing import Any, Optional, Union

import requests
from ratelimit import limits, sleep_and_retry
from dotenv import load_dotenv

load_dotenv()

# Configure rate limiting: Maximum 10 calls per minute
MAX_CALLS = 10
PERIOD = 60  # in seconds


@sleep_and_retry
@limits(calls=MAX_CALLS, period=PERIOD)
def call_llm(
    system_prompt: str,
    user_prompt: str,
    model: str = "gpt-4o-mini",
    max_tokens: int = 8192,
    temperature: float = 1.0,
    schema: Optional[dict[str, Any]] = None,
) -> Union[str, dict[str, Any]]:
    """
    Make a synchronous call to OpenAI's API with rate limiting.

    Parameters
    ----------
    system_prompt : str
        The system message to provide context to the model.
    user_prompt : str
        The user message/prompt to generate content from.
    model : str, optional
        The OpenAI model to use, by default "gpt-4o-mini"
    max_tokens : int, optional
        Maximum number of tokens in the response, by default 8192
    temperature : float, optional
        Controls randomness in the response (0.0 to 1.0), by default 0.0
    schema : Optional[dict[str, Any]], optional
        JSON schema for structured output, by default None

    Returns
    -------
    Union[str, dict[str, Any]]
        If schema is None, returns the model's response as a string.
        If schema is provided, returns the response as a dictionary.

    Raises
    ------
    requests.exceptions.RequestException
        If the API call fails
    json.JSONDecodeError
        If the response cannot be parsed as JSON when schema is provided
    """
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "response", "schema": schema},
        }
        if schema
        else {"type": "text"},
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    response = requests.post(url, headers=headers, json=payload, timeout=300)
    response.raise_for_status()

    content = response.json()["choices"][0]["message"]["content"]

    if schema is not None:
        return json.loads(content)
    return content


if __name__ == "__main__":
    try:
        # Example usage without schema (returns string)
        response = call_llm(
            system_prompt="You are a helpful assistant.",
            user_prompt="What is the capital of France?",
        )
        print("Text response:", response)

        # Example usage with schema (returns dictionary)
        schema = {
            "type": "object",
            "properties": {
                "capital": {"type": "string"},
                "country": {"type": "string"},
            },
            "required": ["capital", "country"],
        }
        structured_response = call_llm(
            system_prompt="You are a helpful assistant.",
            user_prompt="What is the capital of France?",
            schema=schema,
        )
        print("\nStructured response:", structured_response)
    except Exception as e:
        print(f"An error occurred: {str(e)}")
