---
name: typescript-workflow
version: 1.0.0
status: implemented
description: |
  TypeScript/Node.js 项目工作流增强 - 覆盖 TS 特有的类型安全、构建工具和测试模式
  自动叠加到 agentic-workflow 上，提供语言专属指导
tags: [language, typescript, javascript, workflow]
requires:
  tools: [Bash, Read, Write, Grep]
---

# TYPESCRIPT WORKFLOW

## Overview

当检测到 TypeScript 项目时（存在 `tsconfig.json` / `package.json` 含 typescript），此 skill 的规则叠加。

## 项目检测

```bash
test -f tsconfig.json && echo "TypeScript project"
test -f package.json && cat package.json | grep -q '"typescript"' && echo "TypeScript dep found"
```

## Iron Laws（TypeScript 专属）

```
NO any — 禁止使用 any 类型，用 unknown + 类型守卫替代
NO type assertions on untrusted data — 外部数据用 zod/yup 验证，不用 as Type 强转
NO implicit returns — 函数必须有明确的返回类型注解
STRICT MODE = ON — tsconfig 必须启用 strict: true
```

## EXECUTING 阶段 — TypeScript 规范

### 构建与质量检查

```bash
# 类型检查（必须无错误）
npx tsc --noEmit

# Lint
npx eslint . --ext .ts,.tsx

# 测试
npm test
# 或
npx jest --coverage
npx vitest run --coverage
```

### 类型安全最佳实践

```typescript
// ✅ 正确 — 用 unknown 处理外部数据
async function fetchUser(id: string): Promise<User> {
  const data: unknown = await fetch(`/api/users/${id}`).then(r => r.json());
  return UserSchema.parse(data); // zod validation
}

// ❌ 错误 — 信任外部数据
async function fetchUser(id: string): Promise<User> {
  return fetch(`/api/users/${id}`).then(r => r.json()) as User;
}
```

## DEBUGGING 阶段 — TypeScript 专属诊断

```bash
# Step 1 强制诊断
npx tsc --noEmit 2>&1 | head -40    # 类型错误
npm test -- --verbose 2>&1 | tail -50  # 测试失败
cat tsconfig.json | grep -E "strict|target|module"  # 配置检查
node --version && npx tsc --version  # 版本信息
```

### 常见 TypeScript 陷阱

| 问题 | 症状 | 修复 |
|------|------|------|
| `strict` 未开启 | 大量隐式 any | `tsconfig.json` 加 `"strict": true` |
| 枚举运行时消失 | `const enum` 跨包报错 | 改为 `enum` 或 string union |
| 循环依赖 | 初始化时值为 undefined | 检查 import 顺序，使用依赖注入 |
| 泛型推断失败 | 手动传类型参数 | 提供足够上下文让 TS 推断 |

## REVIEWING 阶段 — TypeScript 专属清单

- [ ] `tsconfig.json` 启用 `strict: true`
- [ ] 无 `any` 类型（grep 确认）
- [ ] 外部数据有 schema 验证（zod/yup）
- [ ] 测试覆盖率 >= 80%
- [ ] 无 `@ts-ignore` 或 `@ts-expect-error`（除非有注释说明原因）
