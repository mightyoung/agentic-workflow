---
name: rust-workflow
version: 1.0.0
status: implemented
description: |
  Rust 项目工作流增强 - 覆盖 Rust 特有的所有权、生命周期、错误处理模式
  自动叠加到 agentic-workflow 上，提供语言专属指导
tags: [language, rust, workflow]
requires:
  tools: [Bash, Read, Write, Grep]
---

# RUST WORKFLOW

## Overview

当检测到 Rust 项目时（存在 `Cargo.toml`），此 skill 的规则叠加。

## 项目检测

```bash
test -f Cargo.toml && echo "Rust project"
```

## Iron Laws（Rust 专属）

```
NO unwrap() IN LIBRARY CODE — 只有 main/tests/examples 可用 unwrap()，库代码用 ? 传播
NO UNSAFE WITHOUT COMMENT — unsafe 块必须有安全性注释说明为什么这是安全的
CLIPPY MUST PASS — cargo clippy 必须无 warnings（-D warnings 模式）
NO CLONE TO FIX BORROW — 不能仅为了绕过 borrow checker 而 clone，先理解所有权
```

## EXECUTING 阶段 — Rust 规范

### 构建与质量检查

```bash
cargo build                              # 编译
cargo test                               # 测试
cargo clippy -- -D warnings              # Lint（视 warning 为 error）
cargo fmt --check                        # 格式检查
```

### 错误处理最佳实践

```rust
// ✅ 正确 — 用 ? 传播错误
fn read_config(path: &str) -> Result<Config, Box<dyn std::error::Error>> {
    let content = std::fs::read_to_string(path)?;
    let config: Config = serde_json::from_str(&content)?;
    Ok(config)
}

// ❌ 错误 — unwrap 会 panic
fn read_config(path: &str) -> Config {
    let content = std::fs::read_to_string(path).unwrap();
    serde_json::from_str(&content).unwrap()
}
```

### 所有权常见模式

```rust
// 需要多次使用时 — 借用而非移动
fn print_name(name: &str) { println!("{name}"); }  // ✅
fn print_name(name: String) { println!("{name}"); }  // ❌（消耗所有权）

// 可选修改时 — &mut 借用
fn append_suffix(s: &mut String) { s.push_str("_suffix"); }  // ✅
```

## DEBUGGING 阶段 — Rust 专属诊断

```bash
# Step 1 强制诊断
cargo test -- --nocapture 2>&1 | tail -60   # 测试失败（含 println 输出）
cargo build 2>&1 | head -40                 # 编译错误（borrow/lifetime）
cargo clippy 2>&1 | head -30                # Lint 警告
rustc --version && cargo --version          # 版本信息
```

### 常见 Rust 陷阱

| 问题 | 症状 | 修复 |
|------|------|------|
| 生命周期不够长 | `borrowed value does not live long enough` | 检查数据所有者，考虑 `Arc<T>` |
| 多重可变借用 | `cannot borrow as mutable more than once` | 分拆借用作用域，或用 `RefCell` |
| 移动后使用 | `value used here after move` | 在移动前 clone 或改为借用 |
| `Send` 未实现 | `cannot send ... between threads` | 用 `Arc<Mutex<T>>` 包装 |
| 异步 trait 未支持 | `the trait cannot be made into an object` | 使用 `async-trait` crate |

## REVIEWING 阶段 — Rust 专属清单

- [ ] 无 `unwrap()` / `expect()` 在库代码中（`grep -rn "\.unwrap()" src/`）
- [ ] 所有 `unsafe` 块有安全注释
- [ ] `cargo clippy -- -D warnings` 通过
- [ ] `cargo fmt --check` 通过
- [ ] 公共 API 有文档注释（`///`）
