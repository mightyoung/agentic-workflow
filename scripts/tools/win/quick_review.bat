@echo off
:: quick_review.bat - 快速代码审查 (Windows)
:: 用法: scripts\win\quick_review.bat [文件路径或目录]

setlocal enabledelayedexpansion

set "TARGET=%~1"
if "%TARGET%"=="" set "TARGET=."

echo ====================================
echo === 快速代码审查 ===
echo ====================================
echo 目标: %TARGET%
echo.

:: 文件统计
echo 文件统计:

if exist "%TARGET%\*" (
    set count=0
    for /r "%TARGET%" %%F in (*.py *.js *.ts *.go *.java) do (
        set /a count+=1
    )
    echo   文件数: !count!
) else (
    if exist "%TARGET%" (
        echo   文件: %TARGET%
        for %%F in ("%TARGET%") do (
            set lines=0
            for /f %%a in ('find /c /v "" ^< "%TARGET%"') do set lines=%%a
            echo   行数: !lines!
        )
    )
)

echo.
echo 检查常见问题:

:: 检查 TODO/FIXME (使用 findstr)
findstr /s /i /m "TODO FIXME XXX" "%TARGET%" 2>nul | findstr /v ".git" >nul
if %errorlevel%==0 (
    echo   [WARNING] 发现 TODO/FIXME
    findstr /s /i /n "TODO FIXME" "%TARGET%" 2>nul | findstr /v ".git" | findstr /r "^.*:.*[0-9]:" | more +2 | more +0
) else (
    echo   [OK] 无 TODO/FIXME
)

:: 检查硬编码密码
findstr /s /i /m /r "password.*=.*['\"][^'\"]{8,}" "%TARGET%" 2>nul | findstr /v ".git" >nul
if %errorlevel%==0 (
    echo   [WARNING] 发现疑似硬编码凭据
) else (
    echo   [OK] 无硬编码凭据
)

:: 检查空文件
set empty_count=0
for /r "%TARGET%" %%F in (*) do (
    if %%~zF==0 (
        set /a empty_count+=1
    )
)
if %empty_count% gtr 0 (
    echo   [WARNING] 发现 %empty_count% 个空文件
) else (
    echo   [OK] 无空文件
)

echo.
echo ====================================
echo === 审查完成 ===
echo ====================================
