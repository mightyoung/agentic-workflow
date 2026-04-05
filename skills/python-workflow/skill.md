---
name: python-workflow
version: 1.0.0
status: implemented
description: |
  Python 项目工作流增强 - 覆盖 Python 特有的开发模式、测试工具和常见陷阱
  自动叠加到 agentic-workflow 上，提供语言专属指导
tags: [language, python, workflow]
requires:
  tools: [Bash, Read, Write, Grep]
---

# PYTHON WORKFLOW

## Overview

当检测到 Python 项目时（存在 `pyproject.toml` / `setup.py` / `*.py`），此 skill 的规则叠加在 agentic-workflow 之上。

## Python 项目检测

```bash
# 自动检测项目类型
test -f pyproject.toml && echo "Python/pyproject"
test -f setup.py && echo "Python/setuptools"
test -f requirements.txt && echo "Python/requirements"
```

## Iron Laws（Python 专属）

```
NO TYPE HINTS = REJECT — 新函数必须有类型注解（Python 3.9+ 用 from __future__ import annotations）
NO BARE EXCEPT — 禁止裸 except:，必须捕获具体异常类型
NO MUTABLE DEFAULTS — 禁止 def f(x=[]) 模式，用 None 替代
NO SILENT FAILURES — 禁止空 except pass，必须记录或重抛
```

## EXECUTING 阶段 — Python 规范

### 代码质量强制检查

```bash
# 在每次提交前运行
python3 -m ruff check . --fix          # 自动修复 lint 问题
python3 -m mypy . --ignore-missing-imports  # 类型检查
python3 -m pytest tests/ -q            # 测试
```

### Python 3.9 兼容性（本项目要求）

```python
# 必须在每个模块顶部添加（在 Python 3.10+ 类型注解语法前）
from __future__ import annotations

# 正确：
def process(items: list[str] | None = None) -> dict[str, Any]:
    ...

# 错误（3.9 不支持，除非有上面的 import）：
def process(items: list[str] | None = None) -> dict[str, Any]:  # ❌ 无 __future__
```

### 测试框架

```bash
# pytest 标准命令
python3 -m pytest tests/ -v --tb=long     # 详细失败信息
python3 -m pytest tests/ -q --tb=short    # 快速模式
python3 -m pytest tests/ -k "test_name"  # 单测试
python3 -m pytest --cov=scripts --cov-report=term-missing  # 覆盖率
```

## DEBUGGING 阶段 — Python 专属诊断

```bash
# Step 1 强制诊断（Python 项目）
python3 -m pytest --tb=long -q 2>&1 | tail -60    # 完整错误输出
python3 -m ruff check . 2>&1 | head -30            # Lint 错误
python3 -c "import sys; print(sys.version)"        # Python 版本确认
pip list | grep -E "pytest|ruff|mypy" | head -10   # 工具版本
```

### 常见 Python 陷阱

| 问题 | 症状 | 修复 |
|------|------|------|
| `list | None` 类型语法错误 | `TypeError: unsupported operand` | 加 `from __future__ import annotations` |
| 循环导入 | `ImportError: cannot import name` | 检查 `__init__.py`，使用延迟导入 |
| 可变默认参数 | 多次调用结果累积 | 改为 `= None`，函数内 `if x is None: x = []` |
| Mock 未重置 | 测试间状态泄漏 | 使用 `@pytest.fixture(autouse=True)` 清理 |
| `assert` 被优化掉 | `-O` 模式 assert 无效 | 用 `if not condition: raise ValueError` |

## REVIEWING 阶段 — Python 专属清单

除标准 REVIEWING 清单外，额外检查：

- [ ] 所有公共函数有类型注解
- [ ] 无裸 `except:` 或 `except Exception: pass`
- [ ] 无可变默认参数
- [ ] 测试覆盖率 >= 80%（`pytest --cov`）
- [ ] `from __future__ import annotations` 存在于需要的模块

## 包管理最佳实践

```bash
# 推荐：pyproject.toml + pip install -e .
pip install -e ".[dev]"

# 检查依赖是否正常安装
python3 -c "import scripts; print('OK')"
```
