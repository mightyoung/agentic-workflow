---
name: boil-the-lake
description: gstack 核心原则 - 完整实现优于捷径
tags: [principles, gstack, completeness, best-practices]
---

# Boil the Lake

> 当 AI 辅助编程使完整实现的边际成本接近零时，应该始终选择完整实现而非捷径。

## 核心原则

**Boil the Lake** 是 gstack 的核心原则：AI 辅助编程彻底改变了「完整实现」与「走捷径」之间的成本对比。

- 传统观点：走捷径是明智的，因为完整实现成本太高
- gstack 观点：AI 让完整实现的边际成本接近零，所以永远选完整实现

### 关键洞察

| 传统思维 | AI 时代思维 |
|---------|-------------|
| 完整测试覆盖 = 高成本 | AI 生成测试 = 边际成本接近零 |
| 走捷径 = 节省时间 | 走捷径 = 技术债务积累 |
| 80% 覆盖就够了 | 100% 覆盖是标准 |

## Lake vs Ocean

### Lake（可完成）

Lake 是指**可完成的工作范围**——可以实现 100% 测试覆盖的任务。

特征：
- 有明确边界的问题
- 可穷举的输入/输出场景
- 现有系统内的功能模块
- Bug 修复 + 完整回归测试

### Ocean（不可完成）

Ocean 是指**无法完成的工作范围**——不可能实现 100% 覆盖的重写或巨大系统。

特征：
- 重写整个系统
- 跨多个不相关系统
- 依赖外部未知系统
- 开放式研究问题

### 判断标准

```
任务 ∈ Lake ? → 完整实现（100% 覆盖）
任务 ∈ Ocean ? → 寻找最小可行路径
```

## 努力估算表

以下表格展示 Human vs CC+gstack 的压缩比：

| 任务类型 | Human 估算 | CC+gstack 估算 | 压缩比 | 说明 |
|---------|-----------|----------------|-------|------|
| 样板/脚手架 | 2 天 | 15 分钟 | ~100x | 项目初始化、配置、模板 |
| 测试编写 | 1 天 | 15 分钟 | ~50x | 单元测试、集成测试、E2E |
| 功能实现 | 1 周 | 30 分钟 | ~30x | 完整功能 + 测试 + 文档 |
| Bug 修复 + 回归测试 | 4 小时 | 15 分钟 | ~20x | 修复 + 验证测试 |
| 代码重构 | 3 天 | 1 小时 | ~70x | 重构 + 测试覆盖 |
| API 设计 | 2 天 | 30 分钟 | ~60x | 接口设计 + Mock + 文档 |
| 数据库迁移 | 1 周 | 1 小时 | ~40x | 迁移脚本 + 回滚测试 |

### 核心结论

> 当 AI 将完成时间从「天」压缩到「分钟」时，选择完整实现的成本几乎为零。

## 反模式（不要做的示例）

### 1. 80% 覆盖陷阱

```typescript
// 反模式：只写通过的主要用例测试
describe('UserService', () => {
  it('should create user', () => { /* ... */ });
  it('should find user by id', () => { /* ... */ });
  // 遗漏：边界情况、错误处理、并发场景
});

// 正模式：100% 覆盖
describe('UserService', () => {
  it('should create user', () => { /* ... */ });
  it('should create user with empty name throws', () => { /* ... */ });
  it('should find user by id', () => { /* ... */ });
  it('should find user by id not found throws', () => { /* ... */ });
  it('should update user', () => { /* ... */ });
  it('should delete user', () => { /* ... */ });
  it('should handle concurrent updates', () => { /* ... */ });
});
```

### 2. 跳过边界情况

```typescript
// 反模式：只处理快乐路径
function parseConfig(json: string): Config {
  const parsed = JSON.parse(json);
  return {
    host: parsed.host,
    port: parsed.port,
  };
}

// 正模式：处理所有边界情况
function parseConfig(json: string): Result<Config, ConfigError> {
  if (!json || json.trim() === '') {
    return { ok: false, error: ConfigError.EmptyInput };
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(json);
  } catch {
    return { ok: false, error: ConfigError.InvalidJSON };
  }

  if (!isConfig(parsed)) {
    return { ok: false, error: ConfigError.InvalidSchema };
  }

  return { ok: true, value: { host: parsed.host, port: parsed.port } };
}
```

### 3. Mock 过度使用

```typescript
// 反模式：Mock 一切，导致测试无用
it('should call userService', async () => {
  const mockUserService = jest.fn().mockResolvedValue({ id: '1' });
  const result = await sut.doSomething(mockUserService);
  expect(result).toBeDefined();
});

// 正模式：使用真实实现或真实 Mock
it('should create user and persist to database', async () => {
  const db = new TestDatabase(); // 真实测试数据库
  const userService = new UserService(db);
  const result = await userService.create({ name: 'Test' });
  expect(result.id).toBeDefined();
  expect(await db.users.findById(result.id)).toEqual(result);
});
```

### 4. 跳过文档

```typescript
// 反模式：无文档或只有 TODO
function calculateShipping(order: Order): number {
  // TODO: implement
  return 0;
}

// 正模式：完整 JSDoc + 类型定义
/**
 * 计算订单配送费用
 *
 * @param order - 已验证的订单对象，包含 items 和 address
 * @returns 配送费用（单位：分）
 * @throws {ShippingError} 当无法配送到指定地址时
 *
 * @example
 * const order = { items: [{ weight: 100 }], address: { zip: '100000' } };
 * const fee = calculateShipping(order); // => 1500
 */
function calculateShipping(order: Order): Result<number, ShippingError> {
  // ... 完整实现
}
```

## 应用场景说明

### 何时应用 Boil the Lake

| 场景 | 应用建议 |
|-----|---------|
| 新功能开发 | 完整 TDD，100% 测试覆盖 |
| Bug 修复 | 修复 + 完整回归测试套件 |
| 重构 | 先写测试，再重构，保持覆盖 |
| API 变更 | 完整 Mock + 集成测试 |
| 数据库变更 | 迁移脚本 + 回滚测试 |

### 何时不适用

| 场景 | 原因 |
|-----|------|
| 概念验证 / 原型 | 快速验证想法，不需要完整实现 |
| 一次性脚本 | 不需要长期维护 |
| 外部系统集成 | 无法控制，聚焦在适配层 |
| 研究/实验 | 目标是学习，不是生产代码 |

### 判断流程

```
1. 这是 Lake 任务吗？（可完成、100% 可达）
   └── 否 → 寻找最小可行路径
   └── 是 → 继续

2. 完整实现的边际成本是否接近零？（AI 辅助）
   └── 是 → 完整实现
   └── 否 → 评估 ROI

3. 技术债务长期成本 > 短期收益？
   └── 是 → 完整实现
   └── 否 → 权衡取舍
```

## 总结

**Boil the Lake 原则：**

1. **永远选择完整实现**（当成本接近零时）
2. **Lake 可完成，Ocean 不可完成**——区分任务范围
3. **AI 让 100% 覆盖的边际成本接近零**——不再有借口
4. **技术债务的长期成本 > 完整实现的短期投入**

> 烧掉湖泊，让每一滴水都得到测试覆盖。
