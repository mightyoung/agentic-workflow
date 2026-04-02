#!/usr/bin/env python3
"""
Worktree Manager - Git Worktree 隔离管理器

为并行任务提供 Git Worktree 隔离：
- 创建独立工作树
- 任务分配到独立 worktree
- 完成后合并回主分支
- 避免文件冲突

用法:
    python worktree_manager.py --op=create --task-id=T001 --branch=feature-x
    python worktree_manager.py --op=list
    python worktree_manager.py --op=merge --task-id=T001
    python worktree_manager.py --op=cleanup
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from typing import Optional

from safe_io import safe_write_json_locked

# 默认 worktree 根目录
DEFAULT_WORKTREE_ROOT = ".worktrees"

# 追踪文件
TRACK_FILE = ".worktree_tracker.json"


def _validate_path(path: str) -> bool:
    """验证路径安全（防止路径遍历攻击）"""
    try:
        real_path = os.path.realpath(path)
        cwd = os.getcwd()
        return real_path.startswith(cwd)
    except OSError:
        return False


def _run_git(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """运行 git 命令"""
    result = subprocess.run(
        ["git"] + args,
        capture_output=True,
        text=True
    )
    if check and result.returncode != 0:
        print(f"Git error: {result.stderr}")
    return result


def _is_git_repo() -> bool:
    """检查当前目录是否是 git 仓库"""
    return os.path.isdir(".git") or os.path.exists(".git")


def load_tracker() -> dict:
    """加载 worktree 追踪数据"""
    if not _validate_path(TRACK_FILE) or not os.path.exists(TRACK_FILE):
        return {"worktrees": [], "version": "1.0"}
    with open(TRACK_FILE, encoding='utf-8') as f:
        data = json.load(f)
        if isinstance(data, dict):
            return data
        return {"worktrees": [], "version": "1.0"}


def save_tracker(data: dict) -> None:
    """保存 worktree 追踪数据"""
    if not _validate_path(TRACK_FILE):
        return
    safe_write_json_locked(TRACK_FILE, data)


def create_worktree(
    task_id: str,
    branch_name: Optional[str] = None,
    base_branch: str = "main",
    worktree_root: str = DEFAULT_WORKTREE_ROOT
) -> dict:
    """创建独立的 worktree"""
    if not _is_git_repo():
        return {"success": False, "error": "Not a git repository"}

    # 生成 worktree 路径
    worktree_path = os.path.join(worktree_root, f"task-{task_id}")

    # 创建目录
    os.makedirs(worktree_path, exist_ok=True)

    # 生成分支名
    if not branch_name:
        branch_name = f"worktree/{task_id}"

    # 检查分支是否已存在
    branch_check = _run_git(["rev-parse", "--verify", branch_name], check=False)
    if branch_check.returncode == 0:
        # 分支已存在，检出
        result = _run_git(["worktree", "add", worktree_path, branch_name])
    else:
        # 创建新分支
        result = _run_git(["worktree", "add", "-b", branch_name, worktree_path, base_branch])

    if result.returncode != 0:
        return {"success": False, "error": result.stderr}

    # 记录到追踪器
    tracker = load_tracker()
    worktree_info = {
        "task_id": task_id,
        "worktree_path": worktree_path,
        "branch_name": branch_name,
        "base_branch": base_branch,
        "created_at": datetime.now().isoformat(),
        "status": "active"
    }
    tracker["worktrees"].append(worktree_info)
    save_tracker(tracker)

    return {
        "success": True,
        "task_id": task_id,
        "worktree_path": worktree_path,
        "branch_name": branch_name,
        "command": f"cd {worktree_path}"
    }


def list_worktrees() -> list[dict]:
    """列出所有 worktree"""
    tracker = load_tracker()
    worktrees = tracker.get("worktrees", [])
    if isinstance(worktrees, list):
        return worktrees
    return []


def get_worktree(task_id: str) -> Optional[dict]:
    """获取指定 task 的 worktree"""
    tracker = load_tracker()
    worktrees: list[dict] = tracker.get("worktrees", [])
    if not isinstance(worktrees, list):
        return None
    for wt in worktrees:
        if isinstance(wt, dict) and wt.get("task_id") == task_id:
            return wt
    return None


def merge_worktree(task_id: str, delete: bool = True) -> dict:
    """合并 worktree 到主分支"""
    wt = get_worktree(task_id)
    if not wt:
        return {"success": False, "error": f"Worktree for task {task_id} not found"}

    worktree_path = wt["worktree_path"]
    branch_name = wt["branch_name"]

    # 检查 worktree 是否存在
    if not os.path.exists(worktree_path):
        return {"success": False, "error": f"Worktree path not found: {worktree_path}"}

    # 切换到主分支并合并
    _run_git(["checkout", wt["base_branch"]])

    # 尝试合并
    merge_result = _run_git(["merge", branch_name], check=False)

    if delete:
        # 删除 worktree
        _run_git(["worktree", "remove", worktree_path, "--force"])

        # 删除分支
        _run_git(["branch", "-d", branch_name], check=False)

        # 从追踪器移除
        tracker = load_tracker()
        tracker["worktrees"] = [
            w for w in tracker.get("worktrees", [])
            if w.get("task_id") != task_id
        ]
        save_tracker(tracker)

    return {
        "success": merge_result.returncode == 0,
        "task_id": task_id,
        "merge_output": merge_result.stdout,
        "merge_error": merge_result.stderr if merge_result.returncode != 0 else None
    }


def cleanup_worktrees(force: bool = False) -> dict:
    """清理所有已完成的 worktree"""
    tracker = load_tracker()
    cleaned = []
    errors = []

    for wt in tracker.get("worktrees", []):
        if wt.get("status") == "completed":
            result = merge_worktree(wt["task_id"], delete=True)
            if result["success"]:
                cleaned.append(wt["task_id"])
            else:
                errors.append({"task_id": wt["task_id"], "error": result.get("error")})

    return {
        "cleaned": cleaned,
        "errors": errors,
        "remaining": len(tracker.get("worktrees", [])) - len(cleaned)
    }


def prune_worktrees() -> dict:
    """清理已失效的 worktree 引用"""
    result = _run_git(["worktree", "prune"], check=False)
    return {
        "success": result.returncode == 0,
        "output": result.stdout,
        "error": result.stderr if result.returncode != 0 else None
    }


def mark_completed(task_id: str) -> dict:
    """标记 worktree 为已完成"""
    tracker = load_tracker()
    for wt in tracker.get("worktrees", []):
        if wt.get("task_id") == task_id:
            wt["status"] = "completed"
            wt["completed_at"] = datetime.now().isoformat()
            save_tracker(tracker)
            return {"success": True, "task_id": task_id}
    return {"success": False, "error": "Task not found"}


def main():
    parser = argparse.ArgumentParser(
        description='Worktree Manager - Git Worktree 隔离管理',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 创建新 worktree
  python worktree_manager.py --op=create --task-id=T001 --branch=feature-x

  # 列出所有 worktree
  python worktree_manager.py --op=list

  # 标记为已完成
  python worktree_manager.py --op=completed --task-id=T001

  # 合并回主分支
  python worktree_manager.py --op=merge --task-id=T001

  # 清理已完成的 worktree
  python worktree_manager.py --op=cleanup
        """
    )
    parser.add_argument('--op', choices=[
        'create', 'list', 'merge', 'cleanup', 'prune', 'completed'
    ], required=True, help='操作类型')
    parser.add_argument('--task-id', '--task_id', dest='task_id',
                       help='任务 ID')
    parser.add_argument('--branch', help='分支名 (默认: worktree/<task_id>)')
    parser.add_argument('--base-branch', dest='base_branch', default='main',
                       help='基础分支 (默认: main)')
    parser.add_argument('--worktree-root', dest='worktree_root',
                       default=DEFAULT_WORKTREE_ROOT, help='Worktree 根目录')
    parser.add_argument('--json', action='store_true', help='输出 JSON 格式')

    args = parser.parse_args()

    if args.op == 'create':
        if not args.task_id:
            print("错误: --task-id 必须指定")
            return 1
        result = create_worktree(
            task_id=args.task_id,
            branch_name=args.branch,
            base_branch=args.base_branch,
            worktree_root=args.worktree_root
        )
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            if result["success"]:
                print("✅ Worktree 创建成功")
                print(f"   任务ID: {result['task_id']}")
                print(f"   路径: {result['worktree_path']}")
                print(f"   分支: {result['branch_name']}")
                print(f"   进入: cd {result['worktree_path']}")
            else:
                print(f"❌ 创建失败: {result.get('error')}")

    elif args.op == 'list':
        worktrees = list_worktrees()
        if args.json:
            print(json.dumps(worktrees, ensure_ascii=False, indent=2))
        else:
            if not worktrees:
                print("无活跃 worktree")
            else:
                print(f"\n活跃 Worktree ({len(worktrees)}):")
                print("-" * 80)
                for wt in worktrees:
                    print(f"  任务: {wt['task_id']}")
                    print(f"  路径: {wt['worktree_path']}")
                    print(f"  分支: {wt['branch_name']}")
                    print(f"  状态: {wt.get('status', 'unknown')}")
                    print(f"  创建: {wt.get('created_at', 'unknown')}")
                    print()

    elif args.op == 'completed':
        if not args.task_id:
            print("错误: --task-id 必须指定")
            return 1
        result = mark_completed(args.task_id)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            if result["success"]:
                print(f"✅ 已标记为完成: {args.task_id}")
            else:
                print(f"❌ 标记失败: {result.get('error')}")

    elif args.op == 'merge':
        if not args.task_id:
            print("错误: --task-id 必须指定")
            return 1
        result = merge_worktree(args.task_id)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            if result["success"]:
                print(f"✅ 合并成功: {args.task_id}")
            else:
                print(f"❌ 合并失败: {result.get('error')}")

    elif args.op == 'cleanup':
        result = cleanup_worktrees()
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print("\n清理完成:")
            print(f"  已清理: {len(result['cleaned'])}")
            print(f"  剩余: {result['remaining']}")
            if result['errors']:
                print(f"  错误: {len(result['errors'])}")

    elif args.op == 'prune':
        result = prune_worktrees()
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            if result["success"]:
                print("✅ 清理完成")
            else:
                print(f"❌ 清理失败: {result.get('error')}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
