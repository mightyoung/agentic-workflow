# ECC命令集成

> 当需要ECC命令时，动态委托ecc-workflow

## 动态委托机制

当需要特定ECC命令时，尝试委托ecc-workflow：

```python
# 尝试调用ECC
try:
    skill("ecc-workflow", "/tdd")
except SkillNotFound:
    # 降级到内置版本
    use_builtin_tdd()
```

## ECC命令映射

| 任务类型 | ECC命令 | 内置版本 |
|---------|---------|---------|
| TDD开发 | /tdd | 内置TDD流程 |
| 代码审查 | /code-review | 内置审查流程 |
| E2E测试 | /e2e | 内置E2E流程 |

## 降级流程

### 1. 检测阶段
```
用户请求TDD开发
    ↓
尝试调用 skill("ecc-workflow", "/tdd")
    ↓
┌─────────────────────────┐
│  ECC存在？              │
├─────────────────────────┤
│  是 → 执行ECC命令       │
│  否 → 进入降级流程      │
└─────────────────────────┘
```

### 2. 提示阶段
```
检测到ecc-workflow不存在

提示用户：
"检测到ecc-workflow未安装。
ECC提供增强的TDD、代码审查等功能。

选项：
[A] 安装ecc-workflow（推荐）
[B] 使用内置简化版

回复选择："
```

### 3. 执行阶段
```
用户选择A → 显示安装引导
用户选择B → 使用内置版本
```

---

## 内置TDD流程

当ECC不可用时，使用简化版TDD：

### 步骤
1. 写失败测试
2. 运行确保失败
3. 最小实现
4. 运行确保通过

### 检测点
- [ ] 测试文件存在？
- [ ] 先运行失败？
- [ ] 使用assert？
- [ ] 覆盖边界条件？

详见 `references/modules/executing.md`

---

## 内置代码审查

当ECC不可用时，使用简化版审查：

### 步骤
1. 整体架构检查
2. 核心逻辑检查
3. 边界条件检查
4. 性能检查
5. 安全检查

### 问题分级
- 🔴 致命
- 🟡 严重
- 🟢 建议

详见 `references/modules/reviewing.md`

---

## 安装引导

### 自动安装
```bash
# 方式1：复制到.skills目录
cp -r /path/to/ecc-workflow ~/.claude/skills/
```

### 手动安装
```bash
# 1. 创建skills目录
mkdir -p ~/.claude/skills

# 2. 克隆或复制ecc-workflow
git clone https://github.com/affaan-m/ecc-workflow ~/.claude/skills/ecc-workflow

# 3. 重新加载
# 重启Claude Code使新skill生效
```

### 验证安装
```bash
# 测试ECC是否可用
skill("ecc-workflow", "test")
```

---

## 检测与提示原则

1. **按功能检测**：每个命令独立检测
2. **提示后执行**：先提示用户，再执行
3. **提供选择**：安装或使用内置
4. **记住选择**：用户选择后记录偏好
