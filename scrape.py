"""
Module for making synchronous calls to Olostep's API with rate limiting.
"""

import os
from typing import Literal, Optional

import requests
from ratelimit import limits, sleep_and_retry
from dotenv import load_dotenv

load_dotenv()

# Configure rate limiting: Maximum 10 calls per minute
MAX_CALLS = 10
PERIOD = 60  # in seconds


@sleep_and_retry
@limits(calls=MAX_CALLS, period=PERIOD)
def scrape_url(
    url: str,
    format: Literal["markdown", "html"] = "markdown",
    wait_ms: int = 1000,
    timeout: int = 60,
) -> Optional[str]:
    """
    Make a synchronous call to Olostep's API with rate limiting.

    Parameters
    ----------
    url : str
        The URL to scrape
    format : Literal["markdown", "html"], optional
        The format to return the content in, by default "markdown"
    wait_ms : int, optional
        Time to wait before scraping in milliseconds, by default 1000
    timeout : int, optional
        Timeout in seconds for the request, by default 60

    Returns
    -------
    Optional[str]
        The scraped content if successful, None if failed

    Raises
    ------
    requests.exceptions.RequestException
        If the API call fails
    """
    api_url = "https://api.olostep.com/v1/scrapes"
    headers = {
        "Authorization": f"Bearer {os.getenv('OLOSTEP_API_KEY')}",
        "Content-Type": "application/json",
    }

    payload = {
        "url_to_scrape": url,
        "formats": [format],
        "wait_before_scraping": wait_ms,
    }

    response = requests.post(
        api_url,
        headers=headers,
        json=payload,
        timeout=timeout,
    )
    response.raise_for_status()
    
    data = response.json()
    return data["result"].get(f"{format}_content")


if __name__ == "__main__":
    try:
        test_url = "https://www.lincolncenter.org/lincoln-center-at-home/page/annual-donor-list"
        content = scrape_url(test_url)
        if content:
            print("Successfully scraped content:")
            print(content[:500] + "...")
        else:
            print("Failed to scrape content")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
