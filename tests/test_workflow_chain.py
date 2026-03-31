from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
import unittest

from router_helpers import load_router_module


REPO_ROOT = Path(__file__).resolve().parent.parent
ROUTER = load_router_module()


class TestWorkflowChain(unittest.TestCase):
    def test_router_to_plan_to_state_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            template_dir = workdir / "references" / "templates"
            template_dir.mkdir(parents=True)
            (template_dir / "task_plan.md").write_text(
                (REPO_ROOT / "references" / "templates" / "task_plan.md").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            (template_dir / "findings.md").write_text(
                (REPO_ROOT / "references" / "templates" / "findings.md").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            (template_dir / "progress.md").write_text(
                (REPO_ROOT / "references" / "templates" / "progress.md").read_text(encoding="utf-8"),
                encoding="utf-8",
            )

            router_result = ROUTER.route("帮我规划一个登录功能")
            self.assertEqual(router_result[0], "STAGE")
            self.assertEqual(router_result[1], "PLANNING")

            create_plan = subprocess.run(
                ["bash", str(REPO_ROOT / "scripts" / "create_plan.sh"), "登录功能", "."],
                cwd=workdir,
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertIn("已创建:", create_plan.stdout)

            plan_file = workdir / "task_plan.md"
            self.assertTrue(plan_file.exists())
            plan_text = plan_file.read_text(encoding="utf-8")
            self.assertIn("登录功能", plan_text)
            self.assertIn("## Goals", plan_text)
            self.assertIn("## Verification", plan_text)

            init_session = subprocess.run(
                ["bash", str(REPO_ROOT / "scripts" / "init_session.sh"), "."],
                cwd=workdir,
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertIn("已初始化:", init_session.stdout)

            session_file = workdir / "SESSION-STATE.md"
            self.assertTrue(session_file.exists())
            self.assertIn("当前任务", session_file.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
