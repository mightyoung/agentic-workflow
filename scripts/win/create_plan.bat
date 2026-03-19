@echo off
:: create_plan.bat - 创建任务计划文件 (Windows)
:: 用法: scripts\win\create_plan.bat [任务名称] [项目路径]

setlocal enabledelayedexpansion

set "TASK_NAME=%~1"
if "%TASK_NAME%"=="" set "TASK_NAME=新任务"

set "PROJECT_DIR=%~2"
if "%PROJECT_DIR%"=="" set "PROJECT_DIR=."

:: 生成日期戳
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do set "DATE_STAMP=%%c-%%a-%%b"

set "FILENAME=%PROJECT_DIR%\task_plan_%DATE_STAMP%.md"

:: 检查是否已存在
if exist "%FILENAME%" (
    echo 文件已存在: %FILENAME%
    exit /b 1
)

:: 创建任务计划文件
(
echo # 任务计划: %TASK_NAME%
echo.
echo # 创建时间: %DATE_STAMP% %TIME%
echo.
echo ## 目标
echo # 一句话描述要完成的任务
echo.
echo ## 专家视角
echo # 这个问题谁最懂？TA会怎么说？
echo.
echo ## 任务元数据
echo.
echo ^| 字段 ^| 值 ^|
echo ^|------^|---^|
echo ^| 优先级 ^| P0 / P1 / P2 / P3 ^|
echo ^| 估计时间 ^| X 分钟 ^|
echo ^| 依赖任务 ^| [task_id, ...] ^|
echo ^| 可独立测试 ^| true / false ^|
echo.
echo ## 阶段
echo.
echo ### Phase 1: [阶段名]
echo - [ ] 任务1 (P0, 5min, 依赖-^)
echo - [ ] 任务2 (P1, 10min, 依赖-^)
echo.
echo ### Phase 2: [阶段名]
echo - [ ] 任务3 (P0, 15min, 依赖task1^)
echo - [ ] 任务4 (P2, 5min, 依赖task2^)
echo.
echo ## 进度
echo.
echo ^| 阶段 ^| 状态 ^| 完成度 ^|
echo ^|------^|------^|--------^|
echo ^| Phase 1 ^| 待开始 ^| 0%% ^|
echo ^| Phase 2 ^| 待开始 ^| 0%% ^|
echo.
echo ## 决策记录
echo.
echo ^| 决策 ^| 理由 ^| VFM评分 ^| 日期 ^|
echo ^|------^|------^|--------^|------^|
echo ^| ^| ^| ^| ^|
echo.
echo ## 遇到的问题
echo.
echo ^| 问题 ^| 尝试次数 ^| 解决方案 ^|
echo ^|------^|----------^|----------^|
echo ^| ^| ^| ^|
echo.
echo ## 自动追踪
echo.
echo ^| 任务ID ^| 状态变更 ^| 时间 ^| 备注 ^|
echo ^|--------^|----------^|------^|------^|
) > "%FILENAME%"

echo 已创建: %FILENAME%
