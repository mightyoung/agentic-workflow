---
name: baidu-search
version: 1.0.0
status: implemented
description: |
  百度AI搜索 - 基于千帆平台的智能搜索服务
  提供AI增强的搜索结果，包含引用来源标注
tags: [search, baidu, qianfan, web-search]
requires:
  tools: [Bash]
env:
  - BAIDU_QIANFAN_API_KEY
---

# BAIDU-SEARCH

## Overview

百度AI搜索是基于百度千帆平台的智能搜索服务，提供AI增强的搜索结果，支持：
- AI 增强的答案生成
- 引用来源标注（corner markers）
- 深度搜索模式
- 后续问题建议

## API Configuration

**Endpoint**: `https://qianfan.baidubce.com/v2/ai_search/chat/completions`

**Authentication**: Bearer Token

```python
import os
import requests

api_key = os.environ.get("BAIDU_QIANFAN_API_KEY")

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}"
}
```

## Usage

### Basic Search

```python
def baidu_search(query: str) -> dict:
    """
    Perform Baidu AI Search.

    Args:
        query: Search query string

    Returns:
        dict with keys: result, references, is_safe
    """
    import os
    import requests

    # 加载 .env 文件
    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.environ.get("BAIDU_QIANFAN_API_KEY")
    if not api_key:
        raise ValueError("BAIDU_QIANFAN_API_KEY not set")

    url = "https://qianfan.baidubce.com/v2/ai_search/chat/completions"

    payload = {
        "messages": [{"role": "user", "content": query}],
        "model": "ernie-4.5-turbo-32k",
        "search_source": "baidu_search_v2",
        "enable_corner_markers": True,
        "stream": False
    }

    response = requests.post(url, headers=headers, json=payload, timeout=120)
    response.raise_for_status()
    return response.json()
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | string | required | Search query |
| `model` | string | ernie-4.5-turbo-32k | Model to use |
| `search_source` | string | baidu_search_v2 | Search engine version |
| `enable_deep_search` | bool | False | Enable deep search mode |
| `enable_corner_markers` | bool | True | Enable citation markers |
| `enable_followup_queries` | bool | False | Enable follow-up suggestions |
| `search_recency_filter` | string | None | Time filter: week/month/semiyear/year |
| `temperature` | float | 0.11 | Sampling temperature |
| `top_p` | float | 0.55 | Sampling top_p |

### Response Format

```json
{
  "choices": [{
    "finish_reason": "stop",
    "message": {
      "content": "AI生成的搜索答案...",
      "role": "assistant"
    }
  }],
  "is_safe": true,
  "references": [
    {
      "id": 1,
      "title": "来源标题",
      "url": "https://example.com",
      "content": "来源内容摘要",
      "website": "网站名称",
      "date": "2026-03-22"
    }
  ]
}
```

## Examples

### Example 1: Basic Search

```python
result = baidu_search("今天北京天气怎么样")
print(result["choices"][0]["message"]["content"])
```

### Example 2: Deep Search

```python
def baidu_deep_search(query: str) -> dict:
    payload = {
        "messages": [{"role": "user", "content": query}],
        "model": "ernie-4.5-turbo-32k",
        "enable_deep_search": True,
        "enable_corner_markers": True
    }
    # ... make request
```

### Example 3: With Recency Filter

```python
def baidu_search_recent(query: str, days: int = 7) -> dict:
    filter_map = {7: "week", 30: "month", 180: "semiyear", 365: "year"}
    recency = filter_map.get(days, "month")

    payload = {
        "messages": [{"role": "user", "content": query}],
        "model": "ernie-4.5-turbo-32k",
        "search_recency_filter": recency
    }
    # ... make request
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `BAIDU_QIANFAN_API_KEY` | Yes | Baidu Qianfan API Key |

## Error Handling

```python
try:
    result = baidu_search("search query")
except requests.exceptions.Timeout:
    print("Request timed out")
except requests.exceptions.HTTPError as e:
    print(f"HTTP error: {e.response.status_code}")
except ValueError as e:
    print(f"Configuration error: {e}")
```

## Notes

- API Key 格式: `bce-v3/ALTAK-xxx/xxx`
- 默认超时: 120秒
- 深度搜索模式会产生更多token消耗
- 引用来源标注有助于追溯信息准确性
