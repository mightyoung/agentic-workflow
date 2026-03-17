# 内置TDD流程（降级版）

> 当ecc-workflow不可用时的简化TDD实现

## 适用场景

- ecc-workflow未安装
- 用户选择不使用ECC
- 快速开发场景

## TDD核心流程

```
红 → 绿 → 重构
```

### 1. 红 (Red) - 写失败测试

```python
# 创建测试文件
def test_add():
    assert add(1, 2) == 3  # 尚未实现，会失败
```

**要求**：
- 测试必须在实现之前编写
- 测试必须能运行（import正确）
- 测试必须失败（assert条件不满足）

### 2. 绿 (Green) - 最小实现

```python
# 只写让测试通过的最小代码
def add(a, b):
    return a + b
```

**原则**：
- 不追求完美，只求通过测试
- 后续可以重构

### 3. 重构 (Refactor)

```python
# 优化代码，保持功能不变
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b
```

**原则**：
- 重构后测试必须仍然通过
- 每次重构后运行测试

## TDD检查清单

- [ ] 测试文件存在？
- [ ] 先运行失败？
- [ ] 使用assert而非print？
- [ ] 覆盖边界条件？

## 测试命名规范

| 语言 | 测试文件 | 测试函数 |
|------|---------|---------|
| Python | test_*.py | test_* |
| JavaScript | *.test.js | test(*) |
| Go | *_test.go | Test* |
| Rust | *.rs | #[test] |

## 断言优先

```python
# 正确
assert result == expected, f"Expected {expected}, got {result}"

# 错误
print(result)  # 不要用print调试
```

## 边界条件

测试必须覆盖：
- 空值/null
- 零值
- 负数（如果适用）
- 极大值
- 特殊字符
