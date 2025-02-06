"""
Module for interacting with the Serper API to fetch search engine results pages (SERPs) synchronously.
"""

import os
import urllib.parse
from collections.abc import Sequence
from typing import Optional

import requests
from pydantic import BaseModel
from ratelimit import limits, sleep_and_retry

from dotenv import load_dotenv
load_dotenv()

# Configure rate limiting: Maximum 10 calls per 1 second.
MAX_CALLS = 10
PERIOD = 1


class SerpedSite(BaseModel):
    url: str
    title: str
    snippet: str
    rich_snippet: Optional[list[str]] = None
    source: Optional[str] = None


@sleep_and_retry
@limits(calls=MAX_CALLS, period=PERIOD)
def fetch_serper(
    session: requests.Session,
    query: str,
    num_sites_per_query: int,
) -> list[SerpedSite]:
    """
    Query the SERP API for a single search query and return a list of sites.

    Parameters
    ----------
    session : requests.Session
        The HTTP session used for the API request.
    query : str
        The URL-encoded search query.
    num_sites_per_query : int
        Maximum number of sites to retrieve for the query.

    Returns
    -------
    List[SerpedSite]
        A list of SerpedSite objects retrieved from the API.

    Raises
    ------
    Exception
        Propagates any exception encountered during the API call.
    """
    url = "https://google.serper.dev/search"
    payload = {
        "q": query,
        "gl": "us",
        "type": "search",
        "includeSubtitle": True,
        "engine": "google",
    }
    headers = {
        "Content-Type": "application/json",
        "X-API-KEY": os.getenv("SERPER_API_KEY"),
    }

    response = session.post(url, headers=headers, json=payload, timeout=10.0)
    response.raise_for_status()
    data = response.json()

    sites: list[SerpedSite] = []
    for site_data in data.get("organic", [])[:num_sites_per_query]:
        site = SerpedSite(
            url=site_data.get("link", ""),
            title=site_data.get("title", ""),
            snippet=site_data.get("snippet", "") if "snippet" in site_data else "",
            source=site_data.get("source", ""),
        )
        sites.append(site)

    return sites


def fetch_serper_batch_by_limit(
    queries: list[str],
    num_sites_per_query: int,
) -> list[list[SerpedSite | Exception]]:
    """Fetch SERP data for a batch of search queries.

    Parameters
    ----------
    queries : list[str]
        List of URL-encoded search queries.
    num_sites_per_query : int
        Maximum number of sites to retrieve per query.

    Returns
    -------
    list[list[SerpedSite | Exception]]
        A list of lists where each element is a list of SerpedSite objects for a query
        or an Exception if that call failed.
    """
    results: list[list[SerpedSite | Exception]] = []
    with requests.Session() as session:
        session.headers.update({"Content-Type": "application/json"})
        for query in queries:
            try:
                sites = fetch_serper(
                    session=session,
                    query=query,
                    num_sites_per_query=num_sites_per_query,
                )
                results.append(sites)
            except Exception as e:
                results.append(e)
    return results


def get_in_factor_order(lists: list[list[SerpedSite]]) -> list[SerpedSite]:
    """Reorder a list of lists by interlacing their elements.

    For example, given [[a, b], [c, d, e]], the result will be [a, c, b, d, e].

    Parameters
    ----------
    lists : List[List[SerpedSite]]
        A list of lists containing SerpedSite objects.

    Returns
    -------
    list[SerpedSite]
        A single list with elements taken in alternating order from each sublist.
    """
    max_len = max(len(lst) for lst in lists) if lists else 0
    result: list[SerpedSite] = []
    for i in range(max_len):
        for lst in lists:
            if i < len(lst):
                result.append(lst[i])
    return result


def serp_and_process(
    search_queries: Sequence[str],
    num_sites_per_query: int,
) -> list[SerpedSite]:
    """Execute search queries against the SERP API and process the results.

    This function URL-encodes the search queries, retrieves the SERP data,
    logs any errors, interlaces the results from all queries, and deduplicates them.

    Parameters
    ----------
    search_queries : Sequence[str]
        List of search queries.
    num_sites_per_query : int
        Maximum number of sites to retrieve per query.
    logger : logging.Logger
        Logger for recording any errors.
    timeout : float, optional
        Timeout for each API request in seconds (default is 60).

    Returns
    -------
    List[SerpedSite]
        A flattened and deduplicated list of SerpedSite objects from all queries.
    """
    # URL-encode the search queries.
    encoded_queries = [urllib.parse.quote_plus(query) for query in search_queries]
    results = fetch_serper_batch_by_limit(
        queries=encoded_queries,
        num_sites_per_query=num_sites_per_query,
    )

    fetched_sites_lists: list[list[SerpedSite]] = []
    for idx, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"The search query '{search_queries[idx]}' failed. Error: {str(result)}")
        else:
            fetched_sites_lists.append(result)

    # Interlace results from different queries.
    if fetched_sites_lists:
        interlaced_sites = get_in_factor_order(fetched_sites_lists)
        # Deduplicate while preserving order based on the site URL.
        seen = set()
        deduped_sites = []
        for site in interlaced_sites:
            if site.url not in seen:
                seen.add(site.url)
                deduped_sites.append(site)
        return deduped_sites
    else:
        return []


if __name__ == "__main__":
    try:
        sites = serp_and_process(
            search_queries=["DonorAtlas"],
            num_sites_per_query=10,
        )
        for site in sites:
            print(f"Site: {site.url}, Source: {site.source}, Snippet: {site.snippet}")
    except Exception as e:
        print(f"An error occurred during processing: {str(e)}")
