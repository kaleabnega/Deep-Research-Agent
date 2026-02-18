import requests
from bs4 import BeautifulSoup
from typing import Dict


def fetch_page(url: str, timeout: int = 15, max_chars: int = 2000) -> Dict[str, str]:
    res = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
    res.raise_for_status()
    content_type = res.headers.get("Content-Type", "")
    text = res.text
    title = ""
    if "text/html" in content_type:
        soup = BeautifulSoup(text, "html.parser")
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
    return {"title": title or url, "content": text[:max_chars]}
