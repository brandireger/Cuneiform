#!/usr/bin/env python3
"""
run_d15_grid.py -- P4 D15 ablation grid driver.

Runs the three positive-mix presets sequentially (single GPU, only one
can train at a time). Each is independently resumable via
20_biencoder.py --resume, so killing/restarting this driver script
loses nothing -- it just re-detects which mixes already finished
(dev_gates_final.json present) and skips them, then resumes the
in-progress one from its own checkpoint.

Launched as a detached Windows Scheduled Task (same rationale as
19_pretrain.py's D14 run): this is a multi-hour unattended job that
must survive Claude Code session teardown.
"""
import json
import subprocess
import sys
from pathlib import Path

PYTHON = sys.executable
MIXES = ["balanced", "real_only", "synthetic_only"]
TAG = "base"


def run_dir_for(mix):
    return Path("runs") / f"biencoder_{TAG}_{mix}"


def main():
    for mix in MIXES:
        rd = run_dir_for(mix)
        final_path = rd / "dev_gates_final.json"
        if final_path.exists():
            print(f"[{mix}] already complete ({final_path}), skipping.", flush=True)
            continue

        resume_flag = ["--resume"] if (rd / "checkpoint.pt").exists() else []
        cmd = [PYTHON, "scripts/20_biencoder.py", "--config", "configs/biencoder_config.json",
               "--tag", TAG, "--mix", mix] + resume_flag
        print(f"[{mix}] launching: {' '.join(cmd)}", flush=True)
        result = subprocess.run(cmd)
        if result.returncode != 0:
            print(f"[{mix}] FAILED with exit code {result.returncode}. Stopping grid.", flush=True)
            sys.exit(result.returncode)
        print(f"[{mix}] done.", flush=True)

    print("D15 ablation grid complete: all three mixes finished.", flush=True)


if __name__ == "__main__":
    main()
