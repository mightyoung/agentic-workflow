#!/usr/bin/env python3
"""
Artifact Registry Tests - 工件注册表专项测试

测试工件注册表的核心功能：
1. 工件注册
2. 工件查询
3. 工件类型过滤
4. 工件ID生成
"""

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from unified_state import (
    ARTIFACT_REGISTRY_FILE,
    ArtifactType,
    _load_artifact_registry,
    _save_artifact_registry,
    get_artifact_by_id,
    get_artifacts,
    register_artifact,
)


class TestArtifactRegistry(unittest.TestCase):
    """工件注册表测试"""

    def setUp(self):
        """每个测试使用独立的工作目录"""
        self.workdir = tempfile.mkdtemp(prefix="artifact_test_")

    def tearDown(self):
        """清理临时目录"""
        if os.path.exists(self.workdir):
            shutil.rmtree(self.workdir, ignore_errors=True)

    def test_register_artifact(self):
        """测试注册工件"""
        artifact = register_artifact(
            self.workdir,
            ArtifactType.PROGRESS,
            "progress.md",
            "PLANNING",
            "system",
        )
        self.assertIn("id", artifact)
        self.assertEqual(artifact["type"], ArtifactType.PROGRESS)
        self.assertEqual(artifact["phase"], "PLANNING")
        self.assertEqual(artifact["generated_by"], "system")

    def test_register_multiple_artifacts(self):
        """测试注册多个工件"""
        artifact1 = register_artifact(
            self.workdir,
            ArtifactType.PROGRESS,
            "progress.md",
            "PLANNING",
        )
        artifact2 = register_artifact(
            self.workdir,
            ArtifactType.PLAN,
            "task_plan.md",
            "PLANNING",
        )
        self.assertNotEqual(artifact1["id"], artifact2["id"])

    def test_get_artifacts_all(self):
        """测试获取所有工件"""
        # 注册测试工件
        register_artifact(self.workdir, ArtifactType.PROGRESS, "progress.md", "PLANNING")
        register_artifact(self.workdir, ArtifactType.PLAN, "task_plan.md", "PLANNING")
        register_artifact(self.workdir, ArtifactType.SESSION, "SESSION-STATE.md", "EXECUTING")

        artifacts = get_artifacts(self.workdir)
        self.assertGreaterEqual(len(artifacts), 3)

    def test_get_artifacts_by_type(self):
        """测试按类型过滤"""
        # 使用唯一的文件名避免与其他测试冲突
        register_artifact(self.workdir, ArtifactType.PROGRESS, "progress_type.md", "PLANNING")
        register_artifact(self.workdir, ArtifactType.PROGRESS, "progress_type2.md", "EXECUTING")
        register_artifact(self.workdir, ArtifactType.PLAN, "task_plan.md", "PLANNING")

        progress_artifacts = get_artifacts(self.workdir, artifact_type=ArtifactType.PROGRESS)
        # 至少有两个我们刚注册的PROGRESS类型工件
        self.assertGreaterEqual(len(progress_artifacts), 2)
        for a in progress_artifacts:
            self.assertEqual(a["type"], ArtifactType.PROGRESS)

    def test_get_artifacts_by_phase(self):
        """测试按phase过滤"""
        register_artifact(self.workdir, ArtifactType.PROGRESS, "progress_phase.md", "PLANNING")
        register_artifact(self.workdir, ArtifactType.PROGRESS, "progress_phase2.md", "EXECUTING")

        planning_artifacts = get_artifacts(self.workdir, phase="PLANNING")
        self.assertGreaterEqual(len(planning_artifacts), 1)
        self.assertEqual(planning_artifacts[0]["phase"], "PLANNING")

    def test_get_artifact_by_id(self):
        """测试根据ID获取工件"""
        registered = register_artifact(
            self.workdir,
            ArtifactType.TRACKER,
            ".task_tracker.json",
            "PLANNING",
        )
        artifact_id = registered["id"]

        found = get_artifact_by_id(self.workdir, artifact_id)
        self.assertIsNotNone(found)
        self.assertEqual(found["id"], artifact_id)

    def test_get_nonexistent_artifact(self):
        """测试获取不存在的工件"""
        found = get_artifact_by_id(self.workdir, "nonexistent_id")
        self.assertIsNone(found)

    def test_artifact_metadata(self):
        """测试工件元数据"""
        metadata = {"key": "value", "count": 42}
        artifact = register_artifact(
            self.workdir,
            ArtifactType.CUSTOM,
            "custom.json",
            "EXECUTING",
            metadata=metadata,
        )
        self.assertEqual(artifact["metadata"], metadata)

    def test_load_save_registry(self):
        """测试注册表加载保存"""
        registry = _load_artifact_registry(self.workdir)
        self.assertIn("artifacts", registry)

        # 保存新数据
        new_registry = {
            "artifacts": [
                {"id": "test_1", "type": ArtifactType.STATE, "path": "test.json"}
            ],
            "updated_at": "2024-01-01T00:00:00",
        }
        _save_artifact_registry(self.workdir, new_registry)

        # 重新加载
        loaded = _load_artifact_registry(self.workdir)
        self.assertEqual(len(loaded["artifacts"]), 1)

    def test_artifact_created_at(self):
        """测试创建时间戳"""
        artifact = register_artifact(
            self.workdir,
            ArtifactType.REVIEW,
            "review.md",
            "REVIEWING",
        )
        self.assertIn("created_at", artifact)
        self.assertIsNotNone(artifact["created_at"])


class TestArtifactTypes(unittest.TestCase):
    """工件类型枚举测试"""

    def test_artifact_types_exist(self):
        """测试所有工件类型都存在"""
        self.assertEqual(ArtifactType.STATE, "state")
        self.assertEqual(ArtifactType.TRAJECTORY, "trajectory")
        self.assertEqual(ArtifactType.PLAN, "plan")
        self.assertEqual(ArtifactType.FINDINGS, "findings")
        self.assertEqual(ArtifactType.REVIEW, "review")
        self.assertEqual(ArtifactType.PROGRESS, "progress")
        self.assertEqual(ArtifactType.SESSION, "session")
        self.assertEqual(ArtifactType.TRACKER, "tracker")
        self.assertEqual(ArtifactType.CUSTOM, "custom")

    def test_artifact_registry_file_constant(self):
        """测试注册表文件常量"""
        self.assertEqual(ARTIFACT_REGISTRY_FILE, ".artifacts.json")


if __name__ == "__main__":
    unittest.main(verbosity=2)
