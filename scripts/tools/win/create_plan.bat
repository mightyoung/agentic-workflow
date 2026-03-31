@echo off
:: create_plan.bat - 创建项目内 task_plan.md (Windows)
:: 用法: scripts\win\create_plan.bat [任务名称] [项目路径]

setlocal enabledelayedexpansion

set "TASK_NAME=%~1"
if "%TASK_NAME%"=="" set "TASK_NAME=新任务"

set "PROJECT_DIR=%~2"
if "%PROJECT_DIR%"=="" set "PROJECT_DIR=."

set "TEMPLATE_FILE=%PROJECT_DIR%\references\templates\task_plan.md"
set "FILENAME=%PROJECT_DIR%\task_plan.md"

if exist "%FILENAME%" (
    echo 文件已存在: %FILENAME%
    exit /b 1
)

if not exist "%TEMPLATE_FILE%" (
    echo 模板不存在: %TEMPLATE_FILE%
    exit /b 1
)

powershell -NoProfile -Command ^
  "$content = Get-Content -Raw '%TEMPLATE_FILE%';" ^
  "$content = $content.Replace('{{TASK_NAME}}', '%TASK_NAME%');" ^
  "$content = $content.Replace('{{CREATED_AT}}', (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'));" ^
  "Set-Content -Path '%FILENAME%' -Value $content -Encoding UTF8"

echo 已创建: %FILENAME%
