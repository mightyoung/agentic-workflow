---
name: gstack/qa
version: 1.0.0
description: |
  QA 工作流负责功能测试和质量保证，确保代码符合质量标准。
tags: [qa, quality, testing]
requires:
  tools: [Read, Write, Bash]
---

# gstack /qa Command

## Overview

QA 工作流负责功能测试和质量保证，确保代码符合质量标准。

## Contract

### Input

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `scope` | `TARGET_FILES` | Yes | 要测试的文件范围 |
| `test_type` | `string` | No | 测试类型: `unit`, `integration`, `e2e` (default: `all`) |
| `coverage_threshold` | `number` | No | 覆盖率阈值 (default: 80) |

### Output

| Field | Type | Description |
|-------|------|-------------|
| `status` | `string` | `passed`, `failed`, `skipped` |
| `tests_run` | `number` | 运行的测试数量 |
| `tests_failed` | `number` | 失败的测试数量 |
| `coverage` | `number` | 代码覆盖率 |
| `report_path` | `string` | 测试报告路径 |
| `issues` | `Issue[]` | 发现的问题列表 |

### Issue Structure

```typescript
interface Issue {
  severity: "fatal" | "serious" | "suggestion";
  type: "test_failure" | "coverage_gap" | "flaky_test" | "missing_test";
  location: string;
  message: string;
  suggestion?: string;
}
```

## Process

### Step 1: 环境准备

```bash
# 1. 确定测试范围
TARGET_FILES=$(确定要测试的文件)

# 2. 检查测试框架
TEST_FRAMEWORK=$(检测项目测试框架: jest, pytest, go test, etc.)

# 3. 初始化测试报告
QA_REPORT="qa_report.md"
```

### Step 2: 执行测试

```bash
# 根据测试框架执行
case $TEST_FRAMEWORK in
  jest)
    npm test -- --coverage
    ;;
  pytest)
    pytest --cov --cov-report=html
    ;;
  go)
    go test -coverprofile=coverage.out ./...
    ;;
  *)
    echo "Unsupported test framework: $TEST_FRAMEWORK"
    ;;
esac
```

### Step 3: 覆盖率检查

```bash
# 检查覆盖率是否达到阈值
COVERAGE=$(get_coverage)
if [ "$COVERAGE" -lt "$coverage_threshold" ]; then
  echo "Coverage $COVERAGE% is below threshold $coverage_threshold%"
fi
```

### Step 4: 问题汇总

```bash
# 汇总测试失败和覆盖率问题
FAILED_TESTS=$(get_failed_tests)
COVERAGE_GAPS=$(get_coverage_gaps)
```

## Integration with REVIEWING

REVIEWING 阶段会尝试委托 QA 工作流：

```markdown
### QA Delegation (Optional)

尝试委托 gstack /qa 进行功能QA测试：

try:
    skill("gstack", "/qa", scope=TARGET_FILES)
except SkillNotFound:
    # Fallback - 继续使用内置review
    pass
```

## Exit Criteria

| Status | Condition |
|--------|-----------|
| `passed` | 所有测试通过且覆盖率达标 |
| `failed` | 有测试失败或覆盖率不达标 |
| `skipped` | 没有可执行的测试 |

## Fallback

如果 gstack skill 不可用，继续使用内置 reviewer 子智能体进行代码审查。
