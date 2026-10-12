"""Bring up one build, seed it and run the load profiles against it.

Usage (Python with locust installed):
    python loadtest/run.py baseline --baseline-dir ../AITesting-baseline
    python loadtest/run.py current
    python loadtest/run.py current --stages smoke --keep-up
"""

import argparse
import os
import re
import subprocess
import sys
import threading
import time
import urllib.request
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
SERVICES = ["postgres", "redis", "migrate", "django"]


def target_config(name: str, baseline_dir: Path) -> dict:
    if name == "baseline":
        # Old compose: project name comes from the worktree directory, ports are fixed
        return {"cwd": baseline_dir, "compose": ["docker", "compose"], "port": 8000}
    return {
        "cwd": REPO,
        "compose": [
            "docker", "compose", "-p", "aitesting-loadtest",
            "-f", "docker-compose.yml", "-f", "loadtest/compose.override.yml",
        ],
        "port": 8001,
    }


def run(cmd: list[str], cwd: Path, **kwargs) -> subprocess.CompletedProcess:
    print("$", " ".join(cmd), flush=True)
    return subprocess.run(cmd, cwd=cwd, check=True, **kwargs)


def wait_healthy(host: str, timeout: int = 180) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{host}/health_check", timeout=5) as resp:
                if resp.status == 200:
                    return
        except Exception:
            pass
        time.sleep(2)
    raise RuntimeError(f"{host} is not healthy after {timeout}s")


def seed(cfg: dict) -> dict[str, str]:
    with open(HERE / "seed.py", "rb") as f:
        out = run(
            cfg["compose"] + ["exec", "-T", "django", "python", "manage.py", "shell"],
            cfg["cwd"], stdin=f, capture_output=True,
        ).stdout.decode()
    line = next(line for line in out.splitlines() if line.startswith("SEED:"))
    print(line)
    return dict(re.findall(r"(\w+)=(\S+)", line))


class DockerStatsSampler(threading.Thread):
    """Samples CPU/memory of the stack's containers every few seconds."""

    def __init__(self, project_filter: str, out: Path, interval: float = 5) -> None:
        super().__init__(daemon=True)
        self.project_filter, self.out, self.interval = project_filter, out, interval
        self.stop_event = threading.Event()

    def run(self) -> None:
        start = time.time()
        with open(self.out, "w", encoding="utf-8") as f:
            f.write("t,container,cpu_percent,mem_usage\n")
            while not self.stop_event.is_set():
                res = subprocess.run(
                    ["docker", "stats", "--no-stream", "--format",
                     "{{.Name}};{{.CPUPerc}};{{.MemUsage}}"],
                    capture_output=True, text=True,
                )
                t = round(time.time() - start, 1)
                for line in res.stdout.splitlines():
                    name, cpu, mem = line.split(";")
                    if self.project_filter in name and ("django" in name or "postgres" in name):
                        f.write(f"{t},{name},{cpu.rstrip('%')},{mem.split('/')[0].strip()}\n")
                f.flush()
                self.stop_event.wait(self.interval)


def locust(profile: str, host: str, env: dict, csv_prefix: Path | None) -> None:
    cmd = [sys.executable, "-m", "locust", "-f", str(HERE / "locustfile.py"),
           "--headless", "--host", host, "--only-summary"]
    if csv_prefix:
        cmd += ["--csv", str(csv_prefix), "--csv-full-history", "--html", f"{csv_prefix}.html"]
    # Locust exits with 1 when any request failed; failures are part of the result
    print(f"--- locust {profile} -> {host}", flush=True)
    subprocess.run(cmd, cwd=HERE, env={**env, "LT_PROFILE": profile})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", choices=["baseline", "current"])
    parser.add_argument("--baseline-dir", default=str(REPO.parent / "AITesting-baseline"))
    parser.add_argument("--stages", default="load,stress,spike")
    parser.add_argument("--keep-up", action="store_true", help="do not stop the stack at the end")
    parser.add_argument("--compose-extra", help="extra compose file for an experiment (current only)")
    parser.add_argument("--results-name", help="results folder name (default: target name)")
    args = parser.parse_args()

    cfg = target_config(args.target, Path(args.baseline_dir).resolve())
    if args.compose_extra:
        cfg["compose"] += ["-f", args.compose_extra]
    host = f"http://localhost:{cfg['port']}"
    results = HERE / "results" / (args.results_name or args.target)
    results.mkdir(parents=True, exist_ok=True)

    run(cfg["compose"] + ["up", "-d", "--build"] + SERVICES, cfg["cwd"])
    wait_healthy(host)
    info = seed(cfg)
    (results / "seed.txt").write_text(str(info), encoding="utf-8")

    env = {
        **os.environ,
        "LT_ITEM_MAX": info["item_ids"].split("..")[1],
        "LT_CATEGORY_MAX": info["category_ids"].split("..")[1],
    }
    project = "aitesting-loadtest" if args.target == "current" else Path(cfg["cwd"]).name.lower()
    try:
        for stage in args.stages.split(","):
            if stage != "smoke":
                locust("warmup", host, env, None)
            sampler = DockerStatsSampler(project, results / f"{stage}_docker.csv")
            sampler.start()
            started = datetime.now().isoformat(timespec="seconds")
            locust(stage, host, env, results / stage)
            sampler.stop_event.set()
            sampler.join()
            print(f"stage {stage} started {started}, finished {datetime.now():%H:%M:%S}")
    finally:
        if not args.keep_up:
            run(cfg["compose"] + ["stop"], cfg["cwd"])


if __name__ == "__main__":
    main()
