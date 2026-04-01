#!/usr/bin/env python3
"""
Search Adapter for RESEARCH phase - Real web search integration

Provides actual web search capabilities for the RESEARCH phase, with fallback
to template-based findings when search is unavailable.
"""

import subprocess
import json
from typing import List, Optional
from dataclasses import dataclass
from urllib.parse import quote_plus


@dataclass
class SearchResult:
    """Single search result with metadata"""
    title: str
    url: str
    snippet: str
    source: str
    reliability: str = "C"  # A/B/C/D reliability grade
    url_validated: bool = False
    response_time_ms: int = 0


@dataclass
class SearchResponse:
    """Complete search response"""
    query: str
    results: List[SearchResult]
    total_results: int
    search_engine: str
    error: Optional[str] = None
    metadata: Optional[dict] = None  # Additional search metadata

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    @property
    def has_results(self) -> bool:
        return len(self.results) > 0 and self.error is None

    def get_high_confidence_results(self, min_reliability: str = "B") -> List[SearchResult]:
        """Return results with reliability >= min_reliability"""
        reliability_order = {"A": 4, "B": 3, "C": 2, "D": 1}
        min_level = reliability_order.get(min_reliability, 0)
        return [r for r in self.results
                if reliability_order.get(r.reliability, 0) >= min_level]


# Source reliability classification
_RELIABILITY_PATTERNS = {
    "A": [
        r"github\.com/(?:tensorflow|pytorch|react|vue|angular|node|vercel|framer)/",
        r"docs\.(?:python|typescript|javascript|rust|golang)\.",
        r"developer\.(?:mozilla|apple|microsoft)\.",
        r"cloud\.google\.com/docs",
        r"aws\.amazon\.com/documentation",
    ],
    "B": [
        r"github\.com/(?!.*(?:tutorial|example|sample))",
        r"stackoverflow\.com/questions/\d+",
        r"medium\.com/@",
        r"dev\.to/",
        r"hackernoon\.com",
    ],
    "C": [
        r"github\.com/.*(?:tutorial|example|sample|demo)",
        r"stackoverflow\.com/(?!questions)",
        r"reddit\.com/r/",
        r"zhihu\.com/",
    ],
    "D": [
        r".*",  # Default fallback
    ]
}


def classify_source_reliability(url: str) -> str:
    """
    Classify search result source reliability.

    Returns:
        A: Official docs, major project repos
        B: Quality blogs, Stack Overflow answers
        C: Tutorials, examples, discussions
        D: Low-quality or unverified sources
    """
    import re
    for grade, patterns in _RELIABILITY_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return grade
    return "D"


def _get_reliability_dist(results: List[SearchResult]) -> dict:
    """Get distribution of reliability grades in results"""
    dist = {"A": 0, "B": 0, "C": 0, "D": 0}
    for r in results:
        dist[r.reliability] = dist.get(r.reliability, 0) + 1
    return dist


def validate_url(url: str, timeout: float = 3.0) -> bool:
    """
    Validate that URL is reachable.

    Args:
        url: URL to validate
        timeout: Timeout in seconds

    Returns:
        True if URL returns 200-299 status code
    """
    import re
    # Only validate http/https URLs
    if not re.match(r'^https?://', url):
        return False

    try:
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
             "--max-time", str(timeout), url],
            capture_output=True, text=True, timeout=timeout + 1
        )
        status_code = result.stdout.strip()
        return status_code.startswith("2")
    except Exception:
        return False


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
                               error=f"Curl failed with code {result.returncode}",
                               metadata={"degraded_mode": True, "degraded_reason": "DuckDuckGo HTML - curl failed"})

        html = result.stdout

        # Validate HTML structure - check for expected markers
        if '<a class="result__a"' not in html:
            # Page structure may have changed - return degraded error
            return SearchResponse(
                query=query, results=[], total_results=0, search_engine="duckduckgo",
                error="DuckDuckGo HTML structure changed - parsing failed",
                metadata={
                    "degraded_mode": True,
                    "degraded_reason": "DuckDuckGo HTML structure changed - result__a class not found. HTML length: " + str(len(html))
                }
            )

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
                    reliability = classify_source_reliability(url)
                    results.append(SearchResult(
                        title=title, url=url, snippet=snippet,
                        source="web", reliability=reliability
                    ))
                    if len(results) >= num_results:
                        break

        # Validate we got results - if not, something changed in structure
        if len(results) == 0:
            return SearchResponse(
                query=query, results=[], total_results=0, search_engine="duckduckgo",
                error="DuckDuckGo HTML parsing found no results - structure may have changed",
                metadata={
                    "degraded_mode": True,
                    "degraded_reason": "DuckDuckGo HTML parsing produced 0 results despite HTML being present"
                }
            )

        return SearchResponse(
            query=query, results=results, total_results=len(results),
            search_engine="duckduckgo",
            metadata={
                "reliability_distribution": _get_reliability_dist(results),
                "degraded_mode": True,
                "degraded_reason": "DuckDuckGo HTML fallback - fragile, structure may change without notice"
            }
        )
    except subprocess.TimeoutExpired:
        return SearchResponse(query=query, results=[], total_results=0, search_engine="duckduckgo",
                           error="Search timeout",
                           metadata={"degraded_mode": True, "degraded_reason": "DuckDuckGo HTML fallback - timeout"})
    except Exception as e:
        return SearchResponse(query=query, results=[], total_results=0, search_engine="duckduckgo",
                           error=str(e),
                           metadata={"degraded_mode": True, "degraded_reason": f"DuckDuckGo HTML fallback - error: {e}"})


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
            url = item.get("url", "")
            results.append(SearchResult(
                title=item.get("title", ""),
                url=url,
                snippet=item.get("snippet", ""),
                source=item.get("source", "web"),
                reliability=classify_source_reliability(url)
            ))
        return SearchResponse(
            query=query, results=results, total_results=len(results),
            search_engine="exa",
            metadata={"reliability_distribution": _get_reliability_dist(results)}
        )
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


def search_with_fallback(query: str, num_results: int = 5, fallback_content: Optional[str] = None) -> tuple:
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
