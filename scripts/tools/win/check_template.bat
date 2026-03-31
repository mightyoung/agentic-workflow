@echo off
:: check_template.bat - 检查任务计划模板是否存在 (Windows)
:: 用法: scripts\win\check_template.bat [项目路径]

setlocal enabledelayedexpansion

set "PROJECT_DIR=%~1"
if "%PROJECT_DIR%"=="" set "PROJECT_DIR=."

set "TEMPLATES=references\templates\task_plan.md;references\templates\findings.md;references\templates\progress.md"

echo 检查项目模板...
echo 项目目录: %PROJECT_DIR%
echo.

set "missing=0"

for %%F in ("%TEMPLATES:;=" "%") do (
    set "template=%%~F"
    set "template=!template:~1,-1!"
    if exist "%PROJECT_DIR%\!template!" (
        echo [OK] !template!
    ) else (
        echo [MISSING] !template!
        set /a missing+=1
    )
)

echo.
if %missing%==0 (
    echo 所有模板文件完整 [OK]
    exit /b 0
) else (
    echo 缺少 %missing% 个模板文件
    exit /b 1
)
