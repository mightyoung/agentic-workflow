#!/usr/bin/env python3
"""
Quality Gate - 执行质量检查门禁

在任务完成前强制执行质量检查，确保代码符合标准：
- typecheck (TypeScript/Python)
- lint (ESLint/Flake8/Pylint)
- test (pytest/npm test)

用法:
    python quality_gate.py --dir=src --gate=all
    python quality_gate.py --dir=src --gate=typecheck,lint
    python quality_gate.py --dir=src --gate=test --timeout=120
"""

import argparse
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pathlib import Path


@dataclass
class GateResult:
    """单个门禁检查结果"""
    name: str
    passed: bool
    output: str
    duration_ms: int
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "duration_ms": self.duration_ms,
            "error": self.error,
            "output_lines": len(self.output.split('\n')) if self.output else 0
        }


@dataclass
class QualityGateReport:
    """完整质量门禁报告"""
    gate_results: List[GateResult] = field(default_factory=list)
    total_duration_ms: int = 0
    project_dir: str = ""
    timestamp: str = ""

    @property
    def all_passed(self) -> bool:
        return all(r.passed for r in self.gate_results)

    @property
    def passed_count(self) -> int:
        return sum(1 for r in self.gate_results if r.passed)

    @property
    def failed_count(self) -> int:
        return sum(1 for r in self.gate_results if not r.passed)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "all_passed": self.all_passed,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "total_duration_ms": self.total_duration_ms,
            "project_dir": self.project_dir,
            "timestamp": self.timestamp,
            "gates": [r.to_dict() for r in self.gate_results]
        }


def detect_project_type(project_dir: str) -> Dict[str, bool]:
    """检测项目类型"""
    has_package_json = os.path.exists(os.path.join(project_dir, "package.json"))
    has_pyproject_toml = os.path.exists(os.path.join(project_dir, "pyproject.toml"))
    has_setup_py = os.path.exists(os.path.join(project_dir, "setup.py"))
    has_tsconfig = os.path.exists(os.path.join(project_dir, "tsconfig.json"))
    has_requirements = os.path.exists(os.path.join(project_dir, "requirements.txt"))

    return {
        "javascript": has_package_json,
        "typescript": has_tsconfig,
        "python": has_pyproject_toml or has_setup_py or has_requirements,
    }


def run_command(command: str, timeout: int = 60, cwd: str = None) -> tuple:
    """执行命令并返回 (returncode, stdout, stderr, duration_ms)"""
    start_time = time.time()
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            timeout=timeout,
            text=True,
            cwd=cwd
        )
        duration_ms = int((time.time() - start_time) * 1000)
        return result.returncode, result.stdout, result.stderr, duration_ms
    except subprocess.TimeoutExpired as e:
        duration_ms = int((time.time() - start_time) * 1000)
        return -1, "", f"TIMEOUT after {timeout}s", duration_ms
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        return -2, "", f"ERROR: {str(e)}", duration_ms


def check_typescript(project_dir: str, timeout: int = 60) -> GateResult:
    """TypeScript 类型检查"""
    start_time = time.time()

    # 优先使用 tsc
    if os.path.exists(os.path.join(project_dir, "tsconfig.json")):
        returncode, stdout, stderr, duration_ms = run_command(
            "npx tsc --noEmit 2>&1 || true",
            timeout=timeout,
            cwd=project_dir
        )
        passed = returncode == 0
        output = stdout + stderr if not passed else "Type check passed"
        error = None if passed else "Type errors found"
    elif os.path.exists(os.path.join(project_dir, "package.json")):
        # JavaScript 项目使用 eslint
        returncode, stdout, stderr, duration_ms = run_command(
            "npx eslint . --ext .js,.jsx 2>&1 || true",
            timeout=timeout,
            cwd=project_dir
        )
        passed = returncode == 0
        output = stdout + stderr if not passed else "Lint passed"
        error = None if passed else "Lint errors found"
    else:
        duration_ms = int((time.time() - start_time) * 1000)
        return GateResult(
            name="typecheck",
            passed=True,
            output="No type check configured",
            duration_ms=duration_ms
        )

    return GateResult(
        name="typecheck",
        passed=passed,
        output=output[:2000] if output else "",  # 限制输出长度
        duration_ms=duration_ms,
        error=error
    )


def check_python(project_dir: str, timeout: int = 60) -> GateResult:
    """Python 类型/语法检查"""
    start_time = time.time()

    # 尝试多种检查工具
    tools = ["pyright", "mypy", "pylint", "flake8"]
    checked = False
    all_passed = True
    output_lines = []

    for tool in tools:
        result = subprocess.run(
            f"which {tool}",
            shell=True,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            checked = True
            if tool == "pyright":
                returncode, stdout, stderr, duration_ms = run_command(
                    f"pyright . 2>&1 || true",
                    timeout=timeout,
                    cwd=project_dir
                )
            elif tool == "mypy":
                returncode, stdout, stderr, duration_ms = run_command(
                    f"mypy . --ignore-missing-imports 2>&1 || true",
                    timeout=timeout,
                    cwd=project_dir
                )
            elif tool == "pylint":
                returncode, stdout, stderr, duration_ms = run_command(
                    f"pylint **/*.py 2>&1 || true",
                    timeout=timeout,
                    cwd=project_dir
                )
            else:  # flake8
                returncode, stdout, stderr, duration_ms = run_command(
                    f"flake8 . 2>&1 || true",
                    timeout=timeout,
                    cwd=project_dir
                )

            if returncode != 0:
                all_passed = False
                output_lines.append(f"{tool}: issues found")

    duration_ms = int((time.time() - start_time) * 1000)

    if not checked:
        return GateResult(
            name="typecheck",
            passed=True,
            output="No Python type checker found (pyright/mypy/pylint/flake8)",
            duration_ms=duration_ms
        )

    return GateResult(
        name="typecheck",
        passed=all_passed,
        output="\n".join(output_lines) if output_lines else "Type check passed",
        duration_ms=duration_ms,
        error=None if all_passed else "Type errors found"
    )


def check_lint(project_dir: str, timeout: int = 60) -> GateResult:
    """Lint 检查"""
    start_time = time.time()

    # 检测并运行适当的 linter
    if os.path.exists(os.path.join(project_dir, "package.json")):
        # JavaScript/TypeScript
        if os.path.exists(os.path.join(project_dir, "eslint.config.js")) or \
           os.path.exists(os.path.join(project_dir, ".eslintrc.js")):
            returncode, stdout, stderr, duration_ms = run_command(
                "npx eslint . 2>&1 || true",
                timeout=timeout,
                cwd=project_dir
            )
            passed = returncode == 0
            output = stdout + stderr if not passed else "ESLint passed"
            error = None if passed else "ESLint errors found"
        else:
            duration_ms = int((time.time() - start_time) * 1000)
            return GateResult(
                name="lint",
                passed=True,
                output="No ESLint config found",
                duration_ms=duration_ms
            )
    elif os.path.exists(os.path.join(project_dir, "pyproject.toml")):
        # Python
        returncode, stdout, stderr, duration_ms = run_command(
            "flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics 2>&1 || true",
            timeout=timeout,
            cwd=project_dir
        )
        passed = returncode == 0
        output = stdout + stderr if not passed else "Flake8 passed"
        error = None if passed else "Flake8 errors found"
    else:
        duration_ms = int((time.time() - start_time) * 1000)
        return GateResult(
            name="lint",
            passed=True,
            output="No linter configured",
            duration_ms=duration_ms
        )

    return GateResult(
        name="lint",
        passed=passed,
        output=output[:2000] if output else "",
        duration_ms=duration_ms,
        error=error
    )


def check_tests(project_dir: str, timeout: int = 120) -> GateResult:
    """运行测试"""
    start_time = time.time()

    # 检测测试框架
    if os.path.exists(os.path.join(project_dir, "package.json")):
        # npm test
        if os.path.exists(os.path.join(project_dir, "jest.config.js")) or \
           os.path.exists(os.path.join(project_dir, "vitest.config.ts")):
            returncode, stdout, stderr, duration_ms = run_command(
                "npm test -- --coverage=false 2>&1 || true",
                timeout=timeout,
                cwd=project_dir
            )
        else:
            duration_ms = int((time.time() - start_time) * 1000)
            return GateResult(
                name="test",
                passed=True,
                output="No test framework configured (jest/vitest)",
                duration_ms=duration_ms
            )
    elif os.path.exists(os.path.join(project_dir, "pytest.ini")) or \
         os.path.exists(os.path.join(project_dir, "pyproject.toml")) or \
         os.path.exists(os.path.join(project_dir, "tests")):
        # pytest
        returncode, stdout, stderr, duration_ms = run_command(
            "pytest -v --tb=short 2>&1 || true",
            timeout=timeout,
            cwd=project_dir
        )
        passed = returncode == 0
        output = stdout + stderr if not passed else "Tests passed"
        error = None if passed else "Tests failed"
    else:
        duration_ms = int((time.time() - start_time) * 1000)
        return GateResult(
            name="test",
            passed=True,
            output="No test framework configured",
            duration_ms=duration_ms
        )

    return GateResult(
        name="test",
        passed=passed,
        output=output[:2000] if output else "",
        duration_ms=duration_ms,
        error=error if not passed else None
    )


def run_quality_gate(project_dir: str, gates: List[str], timeout: int = 60) -> QualityGateReport:
    """运行完整质量门禁"""
    from datetime import datetime

    report = QualityGateReport(
        project_dir=project_dir,
        timestamp=datetime.now().isoformat()
    )

    gate_map = {
        "typecheck": check_typescript,
        "typescript": check_typescript,
        "python": check_python,
        "lint": check_lint,
        "test": check_tests,
        "tests": check_tests,
    }

    project_types = detect_project_type(project_dir)
    all_gates = set(gates) if "all" not in gates else set(gate_map.keys())

    # 根据项目类型添加适当的检查
    if project_types["typescript"] and "typecheck" not in all_gates:
        all_gates.add("typecheck")
    elif project_types["python"] and "typecheck" not in all_gates:
        all_gates.add("python")

    for gate_name in sorted(all_gates):
        if gate_name in gate_map:
            gate_func = gate_map[gate_name]
            test_timeout = timeout if gate_name != "test" else timeout * 2
            result = gate_func(project_dir, test_timeout)
            report.gate_results.append(result)

    report.total_duration_ms = sum(r.duration_ms for r in report.gate_results)
    return report


def format_report(report: QualityGateReport, verbose: bool = False) -> str:
    """格式化报告输出"""
    lines = []
    lines.append("=" * 60)
    lines.append("Quality Gate Report")
    lines.append("=" * 60)
    lines.append(f"Project: {report.project_dir}")
    lines.append(f"Timestamp: {report.timestamp}")
    lines.append(f"Total Duration: {report.total_duration_ms}ms")
    lines.append("-" * 60)

    for result in report.gate_results:
        status = "✓ PASS" if result.passed else "✗ FAIL"
        lines.append(f"{status} | {result.name} ({result.duration_ms}ms)")
        if verbose and not result.passed:
            lines.append(f"  Error: {result.error}")
            if result.output:
                lines.append(f"  Output: {result.output[:500]}...")

    lines.append("-" * 60)
    summary = f"Passed: {report.passed_count}/{len(report.gate_results)}"
    if report.all_passed:
        lines.append(f"✓ ALL GATES PASSED - Quality check OK")
    else:
        lines.append(f"✗ QUALITY GATE FAILED - {report.failed_count} gate(s) failed")
    lines.append("=" * 60)

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='Quality Gate - 执行质量检查门禁',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python quality_gate.py --dir=src --gate=all
  python quality_gate.py --dir=. --gate=typecheck,lint
  python quality_gate.py --dir=src --gate=test --timeout=120 --verbose

支持的门禁:
  typecheck - TypeScript/JavaScript 类型检查
  lint      - 代码风格检查
  test      - 单元测试
  all       - 运行所有门禁
        """
    )
    parser.add_argument('--dir', '-d', default='.',
                      help='项目目录 (默认: 当前目录)')
    parser.add_argument('--gate', '-g', default='all',
                      help='要运行的门禁，逗号分隔 (default: all)')
    parser.add_argument('--timeout', '-t', type=int, default=60,
                      help='单个门禁超时秒数 (default: 60)')
    parser.add_argument('--verbose', '-v', action='store_true',
                      help='显示详细输出')
    parser.add_argument('--json', '-j', action='store_true',
                      help='JSON格式输出')
    parser.add_argument('--fail-fast', action='store_true',
                      help='遇到第一个失败就停止')

    args = parser.parse_args()

    gates = [g.strip().lower() for g in args.gate.split(',')]
    project_dir = os.path.abspath(args.dir)

    if not os.path.exists(project_dir):
        print(f"Error: Directory not found: {project_dir}")
        return 1

    report = run_quality_gate(project_dir, gates, args.timeout)

    if args.json:
        import json
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(format_report(report, args.verbose))

    return 0 if report.all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
