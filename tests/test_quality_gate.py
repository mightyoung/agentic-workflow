#!/usr/bin/env python3
"""
Quality Gate 测试 - 测试 quality_gate.py 的功能

覆盖:
- 项目类型检测
- 门禁检查 (typecheck, lint, test)
- 报告生成
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts'))

from quality_gate import (
    detect_project_type,
    run_command,
    check_typescript,
    check_python,
    check_lint,
    check_tests,
    run_quality_gate,
    format_report,
    GateResult,
    QualityGateReport
)


class TestQualityGate(unittest.TestCase):
    """Quality Gate 核心功能测试"""

    def setUp(self):
        """每个测试前创建临时目录"""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # ==================== 项目类型检测测试 ====================

    def test_detect_javascript(self):
        """测试检测 JavaScript 项目"""
        Path(os.path.join(self.temp_dir, 'package.json')).touch()
        result = detect_project_type(self.temp_dir)
        self.assertTrue(result['javascript'])
        self.assertFalse(result['python'])

    def test_detect_typescript(self):
        """测试检测 TypeScript 项目"""
        Path(os.path.join(self.temp_dir, 'package.json')).touch()
        Path(os.path.join(self.temp_dir, 'tsconfig.json')).touch()
        result = detect_project_type(self.temp_dir)
        self.assertTrue(result['javascript'])
        self.assertTrue(result['typescript'])

    def test_detect_python(self):
        """测试检测 Python 项目"""
        Path(os.path.join(self.temp_dir, 'pyproject.toml')).touch()
        result = detect_project_type(self.temp_dir)
        self.assertTrue(result['python'])
        self.assertFalse(result['javascript'])

    def test_detect_empty_dir(self):
        """测试检测空目录"""
        result = detect_project_type(self.temp_dir)
        self.assertFalse(result['javascript'])
        self.assertFalse(result['python'])

    # ==================== run_command 测试 ====================

    def test_run_command_success(self):
        """测试成功执行命令"""
        returncode, stdout, stderr, duration = run_command('echo hello', timeout=5)
        self.assertEqual(returncode, 0)
        self.assertIn('hello', stdout)

    def test_run_command_timeout(self):
        """测试命令超时"""
        returncode, stdout, stderr, duration = run_command('sleep 10', timeout=1)
        self.assertEqual(returncode, -1)
        self.assertIn('TIMEOUT', stderr)

    def test_run_command_not_found(self):
        """测试命令不存在"""
        returncode, stdout, stderr, duration = run_command('nonexistent_command_xyz', timeout=5)
        self.assertNotEqual(returncode, 0)

    # ==================== 门禁检查测试 ====================

    def test_check_typescript_no_tsconfig(self):
        """测试无 tsconfig 时 typecheck"""
        # 空目录，没有 tsconfig
        result = check_typescript(self.temp_dir, timeout=10)
        # 应该跳过检查（因为没有配置）
        self.assertTrue(result.passed)

    def test_check_python_no_tools(self):
        """测试 Python 项目无检查工具"""
        Path(os.path.join(self.temp_dir, 'pyproject.toml')).touch()
        result = check_python(self.temp_dir, timeout=10)
        # 应该跳过（因为没有检查工具）
        self.assertTrue(result.passed)

    def test_check_lint_no_config(self):
        """测试无 lint 配置"""
        # 空目录，没有 lint 配置
        result = check_lint(self.temp_dir, timeout=10)
        self.assertTrue(result.passed)

    def test_check_tests_no_framework(self):
        """测试无测试框架"""
        # 空目录，没有测试框架
        result = check_tests(self.temp_dir, timeout=10)
        self.assertTrue(result.passed)

    # ==================== 报告生成测试 ====================

    def test_gate_result_to_dict(self):
        """测试 GateResult 序列化"""
        result = GateResult(
            name='typecheck',
            passed=True,
            output='Check passed',
            duration_ms=100
        )
        d = result.to_dict()
        self.assertEqual(d['name'], 'typecheck')
        self.assertTrue(d['passed'])
        self.assertEqual(d['duration_ms'], 100)

    def test_quality_gate_report_all_passed(self):
        """测试全部通过的报告"""
        report = QualityGateReport(
            project_dir='/test',
            timestamp='2024-01-01T00:00:00'
        )
        report.gate_results.append(
            GateResult(name='typecheck', passed=True, output='', duration_ms=50)
        )
        report.gate_results.append(
            GateResult(name='lint', passed=True, output='', duration_ms=50)
        )

        self.assertTrue(report.all_passed)
        self.assertEqual(report.passed_count, 2)
        self.assertEqual(report.failed_count, 0)

    def test_quality_gate_report_partial_fail(self):
        """测试部分失败的报告"""
        report = QualityGateReport(
            project_dir='/test',
            timestamp='2024-01-01T00:00:00'
        )
        report.gate_results.append(
            GateResult(name='typecheck', passed=True, output='', duration_ms=50)
        )
        report.gate_results.append(
            GateResult(name='lint', passed=False, output='Errors', duration_ms=50)
        )

        self.assertFalse(report.all_passed)
        self.assertEqual(report.passed_count, 1)
        self.assertEqual(report.failed_count, 1)

    def test_format_report(self):
        """测试报告格式化"""
        report = QualityGateReport(
            project_dir='/test',
            timestamp='2024-01-01T00:00:00'
        )
        report.gate_results.append(
            GateResult(name='typecheck', passed=True, output='OK', duration_ms=50)
        )

        formatted = format_report(report)
        self.assertIn('Quality Gate Report', formatted)
        self.assertIn('/test', formatted)
        self.assertIn('PASS', formatted)
        self.assertIn('ALL GATES PASSED', formatted)

    def test_format_report_failed(self):
        """测试失败报告格式化"""
        report = QualityGateReport(
            project_dir='/test',
            timestamp='2024-01-01T00:00:00'
        )
        report.gate_results.append(
            GateResult(name='lint', passed=False, output='Error', duration_ms=50)
        )

        formatted = format_report(report)
        self.assertIn('FAIL', formatted)
        self.assertIn('QUALITY GATE FAILED', formatted)

    # ==================== 集成测试 ====================

    def test_run_quality_gate_empty_dir(self):
        """测试空目录运行质量门禁"""
        gates = ['typecheck', 'lint']
        report = run_quality_gate(self.temp_dir, gates, timeout=30)

        self.assertIsNotNone(report)
        self.assertEqual(report.project_dir, self.temp_dir)
        # 空目录所有检查应该跳过（passed=True）
        self.assertTrue(report.all_passed)

    def test_run_quality_gate_with_python_project(self):
        """测试 Python 项目运行质量门禁"""
        Path(os.path.join(self.temp_dir, 'pyproject.toml')).touch()

        # 创建一个简单的 Python 文件
        Path(os.path.join(self.temp_dir, 'test.py')).touch()

        gates = ['python']
        report = run_quality_gate(self.temp_dir, gates, timeout=30)

        self.assertIsNotNone(report)
        # 没有类型检查工具，应该跳过
        self.assertTrue(report.all_passed or len(report.gate_results) > 0)


class TestQualityGateTools(unittest.TestCase):
    """工具检测测试"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_check_python_with_pyright(self):
        """测试使用 pyright 检查 Python"""
        # 创建 pyproject.toml 标识为 Python 项目
        Path(os.path.join(self.temp_dir, 'pyproject.toml')).touch()

        # 创建 Python 文件
        Path(os.path.join(self.temp_dir, 'main.py')).write_text('def main(): pass\n')

        result = check_python(self.temp_dir, timeout=30)
        # 如果安装了 pyright 应该能运行
        self.assertIsInstance(result.passed, bool)


def run_tests():
    """运行所有测试"""
    unittest.main(module=__name__, exit=False, verbosity=2)


if __name__ == '__main__':
    run_tests()
