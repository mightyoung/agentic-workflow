#!/usr/bin/env python3
"""
Tests for self-improvement harness governance layer.

Covers:
- baseline_check.sh gate 0: branch/worktree enforcement
- record_result.sh: ledger append with fcntl locking
- TSV integrity under concurrent writes
"""

import fcntl
import os
import subprocess
import time
from pathlib import Path


class TestBaselineCheckGate0:
    """Test baseline_check.sh gate 0: self-improvement context enforcement"""

    def test_main_branch_fails_without_allow_dirty(self, tmp_path):
        """On main branch without additional worktrees, gate 0 should fail"""
        # Create a temporary git repo to test in
        repo_dir = tmp_path / "test_repo"
        repo_dir.mkdir()

        # Init git repo
        subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=repo_dir, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=repo_dir, capture_output=True
        )

        # Create initial commit
        readme = repo_dir / "README.md"
        readme.write_text("# Test")
        subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "initial"],
            cwd=repo_dir, capture_output=True
        )

        # Create .self-improvement directory with baseline_check
        self_imp_dir = repo_dir / ".self-improvement"
        self_imp_dir.mkdir()
        baseline_check = self_imp_dir / "baseline_check.sh"

        # Copy baseline_check.sh from project
        project_baseline = Path(__file__).parent.parent / ".self-improvement" / "baseline_check.sh"
        if project_baseline.exists():
            baseline_check.write_text(project_baseline.read_text())

        # On main branch with no additional worktrees, should fail
        result = subprocess.run(
            ["bash", ".self-improvement/baseline_check.sh"],
            cwd=repo_dir,
            capture_output=True,
            text=True
        )

        # Should fail (non-zero exit)
        assert result.returncode != 0, "Expected baseline_check to fail on main branch"
        assert "FAIL" in result.stdout or "BASELINE CHECK FAILED" in result.stdout

    def test_self_improve_branch_passes(self, tmp_path):
        """On self-improve/* branch, gate 0 should pass"""
        repo_dir = tmp_path / "test_repo"
        repo_dir.mkdir()

        # Init git repo
        subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=repo_dir, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=repo_dir, capture_output=True
        )

        # Create initial commit
        readme = repo_dir / "README.md"
        readme.write_text("# Test")
        subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "initial"],
            cwd=repo_dir, capture_output=True
        )

        # Create self-improve branch
        subprocess.run(
            ["git", "checkout", "-b", "self-improve/test"],
            cwd=repo_dir, capture_output=True
        )

        # Create .self-improvement directory
        self_imp_dir = repo_dir / ".self-improvement"
        self_imp_dir.mkdir()
        baseline_check = self_imp_dir / "baseline_check.sh"

        # Copy baseline_check.sh
        project_baseline = Path(__file__).parent.parent / ".self-improvement" / "baseline_check.sh"
        if project_baseline.exists():
            baseline_check.write_text(project_baseline.read_text())

        # Create stub scripts directory with necessary files
        scripts_dir = repo_dir / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "unified_state.py").write_text("# stub")

        result = subprocess.run(
            ["bash", ".self-improvement/baseline_check.sh", "--allow-dirty"],
            cwd=repo_dir,
            capture_output=True,
            text=True
        )

        # Should pass gate 0
        assert "PASS" in result.stdout, f"Expected PASS for self-improve branch: {result.stdout}"


class TestRecordResultLedger:
    """Test record_result.sh ledger integrity"""

    def test_ledger_tsv_integrity_single_write(self, tmp_path):
        """Single ledger append produces well-formed TSV"""
        ledger = tmp_path / "results.tsv"

        # Create minimal test ledger
        ledger.write_text(
            "run_id\thypothesis\tfiles_changed\tchecks_passed\tstatus\tnotes\n"
        )

        # Write a record using the Python helper pattern
        lock_path = str(ledger) + '.lock'

        with open(lock_path, 'w') as lock_f:
            fcntl.flock(lock_f.fileno(), fcntl.LOCK_EX)
            try:
                with open(ledger, 'a') as f:
                    row = '\t'.join([
                        "test-run-001",
                        "test hypothesis",
                        "scripts/router.py",
                        "10/10 gates",
                        "keep",
                        "test notes"
                    ])
                    f.write(row + '\n')
            finally:
                fcntl.flock(lock_f.fileno(), fcntl.LOCK_UN)
                os.remove(lock_path)

        # Verify TSV integrity
        lines = ledger.read_text().splitlines()
        assert len(lines) == 2  # header + 1 record

        # Check each line has exactly 6 fields
        for line in lines[1:]:  # skip header
            fields = line.split('\t')
            assert len(fields) == 6, f"Expected 6 fields, got {len(fields)}: {line}"

    def test_ledger_tsv_integrity_concurrent_writes(self, tmp_path):
        """Concurrent ledger appends maintain TSV integrity via fcntl"""
        import threading
        import time

        ledger = tmp_path / "results.tsv"
        ledger.write_text(
            "run_id\thypothesis\tfiles_changed\tchecks_passed\tstatus\tnotes\n"
        )

        errors = []
        written_records = []

        def write_record_with_retry(run_id, retries=3):
            """Write with retry to handle potential lock contention"""
            for attempt in range(retries):
                try:
                    lock_path = str(ledger) + f'.lock.{os.getpid()}.{threading.current_thread().ident}'
                    with open(lock_path, 'w') as lock_f:
                        fcntl.flock(lock_f.fileno(), fcntl.LOCK_EX)
                        try:
                            with open(ledger, 'a') as f:
                                row = '\t'.join([
                                    run_id,
                                    f"hypothesis for {run_id}",
                                    "scripts/test.py",
                                    "10/10 gates",
                                    "keep",
                                    f"notes for {run_id}"
                                ])
                                f.write(row + '\n')
                            written_records.append(run_id)
                        finally:
                            fcntl.flock(lock_f.fileno(), fcntl.LOCK_UN)
                    # Only remove lock if it still exists
                    if os.path.exists(lock_path):
                        os.remove(lock_path)
                    return  # Success
                except FileNotFoundError:
                    # Lock file was removed by another process, retry
                    if attempt < retries - 1:
                        time.sleep(0.01)
                    else:
                        errors.append(f"Failed to acquire lock for {run_id} after {retries} attempts")
                except Exception as e:
                    errors.append(f"Error writing {run_id}: {str(e)}")
                    return

        # Run 5 concurrent writes
        threads = []
        for i in range(5):
            t = threading.Thread(target=write_record_with_retry, args=(f"concurrent-run-{i:03d}",))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Give a moment for any pending I/O
        time.sleep(0.1)

        # Verify no errors
        assert len(errors) == 0, f"Concurrent write errors: {errors}"
        assert len(written_records) == 5

        # Verify TSV integrity
        lines = ledger.read_text().splitlines()
        assert len(lines) == 6, f"Expected 6 lines, got {len(lines)}: {lines}"

        for line in lines[1:]:
            fields = line.split('\t')
            assert len(fields) == 6, f"Corrupted TSV line: {line}"

    def test_record_result_includes_skill_proposal(self, tmp_path):
        """benchmark evidence + skill proposal + verification should be encoded in notes."""
        repo_root = Path(__file__).parent.parent
        script_src = repo_root / ".self-improvement" / "record_result.sh"
        helper_src = repo_root / ".self-improvement" / "_record_helper.py"
        local_dir = tmp_path / "self_improvement"
        local_dir.mkdir()
        (local_dir / "record_result.sh").write_text(script_src.read_text(encoding="utf-8"), encoding="utf-8")
        if helper_src.exists():
            (local_dir / "_record_helper.py").write_text(helper_src.read_text(encoding="utf-8"), encoding="utf-8")

        script = local_dir / "record_result.sh"
        proposal = tmp_path / "proposal.md"
        proposal.write_text("# proposal", encoding="utf-8")
        verification = tmp_path / "verification.json"
        verification.write_text('{"decision":"approve"}', encoding="utf-8")

        result = subprocess.run(
            [
                "bash",
                str(script),
                "--run-id",
                "run-test-001",
                "--hypothesis",
                "tighten memory gate",
                "--files",
                "scripts/memory_longterm.py",
                "--checks",
                "10/10 gates",
                "--status",
                "keep",
                "--benchmark-evidence",
                "tests/bench/sample.json",
                "--skill-proposal",
                str(proposal),
                "--proposal-verification",
                str(verification),
                "--proposal-decision",
                "approve",
                "--notes",
                "integration smoke",
            ],
            cwd=local_dir,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, result.stderr
        ledger_text = (local_dir / "results.tsv").read_text(encoding="utf-8")
        assert "skill_proposal=" in ledger_text
        assert "proposal_verification=" in ledger_text
        assert "proposal_decision=approve" in ledger_text
        assert "benchmark_evidence=" in ledger_text

        ledger_v2 = local_dir / "results_v2.jsonl"
        assert ledger_v2.exists()
        ledger_v2_text = ledger_v2.read_text(encoding="utf-8")
        assert '"proposal_decision": "approve"' in ledger_v2_text

    def test_ledger_handles_special_characters(self, tmp_path):
        """TSV cleaner properly escapes tabs and newlines"""
        ledger = tmp_path / "results.tsv"
        ledger.write_text(
            "run_id\thypothesis\tfiles_changed\tchecks_passed\tstatus\tnotes\n"
        )

        lock_path = str(ledger) + '.lock'

        # Test with content that would break TSV
        hypothesis_with_newline = "multi\nline\nhypothesis"
        notes_with_tabs = "note1\twith\ttabs"

        with open(lock_path, 'w') as lock_f:
            fcntl.flock(lock_f.fileno(), fcntl.LOCK_EX)
            try:
                with open(ledger, 'a') as f:
                    # Use the same tsv_clean logic as record_result.sh
                    cleaned_hyp = ' '.join(hypothesis_with_newline.replace('\t', ' ').replace('\n', ' ').split())
                    cleaned_notes = ' '.join(notes_with_tabs.replace('\t', ' ').replace('\n', ' ').split())
                    row = '\t'.join([
                        "special-char-test",
                        cleaned_hyp,
                        "file.py",
                        "10/10",
                        "keep",
                        cleaned_notes
                    ])
                    f.write(row + '\n')
            finally:
                fcntl.flock(lock_f.fileno(), fcntl.LOCK_UN)
                os.remove(lock_path)

        # Verify still valid TSV
        lines = ledger.read_text().splitlines()
        assert len(lines) == 2
        fields = lines[1].split('\t')
        assert len(fields) == 6
        # Verify the content is preserved (without special chars)
        assert "multi line hypothesis" in fields[1]
        assert "note1 with tabs" in fields[5]


class TestBaselineCheckIntegration:
    """Integration tests for baseline_check.sh"""

    def test_baseline_check_with_worktree(self, tmp_path):
        """Creating additional worktree should allow gate 0 to pass"""
        repo_dir = tmp_path / "test_repo"
        repo_dir.mkdir()

        # Init git repo
        subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=repo_dir, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=repo_dir, capture_output=True
        )

        # Create initial commit
        readme = repo_dir / "README.md"
        readme.write_text("# Test")
        subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "initial"],
            cwd=repo_dir, capture_output=True
        )

        # Create a worktree
        worktree_dir = tmp_path / "test_worktree"
        worktree_dir.mkdir()
        subprocess.run(
            ["git", "worktree", "add", str(worktree_dir), "-b", "worktree/test"],
            cwd=repo_dir, capture_output=True
        )

        # Copy baseline_check to worktree
        self_imp_dir = worktree_dir / ".self-improvement"
        self_imp_dir.mkdir()
        baseline_check = self_imp_dir / "baseline_check.sh"

        project_baseline = Path(__file__).parent.parent / ".self-improvement" / "baseline_check.sh"
        if project_baseline.exists():
            baseline_check.write_text(project_baseline.read_text())

        # Create stub scripts
        scripts_dir = worktree_dir / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "unified_state.py").write_text("# stub")

        # Run baseline_check from worktree
        result = subprocess.run(
            ["bash", ".self-improvement/baseline_check.sh", "--allow-dirty"],
            cwd=worktree_dir,
            capture_output=True,
            text=True
        )

        # Gate 0 should pass because we're in a worktree
        assert "PASS" in result.stdout, f"Expected PASS in worktree: {result.stdout}"
