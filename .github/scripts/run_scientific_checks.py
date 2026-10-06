"""Run reviewed finite checks in scratch space; preserve each command's raw output.

The artifact is the repository root. The Ubuntu workflow supplies the whole-run
deadline and process limits; this driver additionally bounds each command. No
source optimizer, external scan, paid service, or manuscript build is invoked.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
TESTS = (
    "pilot_algebra", "test_suite", "pilot_dominance", "test_dominance",
    "test_context_hardness", "test_frontier", "test_actual_context_gap",
    "test_order_invariance", "test_public_inputs", "test_online_frontier_peak",
    "test_control_oracle", "test_milp_oracle", "test_boundary_inputs",
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    out = Path(args.out).resolve()
    if out == ROOT or out.is_relative_to(ROOT):
        parser.error("raw output must be outside the artifact checkout")
    out.mkdir(parents=True, exist_ok=True)
    scratch = out / "working"
    if scratch.exists():
        parser.error("scratch path already exists; refusing stale test output")
    shutil.copytree(ROOT, scratch, ignore=shutil.ignore_patterns(
        ".git", "__pycache__", "*.pyc", "*.pyo", ".pytest_cache", ".venv"))
    logs = out / "logs"
    logs.mkdir()
    env = dict(os.environ, PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1",
               OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")
    started = time.perf_counter()
    attempts = []
    (out / "environment.json").write_text(json.dumps({
        "python": sys.version, "platform": platform.platform(),
        "source_root": str(ROOT), "scratch_root": str(scratch),
        "scope": "finite exact checks and retained-input reproduction; not a proof-assistant result",
    }, indent=2) + "\n", encoding="utf-8")
    commands = [(["tests/" + test + ".py"], 180) for test in TESTS]
    commands += [
        (["validate_dominance.py", "results/dominance-campaign"], 180),
        (["validate_results.py", "results/campaign"], 180),
        (["validate_results.py", "results/null-baseline", "--methods", "constant_raw"], 180),
        (["validate_public_extension.py", "results/public-portfolio-extension"], 180),
        (["validate_public_matched_control.py", "results/public-portfolio-matched-control"], 180),
        (["audit_artifact.py"], 60),
        (["run_dominance.py", "--out", str(out / "fresh-dominance")], 300),
        (["validate_dominance.py", str(out / "fresh-dominance")], 180),
        (["compare_dominance.py", "results/dominance-campaign", str(out / "fresh-dominance")], 60),
    ]
    try:
        for index, (arguments, limit) in enumerate(commands):
            command = [sys.executable, "-B", *arguments]
            begin = time.perf_counter()
            row = {"command": command, "timeout_seconds": limit}
            with (logs / f"{index:02d}.stdout.log").open("wb") as stdout, \
                 (logs / f"{index:02d}.stderr.log").open("wb") as stderr:
                try:
                    result = subprocess.run(command, cwd=scratch, env=env,
                                            stdout=stdout, stderr=stderr, timeout=limit)
                    row.update(status="passed" if result.returncode == 0 else "failed",
                               exit_code=result.returncode)
                except subprocess.TimeoutExpired:
                    row.update(status="timeout", exit_code=None)
            row["wall_seconds"] = time.perf_counter() - begin
            attempts.append(row)
            (out / "commands.json").write_text(json.dumps(attempts, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(row), flush=True)
            if row["status"] != "passed":
                raise SystemExit(1)
    finally:
        (out / "elapsed.json").write_text(json.dumps({
            "wall_seconds": time.perf_counter() - started,
            "commands_completed": len(attempts),
            "all_listed_commands_completed": len(attempts) == len(commands),
        }, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
