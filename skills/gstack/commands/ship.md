---
name: gstack/ship
version: 1.0.0
description: |
  Ship 工作流负责版本发布和部署，确保安全、可追溯的发布流程。
tags: [ship, release, deployment]
requires:
  tools: [Read, Write, Bash]
---

# gstack /ship Command

## Overview

Ship 工作流负责版本发布和部署，确保安全、可追溯的发布流程。

## Contract

### Input

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `scope` | `TARGET_SCOPE` | Yes | 发布范围 |
| `version_type` | `string` | No | 版本类型: `major`, `minor`, `patch` (default: `patch`) |
| `dry_run` | `boolean` | No | 是否为预演模式 (default: `true`) |
| `targets` | `string[]` | No | 部署目标环境列表 |

### Output

| Field | Type | Description |
|-------|------|-------------|
| `status` | `string` | `success`, `failed`, `dry_run` |
| `version` | `string` | 新版本号 |
| `changelog` | `string` | 更新日志 |
| `artifacts` | `Artifact[]` | 发布的产物列表 |
| `deployments` | `Deployment[]` | 部署结果列表 |

### Artifact Structure

```typescript
interface Artifact {
  name: string;
  type: "binary" | "container" | "package";
  path: string;
  checksum: string;
}
```

### Deployment Structure

```typescript
interface Deployment {
  environment: string;
  status: "pending" | "running" | "success" | "failed";
  url?: string;
  timestamp: string;
}
```

## Process

### Step 1: 预检查

```bash
# 1. 检查发布条件
check_git_status()    # 确保工作区干净
check_tests_passed()  # 确保测试通过
check_version_bump()  # 确保版本已更新

# 2. 确定发布类型
VERSION_TYPE=$(determine_version_type)
```

### Step 2: 版本管理

```bash
# 根据发布类型更新版本
case $VERSION_TYPE in
  major)
    bump_major_version
    ;;
  minor)
    bump_minor_version
    ;;
  patch)
    bump_patch_version
    ;;
esac
```

### Step 3: 构建产物

```bash
# 构建所有产物
build_artifacts() {
  npm run build          # 前端构建
  docker build           # 容器镜像
  npm pack              # npm 包
}
```

### Step 4: 生成更新日志

```bash
# 从 git log 生成 changelog
CHANGELOG=$(generate_changelog)
```

### Step 5: 部署 (可选)

```bash
# 部署到目标环境
for env in $TARGETS; do
  deploy_to "$env"
done
```

## Integration with REVIEWING

Ship 工作流通常在 REVIEWING 阶段之后执行，作为发布前的最后检查。

## Exit Criteria

| Status | Condition |
|--------|-----------|
| `success` | 构建成功、测试通过、版本已发布 |
| `failed` | 任何步骤失败 |
| `dry_run` | 预演模式，只检查不执行 |

## Safety Checks

- [ ] Git 工作区干净
- [ ] 所有测试通过
- [ ] 版本已正确更新
- [ ] CHANGELOG 已生成
- [ ] 产物已签名验证
