import os
from typing import List, Dict, Any
import requests
from app.config import SERPAPI_API_KEY, TAVILY_API_KEY


def search_web(query: str, max_results: int = 5, constraints: Dict[str, Any] | None = None) -> List[str]:
    constraints = constraints or {}
    provider = _select_provider(constraints)
    if provider == "serpapi" and SERPAPI_API_KEY:
        return _serpapi_search(query, max_results)
    if provider == "tavily" and TAVILY_API_KEY:
        return _tavily_search(query, max_results)
    if SERPAPI_API_KEY:
        return _serpapi_search(query, max_results)
    if TAVILY_API_KEY:
        return _tavily_search(query, max_results)
    return _duckduckgo_search(query, max_results)


def _serpapi_search(query: str, max_results: int) -> List[str]:
    params = {
        "engine": "google",
        "q": query,
        "api_key": SERPAPI_API_KEY,
    }
    res = requests.get("https://serpapi.com/search.json", params=params, timeout=15)
    res.raise_for_status()
    data = res.json()
    results = data.get("organic_results", [])
    return [item.get("link") for item in results if item.get("link")][:max_results]


def _tavily_search(query: str, max_results: int) -> List[str]:
    payload = {"query": query, "max_results": max_results}
    res = requests.post(
        "https://api.tavily.com/search",
        json=payload,
        headers={"Authorization": f"Bearer {TAVILY_API_KEY}"},
        timeout=15,
    )
    res.raise_for_status()
    data = res.json()
    results = data.get("results", [])
    return [item.get("url") for item in results if item.get("url")][:max_results]


def _duckduckgo_search(query: str, max_results: int) -> List[str]:
    params = {"q": query}
    res = requests.get("https://duckduckgo.com/html/", params=params, timeout=15)
    res.raise_for_status()
    html = res.text
    links = []
    for part in html.split('href="'):
        if part.startswith("http"):
            links.append(part.split('"')[0])
    cleaned = [link for link in links if "duckduckgo.com" not in link]
    return cleaned[:max_results]


def _select_provider(constraints: Dict[str, Any]) -> str:
    source_types = set(constraints.get("source_types", []) or [])
    if "peer_reviewed" in source_types or "preprint" in source_types:
        return "serpapi"
    if "news" in source_types:
        return "tavily"
    return "duckduckgo"
