@echo off
:: init_session.bat - 初始化会话状态 (Windows)
:: 用法: scripts\win\init_session.bat [项目路径]

setlocal enabledelayedexpansion

set "PROJECT_DIR=%~1"
if "%PROJECT_DIR%"=="" set "PROJECT_DIR=."

:: 检查是否已存在
if exist "%PROJECT_DIR%\SESSION-STATE.md" (
    echo SESSION-STATE.md 已存在
    echo 如需重新初始化，请先删除现有文件
    exit /b 0
)

:: 获取当前时间
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do set "TIMESTAMP=%%c-%%a-%%b"
for /f "tokens=1-2 delims=: " %%a in ('time /t') do set "TIMESTAMP=%TIMESTAMP% %%a:%%b"

:: 创建 SESSION-STATE.md
(
echo # SESSION-STATE.md
echo.
echo # 自动生成的工作内存文件 - %DATE%
echo.
echo # 当前任务
echo - **任务描述**: (未设置^)
echo - **阶段**: IDLE
echo - **开始时间**: %TIMESTAMP%
echo - **优先级**: P2
echo.
echo # 关键信息 (WAL协议收集^)
echo.
echo ## 修正记录
echo ^| 时间 ^| 原始理解 ^| 正确理解 ^|
echo ^|------^|----------^|----------^|
echo.
echo ## 用户偏好
echo - **风格偏好**:
echo - **技术偏好**:
echo.
echo ## 决策记录
echo ^| 时间 ^| 决策内容 ^| 理由 ^|
echo ^|------^|----------^|------^|
echo.
echo ## 具体数值
echo ^| 类型 ^| 值 ^|
echo ^|------^|---^|
echo.
echo # 上下文进度
echo.
echo ## 已完成步骤
echo - [ ]
echo.
echo ## 当前步骤
echo -
echo.
echo ## 遇到的问题
echo ^| 问题 ^| 尝试次数 ^| 解决方案 ^|
echo ^|------^|----------^|----------^|
) > "%PROJECT_DIR%\SESSION-STATE.md"

echo 已初始化: %PROJECT_DIR%\SESSION-STATE.md
