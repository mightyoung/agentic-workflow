#!/usr/bin/env python3
"""
Search Adapter for RESEARCH phase - Real web search integration

Provides actual web search capabilities for the RESEARCH phase, with fallback
to template-based findings when search is unavailable.
"""

import subprocess
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from urllib.parse import quote_plus


@dataclass
class SearchResult:
    """Single search result"""
    title: str
    url: str
    snippet: str
    source: str


@dataclass
class SearchResponse:
    """Complete search response"""
    query: str
    results: List[SearchResult]
    total_results: int
    search_engine: str
    error: Optional[str] = None

    @property
    def has_results(self) -> bool:
        return len(self.results) > 0 and self.error is None


def _search_ddg(query: str, num_results: int = 5) -> SearchResponse:
    """Search using DuckDuckGo HTML (no API key required)"""
    try:
        # Properly URL-encode the query
        encoded_query = quote_plus(query)
        cmd = [
            "curl", "-s", "--max-time", "10",
            f"https://html.duckduckgo.com/html/?q={encoded_query}"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode != 0:
            return SearchResponse(query=query, results=[], total_results=0, search_engine="duckduckgo",
                               error=f"Curl failed with code {result.returncode}")

        html = result.stdout
        results = []
        # Simple HTML parsing for DuckDuckGo results
        lines = html.split('\n')
        for i, line in enumerate(lines):
            if '<a class="result__a"' in line:
                # Extract URL
                url_start = line.find('href="') + 6
                url_end = line.find('"', url_start)
                if url_start > 5 and url_end > url_start:
                    url = line[url_start:url_end]
                else:
                    continue

                # Extract title from next few lines
                title = ""
                for j in range(i, min(i+5, len(lines))):
                    if '<a class="result__a"' in lines[j]:
                        title_start = lines[j].find('>') + 1
                        title_end = lines[j].find('</a>')
                        if title_start > 0 and title_end > title_start:
                            title = lines[j][title_start:title_end].strip()
                        break

                # Extract snippet
                snippet = ""
                for j in range(i, min(i+10, len(lines))):
                    if '<a class="result__snippet"' in lines[j]:
                        snippet_start = lines[j].find('>') + 1
                        snippet_end = lines[j].find('</a>')
                        if snippet_start > 0 and snippet_end > snippet_start:
                            snippet = lines[j][snippet_start:snippet_end].strip()
                        break

                if title and url:
                    # Clean HTML tags from title and snippet
                    import re
                    title = re.sub(r'<[^>]+>', '', title)
                    snippet = re.sub(r'<[^>]+>', '', snippet)
                    results.append(SearchResult(title=title, url=url, snippet=snippet, source="web"))
                    if len(results) >= num_results:
                        break

        return SearchResponse(query=query, results=results, total_results=len(results), search_engine="duckduckgo")
    except subprocess.TimeoutExpired:
        return SearchResponse(query=query, results=[], total_results=0, search_engine="duckduckgo",
                           error="Search timeout")
    except Exception as e:
        return SearchResponse(query=query, results=[], total_results=0, search_engine="duckduckgo",
                           error=str(e))


def _search_exa(query: str, num_results: int = 5) -> SearchResponse:
    """Search using Exa API (if EXA_API_KEY is set)"""
    import os
    api_key = os.environ.get("EXA_API_KEY")
    if not api_key:
        return SearchResponse(query=query, results=[], total_results=0, search_engine="exa",
                           error="EXA_API_KEY not set")

    try:
        # Properly URL-encode the query
        encoded_query = quote_plus(query)
        cmd = [
            "curl", "-s", "--max-time", "15",
            "-H", f"Authorization: Bearer {api_key}",
            f"https://api.exa.ai/search?q={encoded_query}&numResults={num_results}"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        if result.returncode != 0:
            return SearchResponse(query=query, results=[], total_results=0, search_engine="exa",
                               error=f"Curl failed with code {result.returncode}")

        data = json.loads(result.stdout)
        results = []
        for item in data.get("results", []):
            results.append(SearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                snippet=item.get("snippet", ""),
                source=item.get("source", "web")
            ))
        return SearchResponse(query=query, results=results, total_results=len(results), search_engine="exa")
    except Exception as e:
        return SearchResponse(query=query, results=[], total_results=0, search_engine="exa", error=str(e))


def search(query: str, num_results: int = 5) -> SearchResponse:
    """
    Perform web search using available search engines.

    Tries Exa API first (if available), then falls back to DuckDuckGo HTML.

    Args:
        query: Search query string
        num_results: Maximum number of results to return

    Returns:
        SearchResponse with results or error
    """
    # Try Exa first (higher quality results)
    exa_response = _search_exa(query, num_results)
    if exa_response.has_results:
        return exa_response

    # Fall back to DuckDuckGo
    ddg_response = _search_ddg(query, num_results)
    if ddg_response.has_results:
        return ddg_response

    # If both failed, return exa error (more informative)
    return exa_response if exa_response.error else ddg_response


def search_with_fallback(query: str, num_results: int = 5, fallback_content: str = None) -> tuple:
    """
    Perform search with fallback to template content.

    Args:
        query: Search query
        num_results: Max results
        fallback_content: Content to use if search fails

    Returns:
        (search_response, used_fallback) tuple
    """
    response = search(query, num_results)
    if response.has_results:
        return response, False

    # Search failed, return fallback indicator
    return response, True


if __name__ == "__main__":
    # Test search
    import sys
    query = sys.argv[1] if len(sys.argv) > 1 else "Python best practices"
    print(f"Searching for: {query}")
    response = search(query)
    print(f"Search engine: {response.search_engine}")
    print(f"Error: {response.error}")
    print(f"Results: {len(response.results)}")
    for r in response.results:
        print(f"  - {r.title}: {r.url}")
