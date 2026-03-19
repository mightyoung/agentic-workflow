@echo off
:: check_env.bat - 检查运行环境 (Windows)
:: 用法: scripts\win\check_env.bat

echo ====================================
echo === 环境检查 ===
echo ====================================
echo.

:: 检查工具是否存在
echo 基础工具:

where git >nul 2>&1
if %errorlevel%==0 (
    for /f "delims=" %%v in ('git --version 2^>nul') do echo [OK] git: %%v
) else (
    echo [MISSING] git
)

where python >nul 2>&1
if %errorlevel%==0 (
    for /f "delims=" %%v in ('python --version 2^>nul') do echo [OK] python: %%v
) else (
    where python3 >nul 2>&1
    if %errorlevel%==0 (
        for /f "delims=" %%v in ('python3 --version 2^>nul') do echo [OK] python: %%v
    ) else (
        echo [MISSING] python
    )
)

where node >nul 2>&1
if %errorlevel%==0 (
    for /f "delims=" %%v in ('node --version 2^>nul') do echo [OK] node: %%v
) else (
    echo [MISSING] node
)

echo.
echo 可选工具:

where gh >nul 2>&1
if %errorlevel%==0 (
    for /f "delims=" %%v in ('gh --version 2^>nul ^| findstr "gh"') do echo [OK] gh: %%v
) else (
    echo [MISSING] gh (需要安装 GitHub CLI^)
)

where cargo >nul 2>&1
if %errorlevel%==0 (
    for /f "delims=" %%v in ('cargo --version 2^>nul') do echo [OK] cargo: %%v
) else (
    echo [MISSING] cargo (Rust^)
)

where go >nul 2>&1
if %errorlevel%==0 (
    for /f "delims=" %%v in ('go version 2^>nul') do echo [OK] go: %%v
) else (
    echo [MISSING] go
)

echo.
echo 环境变量:

if defined TAVILY_API_KEY (
    echo [OK] TAVILY_API_KEY 已设置
) else (
    echo [MISSING] TAVILY_API_KEY 未设置
)

if defined OPENAI_API_KEY (
    echo [OK] OPENAI_API_KEY 已设置
) else (
    echo [MISSING] OPENAI_API_KEY 未设置
)

echo.
where claude >nul 2>&1
if %errorlevel%==0 (
    for /f "delims=" %%v in ('claude --version 2^>nul ^| findstr "Claude"') do echo [OK] Claude Code: %%v
) else (
    echo [MISSING] Claude Code 未安装
)

echo.
echo ====================================
echo === 检查完成 ===
echo ====================================
