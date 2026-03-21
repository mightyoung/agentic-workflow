---
name: Browser Daemon
description: Browser Daemon 接口合约 - E2E 测试和文档预览能力
version: 1.0.0
created: 2026-03-21
---

# Browser Daemon 遥测模块

## 价值和意义

Browser Daemon 是 agentic-workflow 的可视化能力基础设施，用于：

1. **E2E 测试支持** - 在 REVIEWING 阶段进行视觉回归测试
2. **文档预览** - 在 COMPLETE 阶段预览 Markdown 文档渲染效果
3. **无头浏览器控制** - 通过 CDP 协议控制浏览器执行自动化任务

## 连接方式

### HTTP API

Browser Daemon 运行在 localhost，提供 REST API：

```
http://localhost:9222
```

### 健康检查

```bash
GET /health
Response: { "status": "ok", "browser": "chromium" }
```

## 能力接口

### 截图 (Screenshot)

```bash
POST /screenshot
Body: {
  "url": "string",           # 目标 URL (必填)
  "fullPage": boolean,       # 是否截取整页 (default: false)
  "viewport": {              # 视口尺寸
    "width": number,
    "height": number
  },
  "selector": string         # CSS 选择器，只截取匹配元素
}
Response: {
  "success": boolean,
  "image": "base64 string",  # PNG 图片 base64 编码
  "error"?: string
}
```

### 点击 (Click)

```bash
POST /click
Body: {
  "selector": "string",      # CSS 选择器 (必填)
  "button": "left" | "right" | "middle",  # 鼠标按钮 (default: "left")
  "count": number           # 点击次数 (default: 1)
}
Response: {
  "success": boolean,
  "error"?: string
}
```

### 填表 (Fill)

```bash
POST /fill
Body: {
  "selector": "string",      # 输入框 CSS 选择器 (必填)
  "value": "string",        # 要填入的值 (必填)
  "pressEnter": boolean     # 填入后是否按回车 (default: false)
}
Response: {
  "success": boolean,
  "error"?: string
}
```

### 滚动 (Scroll)

```bash
POST /scroll
Body: {
  "direction": "up" | "down" | "left" | "right",
  "amount": number,          # 滚动像素值 (default: 300)
  "selector": string         # 可选：滚动到指定元素可见
}
Response: {
  "success": boolean,
  "error"?: string
}
```

### Accessibility Tree

```bash
POST /a11y
Body: {
  "url": "string",           # 目标 URL (必填)
  "selector": string         # 可选：只获取特定元素的 a11y 树
}
Response: {
  "success": boolean,
  "tree": {                 # Accessibility tree 结构
    "role": string,
    "name": string,
    "children": [...]        # 子节点递归
  },
  "error"?: string
}
```

### 执行 JavaScript

```bash
POST /eval
Body: {
  "script": "string",        # 要执行的 JavaScript 代码
  "args": [...]              # 传递给脚本的参数
}
Response: {
  "success": boolean,
  "result": any,            # 脚本返回值
  "error"?: string
}
```

## 错误处理

### Daemon 不可用时的 Fallback

```python
def browser_operation(operation, *args, **kwargs):
    """
    执行浏览器操作，带优雅降级
    """
    try:
        # 尝试连接 Browser Daemon
        response = requests.post(
            f"http://localhost:9222{operation}",
            json=kwargs,
            timeout=5
        )
        response.raise_for_status()
        return response.json()
    except (requests.ConnectionError, requests.Timeout):
        # Fallback: 返回不可用状态，不阻断流程
        return {
            "success": False,
            "error": "Browser Daemon unavailable",
            "fallback": True
        }
```

### 错误码

| Code | 含义 | 处理方式 |
|------|------|----------|
| `DAEMON_UNAVAILABLE` | Daemon 未启动 | 使用手动检查清单 |
| `TIMEOUT` | 操作超时 | 重试或跳过 |
| `INVALID_SELECTOR` | CSS 选择器无效 | 记录错误，继续 |
| `NAVIGATION_ERROR` | 页面导航失败 | 截图当前状态，记录 |

## E2E 测试集成

### 视觉回归测试

```bash
# 1. 截取当前页面
SCREENSHOT=$(POST /screenshot {"url": TARGET_URL, "fullPage": true})

# 2. 与基准截图对比
if [ "$BASELINE_EXISTS" = true ]; then
    DIFF=$(compare_images "$SCREENSHOT" "$BASELINE")
    if [ "$DIFF" -gt "$THRESHOLD" ]; then
        echo "Visual regression detected: $DIFF% difference"
    fi
fi
```

### 交互测试

```bash
# 测试用户登录流程
POST /fill {"selector": "#username", "value": "testuser"}
POST /fill {"selector": "#password", "value": "password123"}
POST /click {"selector": "button[type=submit]"}
POST /screenshot {"selector": ".dashboard"}

# 检查是否成功导航
A11Y=$(POST /a11y)
if echo "$A11Y" | grep -q "Dashboard"; then
    echo "Login flow passed"
fi
```

## 文档预览集成

### Markdown 预览

```bash
# 在 COMPLETE 阶段预览文档
PREVIEW_URL="file://$(pwd)/docs/output.md"

# 截取文档预览
DOC_SCREENSHOT=$(POST /screenshot {
    "url": PREVIEW_URL,
    "viewport": {"width": 1200, "height": 800}
})

# 验证渲染效果
if [ "$DOC_SCREENSHOT.success" = true ]; then
    echo "Document preview generated successfully"
else
    echo "Preview generation failed: $DOC_SCREENSHOT.error"
fi
```

## 配置选项

### 环境变量

```bash
# Browser Daemon 地址 (默认: localhost:9222)
export BROWSER_DAEMON_URL=http://localhost:9222

# 默认超时 (默认: 30s)
export BROWSER_DAEMON_TIMEOUT=30

# 截图质量 (默认: 80)
export BROWSER_SCREENSHOT_QUALITY=80
```

### 启动 Browser Daemon

```bash
# 使用 Puppeteer 启动
node -e "
const puppeteer = require('puppeteer');
(async () => {
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--remote-debugging-port=9222']
  });
  console.log('Browser Daemon ready on port 9222');
})();
"
```

## 实现状态

- [x] 接口合约定义
- [x] 连接方式 (HTTP)
- [x] 能力定义 (截图、点击、填表、滚动、a11y)
- [x] 错误处理和 fallback
- [ ] 集成到 REVIEWING 阶段
- [ ] 集成到 COMPLETE 阶段
- [ ] 视觉回归测试模板
