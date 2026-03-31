# Windows 批处理脚本 (win/)

> 本目录包含 Windows 批处理脚本（.bat），提供与 Unix/Linux 脚本相同的功能。

## 脚本列表

| 脚本 | 功能 | 对应 Bash 版本 |
|------|------|----------------|
| `init_session.bat` | 初始化会话 | `../init_session.sh` |
| `check_template.bat` | 检查模板 | `../check_template.sh` |
| `check_env.bat` | 环境检查 | `../check_env.sh` |
| `quick_review.bat` | 快速审查 | `../quick_review.sh` |
| `create_plan.bat` | 创建计划 | `../create_plan.sh` |

## 使用方式

在 Windows 环境下，Agent 应自动检测系统并使用 .bat 版本：

```batch
:: Windows 检测逻辑
if "%OS%"=="Windows_NT" (
    scripts\win\init_session.bat
) else (
    bash scripts/init_session.sh
)
```

## 主要差异

| 特性 | Windows (.bat) | Unix (.sh) |
|------|---------------|------------|
| 变量赋值 | `set VAR=value` | `VAR=value` |
| 变量引用 | `%VAR%` | `$VAR` |
| 路径分隔 | `\` | `/` |
| 文件存在 | `if exist file` | `if [ -f file ]` |
| 目录创建 | `mkdir` 或 `md` | `mkdir -p` |
| 颜色输出 | 有限支持 | ANSI 转义序列 |
| 命令分隔 | `&` 或 `&&` | `;` 或 `&&` |

## 调用示例

```batch
:: 初始化会话
scripts\win\init_session.bat

:: 检查环境
scripts\win\check_env.bat

:: 创建计划
scripts\win\create_plan.bat "新功能开发"
```

## 注意事项

1. Windows 批处理脚本不支持 ANSI 颜色码，需要移除颜色转义序列
2. 路径使用反斜杠 `\`
3. 某些命令参数可能与 Unix 版本不同
4. 建议在 Git Bash 或 WSL 环境下使用 Bash 版本以获得最佳兼容性
