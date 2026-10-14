"""Shared fixtures and the requirements-traceability hook.

Every test is tagged with @pytest.mark.req("ID"). At the end of a run this hook
writes a traceability matrix that links each requirement to its tests and
results, stamped with the git commit and config hash (config control evidence).
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import platform
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sil.sim import load_config  # noqa: E402

REPORT_DIR = ROOT / "reports"
_results: list[dict] = []
_t0 = time.time()


# ---------------------------------------------------------------- fixtures
@pytest.fixture(scope="session")
def cfg():
    """Baseline SIL configuration, loaded fresh from version control."""
    return load_config()


@pytest.fixture
def fresh_cfg():
    """A private copy a test may modify (e.g. to verify a corrective action)."""
    return load_config()


def _load_ids():
    return list(load_config()["load_conditions"].keys())


@pytest.fixture(params=_load_ids())
def load_condition(request, cfg):
    """Every test that takes this fixture runs once per load condition."""
    name = request.param
    return name, cfg["load_conditions"][name]


# ------------------------------------------------------- traceability hook
def _git_commit() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                             capture_output=True, text=True, timeout=5)
        commit = out.stdout.strip() or "no-git"
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                               capture_output=True, text=True, timeout=5).stdout.strip()
        return commit + ("-dirty" if dirty else "")
    except Exception:
        return "no-git"


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    rep.req_ids = [m.args[0] for m in item.iter_markers("req")]


def pytest_runtest_logreport(report):
    if report.when == "call" or (report.when == "setup" and report.outcome != "passed"):
        if hasattr(report, "wasxfail"):
            status = "xfail" if report.skipped else "xpass"
        else:
            status = report.outcome
        _results.append({
            "test": report.nodeid,
            "reqs": getattr(report, "req_ids", []),
            "status": status,
            "duration_s": round(report.duration, 3),
            "measured": dict(report.user_properties),
            "note": getattr(report, "wasxfail", ""),
        })


def pytest_sessionfinish(session, exitstatus):
    if not _results:
        return
    REPORT_DIR.mkdir(exist_ok=True)
    cfg = load_config()
    reqs = yaml.safe_load((ROOT / "requirements" / "requirements.yaml").read_text())
    meta = {
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "git_commit": _git_commit(),
        "config_file": "config/sil.yaml",
        "config_sha256_12": cfg["_hash"],
        "airframe_icd": cfg["icd"]["airframe"],
        "load_conditions": cfg["load_conditions"],
        "python": platform.python_version(),
        "suite_runtime_s": round(time.time() - _t0, 1),
    }

    by_req: dict[str, list[dict]] = defaultdict(list)
    for r in _results:
        for rid in r["reqs"]:
            by_req[rid].append(r)

    rows = []
    for rid, info in reqs.items():
        tests = by_req.get(rid, [])
        statuses = {t["status"] for t in tests}
        if not tests:
            verdict = "NOT TESTED"
        elif statuses & {"failed", "xpass"}:
            verdict = "FAIL"
        elif "xfail" in statuses:
            verdict = "OPEN DEFECT"
        else:
            verdict = "PASS"
        rows.append({"req": rid, "stage": info["stage"], "text": info["text"],
                     "tests": len(tests),
                     "passed": sum(t["status"] == "passed" for t in tests),
                     "verdict": verdict,
                     "notes": "; ".join(sorted({t["note"] for t in tests if t["note"]}))})

    traced = sum(r["tests"] > 0 for r in rows)
    counts = defaultdict(int)
    for r in _results:
        counts[r["status"]] += 1
    summary = {**meta,
               "requirements_total": len(rows),
               "requirements_traced": traced,
               "requirements_traced_pct": round(100.0 * traced / len(rows), 1),
               "tests_total": len(_results),
               "tests_by_status": dict(counts),
               "untagged_tests": [r["test"] for r in _results if not r["reqs"]]}

    (REPORT_DIR / "test_summary.json").write_text(
        json.dumps({"summary": summary, "requirements": rows, "results": _results},
                   indent=2, default=str))

    with open(REPORT_DIR / "traceability.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    lines = [
        "# Requirements Traceability Matrix",
        "",
        f"- Generated: {meta['generated_utc']}",
        f"- Git commit: `{meta['git_commit']}`",
        f"- Config: `{meta['config_file']}` (sha256 `{meta['config_sha256_12']}`)",
        f"- ICD: {meta['airframe_icd']}",
        f"- Load conditions: {meta['load_conditions']}",
        f"- Requirements traced: {traced}/{len(rows)} ({summary['requirements_traced_pct']}%)",
        f"- Tests: {len(_results)} ({', '.join(f'{k} {v}' for k, v in sorted(counts.items()))})",
        f"- Suite runtime: {meta['suite_runtime_s']} s",
        "",
        "| Req | Stage | Requirement | Tests | Passed | Verdict | Notes |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in rows:
        lines.append(f"| {r['req']} | {r['stage']} | {r['text']} | {r['tests']} | "
                     f"{r['passed']} | **{r['verdict']}** | {r['notes']} |")
    lines += ["", "## Test results", "", "| Test | Reqs | Status | Measured |",
              "| --- | --- | --- | --- |"]
    for r in _results:
        meas = ", ".join(f"{k}={v}" for k, v in r["measured"].items())
        lines.append(f"| `{r['test'].split('::', 1)[-1]}` | {', '.join(r['reqs'])} | "
                     f"{r['status']} | {meas} |")
    (REPORT_DIR / "traceability.md").write_text("\n".join(lines) + "\n")
