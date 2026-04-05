---
name: go-workflow
version: 1.0.0
status: implemented
description: |
  Go 项目工作流增强 - 覆盖 Go 特有的惯用模式、错误处理和并发安全
  自动叠加到 agentic-workflow 上，提供语言专属指导
tags: [language, go, golang, workflow]
requires:
  tools: [Bash, Read, Write, Grep]
---

# GO WORKFLOW

## Overview

当检测到 Go 项目时（存在 `go.mod`），此 skill 的规则叠加。

## 项目检测

```bash
test -f go.mod && echo "Go module project"
```

## Iron Laws（Go 专属）

```
NO IGNORED ERRORS — err 必须处理，禁止 _, err := ... 后不检查 err
NO GOROUTINE LEAK — 启动的 goroutine 必须有退出机制（context / done channel）
NO PANIC IN LIBRARY — 库代码禁止 panic，只有 main/入口可以 panic
ERRORS ARE VALUES — 用 errors.Is/As 比较错误，不用字符串比较
```

## EXECUTING 阶段 — Go 规范

### 构建与质量检查

```bash
go build ./...                    # 编译检查
go vet ./...                      # 静态分析
go test ./... -v -race            # 测试（含 race detector）
golangci-lint run ./... 2>/dev/null || go vet ./...  # Lint
```

### 惯用错误处理

```go
// ✅ 正确
result, err := doSomething()
if err != nil {
    return fmt.Errorf("doSomething: %w", err)
}

// ❌ 错误 — 忽略错误
result, _ := doSomething()
```

### Context 使用

```go
// ✅ 正确 — 传递 context
func processRequest(ctx context.Context, req Request) (Response, error) {
    if err := ctx.Err(); err != nil {
        return Response{}, err
    }
    // ...
}

// ❌ 错误 — 无 context，无法取消
func processRequest(req Request) (Response, error) { ... }
```

## DEBUGGING 阶段 — Go 专属诊断

```bash
# Step 1 强制诊断
go test ./... -v -run TestFailing 2>&1 | tail -60  # 特定失败测试
go test -race ./... 2>&1 | grep -E "DATA RACE|FAIL"  # Race condition
go build ./... 2>&1                                  # 编译错误
go mod tidy && go mod verify                         # 依赖问题
```

### 常见 Go 陷阱

| 问题 | 症状 | 修复 |
|------|------|------|
| goroutine 泄漏 | 内存持续增长 | 用 context 或 done channel 控制退出 |
| slice 共享底层数组 | 意外修改 | 用 `copy()` 或 `append([]T{}, s...)` |
| 接口 nil 陷阱 | `(*T)(nil) != nil` | 返回 `(T, error)` 而非 `(interface{}, error)` |
| map 并发读写 | race condition panic | 使用 `sync.Map` 或 mutex |
| defer 在循环中 | 资源到函数退出才释放 | 提取为函数或手动关闭 |

## REVIEWING 阶段 — Go 专属清单

- [ ] 所有 `err` 都被检查（`grep -n "_, err" | grep -v "//"`）
- [ ] goroutine 有退出机制
- [ ] 无 `panic` 在非 main 包中
- [ ] 错误用 `%w` 包装（而非 `%v`）
- [ ] `go test -race` 通过
