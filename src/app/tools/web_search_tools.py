import os
import re
import sys
import time
import traceback
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx
from bs4 import BeautifulSoup
from langchain_core.tools import tool


@dataclass
class SearchResult:
    title: str
    link: str
    snippet: str
    position: int


class RateLimiter:
    def __init__(self, requests_per_minute: int = 30):
        self.requests_per_minute = requests_per_minute
        self.requests = []

    def acquire(self):
        now = datetime.now()
        # Remove requests older than 1 minute
        self.requests = [
            req for req in self.requests if now - req < timedelta(minutes=1)
        ]

        if len(self.requests) >= self.requests_per_minute:
            # Calculate wait time until the oldest request expires
            oldest_request = self.requests[0]
            wait_time = (oldest_request + timedelta(minutes=1) - now).total_seconds()
            if wait_time > 0:
                time.sleep(wait_time)  # Use time.sleep for synchronous code

        self.requests.append(now)


class SerperSearcher:
    BASE_URL = "https://google.serper.dev/search"

    def __init__(self):
        self.api_key = os.getenv("SERPER_API_KEY")
        if not self.api_key:
            raise ValueError("SERPER_API_KEY environment variable is not set")

        self.headers = {"X-API-KEY": self.api_key, "Content-Type": "application/json"}
        # Conservative rate limiting for free tier (100 requests/month)
        self.rate_limiter = RateLimiter(
            requests_per_minute=5
        )  # 1 request every 12 seconds

    def format_results_for_llm(self, results: List[SearchResult]) -> str:
        """Format results in a natural language style that's easier for LLMs to process"""
        if not results:
            return "No results were found for your search query. This could be due to API limitations or the query returned no matches. Please try rephrasing your search."

        output = []
        output.append(f"Found {len(results)} search results:\n")

        for result in results:
            output.append(f"{result.position}. {result.title}")
            output.append(f"   URL: {result.link}")
            output.append(f"   Summary: {result.snippet}")
            output.append("")  # Empty line between results

        return "\n".join(output)

    def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        try:
            # Apply rate limiting
            self.rate_limiter.acquire()

            payload = {"q": query, "num": max_results}

            with httpx.Client() as client:
                response = client.post(
                    self.BASE_URL, json=payload, headers=self.headers, timeout=30.0
                )
                response.raise_for_status()
                data = response.json()

            # Handle API errors
            if "error" in data:
                print(f"Serper API error: {data['error']}", file=sys.stderr)
                return []

            # Parse organic results
            results = []
            organic_results = data.get("organic", [])
            for i, result in enumerate(organic_results[:max_results]):
                results.append(
                    SearchResult(
                        title=result.get("title", "No title"),
                        link=result.get("link", ""),
                        snippet=result.get("snippet", "No snippet available"),
                        position=i + 1,
                    )
                )

            return results

        except httpx.TimeoutException:
            print("Request to Serper API timed out", file=sys.stderr)
            return []
        except httpx.HTTPStatusError as e:
            print(
                f"HTTP error occurred: {e.response.status_code} - {e.response.text}",
                file=sys.stderr,
            )
            return []
        except Exception as e:
            traceback.print_exc(file=sys.stderr)
            return []


class WebContentFetcher:
    def __init__(self):
        self.rate_limiter = RateLimiter(requests_per_minute=20)

    def fetch_and_parse(self, url: str) -> str:
        """Fetch and parse content from a webpage"""
        try:
            self.rate_limiter.acquire()

            with httpx.Client() as client:
                response = client.get(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    },
                    follow_redirects=True,
                    timeout=30.0,
                )
                response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            for element in soup(
                [
                    "script",
                    "style",
                    "nav",
                    "header",
                    "footer",
                    "iframe",
                    "noscript",
                    "aside",
                    "form",
                ]
            ):
                element.decompose()

            main_content = (
                soup.find("main")
                or soup.find("article")
                or soup.find(id=re.compile("content|main|article", re.I))
                or soup.find(class_=re.compile("content|main|article", re.I))
                or soup.body
            )

            if main_content:
                text = main_content.get_text(separator=" ", strip=True)
            else:
                text = soup.get_text(separator=" ", strip=True)

            text = re.sub(r"\s+", " ", text).strip()
            text = re.sub(r"[^\x00-\x7F]+", " ", text)

            if len(text) > 10000:
                text = text[:10000] + "... [content truncated]"

            return text

        except httpx.TimeoutException:
            return "Error: Request timed out while fetching webpage."
        except httpx.HTTPError as e:
            return f"Error: HTTP error occurred ({str(e)})"
        except Exception as e:
            return f"Error: Unexpected error occurred ({str(e)})"


try:
    searcher = SerperSearcher()
except ValueError as e:
    print(f"Search initialization failed: {str(e)}", file=sys.stderr)
    searcher = None

fetcher = WebContentFetcher()


class DuckDuckGoSearcher:
    BASE_URL = "https://html.duckduckgo.com/html"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    def __init__(self):
        self.rate_limiter = RateLimiter()

    def format_results_for_llm(self, results: List[SearchResult]) -> str:
        """Format results in a natural language style that's easier for LLMs to process"""
        if not results:
            return "No results were found for your search query. This could be due to DuckDuckGo's bot detection or the query returned no matches. Please try rephrasing your search or try again in a few minutes."

        output = []
        output.append(f"Found {len(results)} search results:\n")

        for result in results:
            output.append(f"{result.position}. {result.title}")
            output.append(f"   URL: {result.link}")
            output.append(f"   Summary: {result.snippet}")
            output.append("")  # Empty line between results

        return "\n".join(output)


@tool(parse_docstring=True)
def search(query: str, max_results: int = 10) -> str:
    """
    Search the web using Serper.dev API and return formatted results.

    Args:
        query: The search query string
        max_results: Maximum number of results to return (default: 10)
    """
    if searcher is None:
        return "Search service is not available. Please check your SERPER_API_KEY environment variable."

    try:
        results = searcher.search(query, max_results)
        return searcher.format_results_for_llm(results)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        return f"An error occurred while searching: {str(e)}"


@tool(parse_docstring=True)
def fetch_content(url: str) -> str:
    """
    Fetch and parse content from a webpage URL.

    Args:
        url: The webpage URL to fetch content from
    """
    return fetcher.fetch_and_parse(url)
