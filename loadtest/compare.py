"""Compare Locust results of the baseline and the current build.

Reads loadtest/results/{baseline,current}/<stage>_stats*.csv and writes
loadtest/results/summary.md and loadtest/results/summary.json.
"""

import csv
import json
import statistics
from datetime import datetime
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
TARGETS = ("baseline", "current")
EXPERIMENT = "current-connage0"
# Follow-up build (gunicorn + Redis cache), compared against "current"
NEXT = "gunicorn-cache"
STAGES = ("load", "stress", "spike")
METRICS = ("rps", "avg", "p50", "p95", "p99", "max", "fail_pct")
LOWER_IS_BETTER = {"avg", "p50", "p95", "p99", "max", "fail_pct"}
# Degradation threshold for the stress steps
P95_LIMIT_MS = 2000
FAIL_LIMIT_PCT = 1.0


def num(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def read_stats(target: str, stage: str) -> dict[str, dict[str, float]]:
    path = RESULTS / target / f"{stage}_stats.csv"
    if not path.exists():
        return {}
    rows = {}
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            count = num(row["Request Count"])
            rows[row["Name"]] = {
                "count": count,
                "rps": num(row["Requests/s"]),
                "avg": num(row["Average Response Time"]),
                "p50": num(row["50%"]),
                "p95": num(row["95%"]),
                "p99": num(row["99%"]),
                "max": num(row["Max Response Time"]),
                "fail_pct": 100 * num(row["Failure Count"]) / count if count else 0.0,
            }
    return rows


def read_history(target: str, stage: str) -> list[dict[str, float]]:
    """Per-second aggregated rows (time from start, users, rps, p95, failures/s)."""
    path = RESULTS / target / f"{stage}_stats_history.csv"
    if not path.exists():
        return []
    rows = []
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["Name"] != "Aggregated":
                continue
            rows.append(
                {
                    "ts": num(row["Timestamp"]),
                    "users": num(row["User Count"]),
                    "rps": num(row["Requests/s"]),
                    "fps": num(row["Failures/s"]),
                    "p50": num(row["50%"]),
                    "p95": num(row["95%"]),
                }
            )
    if rows:
        start = rows[0]["ts"]
        for row in rows:
            row["t"] = row.pop("ts") - start
    return rows


def stress_steps(history: list[dict[str, float]], settle: int = 15) -> list[dict[str, float]]:
    """Mean rps / median p95 per user level, skipping the first seconds after a ramp."""
    steps: dict[int, list[dict[str, float]]] = {}
    seen_at: dict[int, float] = {}
    for row in history:
        users = int(row["users"])
        seen_at.setdefault(users, row["t"])
        if row["t"] - seen_at[users] >= settle:
            steps.setdefault(users, []).append(row)
    result = []
    for users, rows in sorted(steps.items()):
        rps = statistics.mean(r["rps"] for r in rows)
        fps = statistics.mean(r["fps"] for r in rows)
        result.append(
            {
                "users": users,
                "rps": round(rps, 1),
                # failed requests return fast, so only successful ones count as useful throughput
                "ok_rps": round(rps - fps, 1),
                "p50": statistics.median(r["p50"] for r in rows),
                "p95": statistics.median(r["p95"] for r in rows),
                "fail_pct": round(100 * fps / rps, 2) if rps else 0.0,
            }
        )
    return result


def degradation_point(steps: list[dict[str, float]]) -> int | None:
    for step in steps:
        if step["p95"] > P95_LIMIT_MS or step["fail_pct"] > FAIL_LIMIT_PCT:
            return int(step["users"])
    return None


def change(metric: str, base: float, cur: float) -> dict[str, float | None]:
    if not base:
        return {"delta_pct": None, "factor": None}
    delta = 100 * (cur - base) / base
    if metric in LOWER_IS_BETTER:
        factor = base / cur if cur else None
    else:
        factor = cur / base
    return {"delta_pct": round(delta, 1), "factor": round(factor, 2) if factor else None}


def error_breakdown(target: str, stage: str) -> dict[str, int]:
    """Server errors vs 401s caused by a failed login (the user then has no token)."""
    path = RESULTS / target / f"{stage}_failures.csv"
    counts = {"server_500": 0, "auth_401": 0, "connection": 0, "other": 0}
    if not path.exists():
        return counts
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            error, n = row["Error"], int(row["Occurrences"])
            if "500 Server Error" in error:
                counts["server_500"] += n
            elif "401 Client Error" in error:
                counts["auth_401"] += n
            elif "Disconnected" in error or "ConnectionError" in error or "Timeout" in error:
                counts["connection"] += n
            else:
                counts["other"] += n
    return counts


def docker_usage(target: str, stage: str) -> dict[str, dict[str, float]]:
    path = RESULTS / target / f"{stage}_docker.csv"
    if not path.exists():
        return {}
    usage: dict[str, list[float]] = {}
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            kind = "django" if "django" in row["container"] else "postgres"
            usage.setdefault(kind, []).append(num(row["cpu_percent"]))
    return {
        kind: {"cpu_avg": round(statistics.mean(v), 1), "cpu_max": round(max(v), 1)}
        for kind, v in usage.items()
        if v
    }


def fmt(value: float | None, suffix: str = "") -> str:
    if value is None:
        return "—"
    return f"{value:,.1f}{suffix}".replace(",", " ")


def next_build_lines(stage: str) -> list[str]:
    """current → NEXT tables for one stage (empty if either run is missing)"""
    cur, nxt = read_stats("current", stage), read_stats(NEXT, stage)
    if not cur or not nxt:
        return []
    lines = [
        f"### {stage}",
        "",
        "| Endpoint | RPS cur → new | avg ms | p50 ms | p95 ms | p99 ms | errors % | p95 speed-up |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for name in sorted(set(cur) & set(nxt), key=lambda n: (n == "Aggregated", n)):
        c, n = cur[name], nxt[name]
        cells = [f"{fmt(c[m])} → {fmt(n[m])}" for m in METRICS if m != "max"]
        factor = change("p95", c["p95"], n["p95"])["factor"]
        lines.append(f"| {name} | " + " | ".join(cells) + f" | ×{fmt(factor)} |")
    lines.append("")
    if stage == "stress":
        steps_c = {s["users"]: s for s in stress_steps(read_history("current", stage))}
        steps_n = {s["users"]: s for s in stress_steps(read_history(NEXT, stage))}
        lines += [
            "| Users | successful RPS cur → new | p95 ms cur → new | errors % cur → new |",
            "|---|---|---|---|",
        ]
        for users in sorted(set(steps_c) & set(steps_n)):
            sc, sn = steps_c[users], steps_n[users]
            lines.append(
                f"| {users} | {fmt(sc['ok_rps'])} → {fmt(sn['ok_rps'])} "
                f"| {fmt(sc['p95'])} → {fmt(sn['p95'])} "
                f"| {fmt(sc['fail_pct'])} → {fmt(sn['fail_pct'])} |"
            )
        deg_c = degradation_point(list(steps_c.values()))
        deg_n = degradation_point(list(steps_n.values()))
        lines += [
            "",
            f"Degradation (p95 > {P95_LIMIT_MS} ms or errors > {FAIL_LIMIT_PCT}%): "
            f"current at {deg_c or 'not reached'}{' users' if deg_c else ''}, "
            f"{NEXT} {f'at {deg_n} users' if deg_n else 'not reached (up to 200 users)'}",
            "",
        ]
    return lines


def main() -> None:
    summary: dict = {"stages": {}}
    lines = ["# Load test: baseline (c3e1a7b) vs current", ""]

    for stage in STAGES:
        base, cur = read_stats("baseline", stage), read_stats("current", stage)
        if not base or not cur:
            continue
        endpoints = []
        for name in sorted(set(base) | set(cur), key=lambda n: (n == "Aggregated", n)):
            b, c = base.get(name), cur.get(name)
            if not b or not c:
                continue
            endpoints.append(
                {
                    "name": name,
                    "baseline": b,
                    "current": c,
                    "change": {m: change(m, b[m], c[m]) for m in METRICS},
                }
            )
        stage_data = {
            "endpoints": endpoints,
            "history": {t: read_history(t, stage) for t in TARGETS},
            "docker": {t: docker_usage(t, stage) for t in TARGETS},
            "errors": {t: error_breakdown(t, stage) for t in TARGETS},
        }
        if stage == "stress":
            stage_data["steps"] = {t: stress_steps(stage_data["history"][t]) for t in TARGETS}
            stage_data["degradation_users"] = {
                t: degradation_point(stage_data["steps"][t]) for t in TARGETS
            }
        summary["stages"][stage] = stage_data

        lines += [f"## {stage}", ""]
        lines += [
            "| Endpoint | RPS base → cur | avg ms | p50 ms | p95 ms | p99 ms | errors % "
            "| p95 speed-up |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for e in endpoints:
            b, c, ch = e["baseline"], e["current"], e["change"]
            cells = [f"{fmt(b[m])} → {fmt(c[m])}" for m in METRICS if m != "max"]
            lines.append(
                f"| {e['name']} | " + " | ".join(cells) + f" | ×{fmt(ch['p95']['factor'])} |"
            )
        lines.append("")
        if stage == "stress":
            lines += ["| Users | successful RPS base → cur | p95 ms base → cur "
                      "| errors % base → cur |",
                      "|---|---|---|---|"]
            steps_b = {s["users"]: s for s in stage_data["steps"]["baseline"]}
            steps_c = {s["users"]: s for s in stage_data["steps"]["current"]}
            for users in sorted(set(steps_b) & set(steps_c)):
                sb, sc = steps_b[users], steps_c[users]
                lines.append(
                    f"| {users} | {fmt(sb['ok_rps'])} → {fmt(sc['ok_rps'])} "
                    f"| {fmt(sb['p95'])} → {fmt(sc['p95'])} "
                    f"| {fmt(sb['fail_pct'])} → {fmt(sc['fail_pct'])} |"
                )
            deg = stage_data["degradation_users"]
            lines += [
                "",
                f"Degradation (p95 > {P95_LIMIT_MS} ms or errors > {FAIL_LIMIT_PCT}%): "
                f"baseline at {deg['baseline'] or 'not reached'} users, "
                f"current at {deg['current'] or 'not reached'} users",
                "",
            ]

    # Experiment: current build with CONN_MAX_AGE=0 (stress only)
    if (RESULTS / EXPERIMENT / "stress_stats.csv").exists():
        steps = stress_steps(read_history(EXPERIMENT, "stress"))
        summary["experiment"] = {
            "name": EXPERIMENT,
            "steps": steps,
            "aggregated": read_stats(EXPERIMENT, "stress").get("Aggregated"),
            "errors": error_breakdown(EXPERIMENT, "stress"),
        }
        lines += [f"## experiment: {EXPERIMENT} (stress)", "",
                  "| Users | successful RPS | p95 ms | errors % |", "|---|---|---|---|"]
        lines += [f"| {x['users']} | {fmt(x['ok_rps'])} | {fmt(x['p95'])} | {fmt(x['fail_pct'])} |"
                  for x in steps]
        lines.append("")

    next_lines = [line for stage in STAGES for line in next_build_lines(stage)]
    if next_lines:
        lines += [
            f"## next: current → {NEXT}",
            "",
            "Both runs on the same data and scenario. current: runserver, DEBUG=True. "
            f"{NEXT}: gunicorn (4 workers × 2 threads), DEBUG=False, Redis cache for the category "
            "tree and the item list.",
            "",
        ] + next_lines

    (RESULTS / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    (RESULTS / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")

    # HTML report: data + hand-written conclusions (results/notes.json: lead, why[])
    notes_path = RESULTS / "notes.json"
    notes = json.loads(notes_path.read_text(encoding="utf-8")) if notes_path.exists() else {}
    report = {
        **summary,
        "generated": datetime.now().strftime("%d.%m.%Y"),
        "lead": notes.get("lead", ""),
        "why": notes.get("why", []),
        "exp_lead": notes.get("exp_lead", ""),
    }
    template = (HERE / "report_template.html").read_text(encoding="utf-8")
    payload = json.dumps(report, ensure_ascii=False).replace("</", "<\\/")
    (RESULTS / "report.html").write_text(template.replace("__DATA__", payload), encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]  # cp1251 console
    print("\n".join(lines))


if __name__ == "__main__":
    main()
