"""Shared fixtures and the requirements-traceability hook.

Every test is tagged with @pytest.mark.req("ID"). At the end of a run this hook
writes a traceability matrix that links each requirement to its tests and
results, stamped with the git commit and config hash (config control evidence).

Each test also gets a verification level (Unit / System / Bench), from the file
it lives in or an explicit @pytest.mark.level("...").

Run for record vs partial run: only a full, unfiltered run writes reports/.
Any partial run (one file, one test, -k, -m, stopped early) writes to
reports/dev/ instead, labeled "not for record", so it can never overwrite the
official record.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import os
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


# ------------------------------------------------------------ live bench
def pytest_addoption(parser):
    g = parser.getgroup("live bench (Raspberry Pi)")
    g.addoption("--live", action="store_true",
                help="drive the real Raspberry Pi: fresh capture with an automated link drop")
    g.addoption("--pi", default=os.environ.get("PI_SSH", "taylor@dronepi.local"),
                help="SSH target for controlling the Pi (Wi-Fi path)")
    g.addoption("--data-host", default=os.environ.get("BENCH_DATA_HOST", "192.168.2.2"),
                help="this PC's IP on the direct Ethernet cable (where the Pi sends words)")
    g.addoption("--drop-at", type=float, default=15.0, help="seconds into the run to drop the link")
    g.addoption("--drop-for", type=float, default=5.0, help="seconds the link stays down")


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


# ------------------------------------------------------ verification level
# Unit:   one component tested alone (encoder, receiver, voter, actuator model).
# System: several components working together in closed loop.
# Bench:  real hardware data (Raspberry Pi over a real Ethernet cable).
LEVEL_BY_FILE = {
    "test_part_b_receiver.py": "Unit",
    "test_part_b_voter.py": "Unit",
    "test_part_a_actuator.py": "Unit",
    "test_model_bench_actuator.py": "Unit",
    "test_part_b_system.py": "System",
    "test_part_c_actuator_faults.py": "System",
    "test_bench_link.py": "Bench",
}
LEVEL_ORDER = ["Unit", "System", "Bench"]
_deselected = 0


def pytest_configure(config):
    config.addinivalue_line("markers", "level(name): verification level, Unit / System / Bench")


def _level_of(item) -> str:
    m = item.get_closest_marker("level")
    if m:
        return m.args[0]
    return LEVEL_BY_FILE.get(Path(str(item.fspath)).name, "Unit")


def pytest_deselected(items):
    global _deselected
    _deselected += len(items)


# ------------------------------------------------------- traceability hook
def _git_commit() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                             capture_output=True, text=True, timeout=5)
        commit = out.stdout.strip() or "no-git"
        # reports/ is the output of a run, so it doesn't count as a code change
        dirty = subprocess.run(["git", "status", "--porcelain", "--", ".", ":!reports"], cwd=ROOT,
                               capture_output=True, text=True, timeout=5).stdout.strip()
        return commit + ("-dirty" if dirty else "")
    except Exception:
        return "no-git"


def _run_type(session, exitstatus) -> tuple[bool, str]:
    """Full run = every test in tests/, no filter, not stopped early."""
    cfg = session.config
    here = Path(cfg.invocation_params.dir)
    args = [(here / a.split("::")[0]).resolve() for a in cfg.args] or [ROOT]
    whole_suite = all(a in (ROOT, ROOT / "tests") for a in args) and "::" not in " ".join(cfg.args)
    filtered = bool(cfg.getoption("keyword") or cfg.getoption("markexpr")
                    or cfg.getoption("lf", False) or cfg.getoption("ignore", None)
                    or cfg.getoption("ignore_glob", None) or cfg.getoption("deselect", None)
                    or _deselected or session.testsfailed and cfg.getoption("continue_on_collection_errors", False))
    stopped = exitstatus == pytest.ExitCode.INTERRUPTED or len(_results) < session.testscollected
    full = whole_suite and not filtered and not stopped
    return full, ("FULL RUN" if full else "STOPPED EARLY" if stopped else "PARTIAL RUN")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    rep.req_ids = [m.args[0] for m in item.iter_markers("req")]
    rep.level = _level_of(item)


def pytest_runtest_logreport(report):
    if report.when == "call" or (report.when == "setup" and report.outcome != "passed"):
        if hasattr(report, "wasxfail"):
            status = "xfail" if report.skipped else "xpass"
        else:
            status = report.outcome
        _results.append({
            "test": report.nodeid,
            "reqs": getattr(report, "req_ids", []),
            "level": getattr(report, "level", ""),
            "status": status,
            "duration_s": round(report.duration, 3),
            "measured": dict(report.user_properties),
            "note": getattr(report, "wasxfail", ""),
        })


def _test_names(tests: list[dict]) -> str:
    """test_fault_matrix x24, test_r1_bad_parity_rejected, ... (parametrized cases grouped)."""
    counts: dict[str, int] = {}
    for t in tests:
        fn = t["test"].split("::", 1)[-1].split("[", 1)[0]
        counts[fn] = counts.get(fn, 0) + 1
    return ", ".join(f"`{fn}` x{n}" if n > 1 else f"`{fn}`" for fn, n in counts.items())


def _levels(tests: list[dict]) -> str:
    found = {t["level"] for t in tests if t["level"]}
    return " + ".join(lv for lv in LEVEL_ORDER if lv in found)


def pytest_sessionfinish(session, exitstatus):
    if not _results:
        return
    full, run_type = _run_type(session, exitstatus)
    out_dir = REPORT_DIR if full else REPORT_DIR / "dev"
    out_dir.mkdir(parents=True, exist_ok=True)
    cfg = load_config()
    reqs = yaml.safe_load((ROOT / "requirements" / "requirements.yaml").read_text())
    commit = _git_commit()
    if not full and run_type == "STOPPED EARLY":
        run_label = (f"PARTIAL RUN, stopped early ({len(_results)} of {session.testscollected} "
                     "tests run), not for record")
    elif not full:
        n = len(_results)
        run_label = f"PARTIAL RUN ({n} test{'s' if n != 1 else ''} selected), not for record"
    elif commit.endswith("-dirty"):
        run_label = (f"FULL RUN ({len(_results)} of {session.testscollected} tests) on uncommitted "
                     "changes, not for record: commit first, then run")
    else:
        run_label = f"FULL RUN ({len(_results)} of {session.testscollected} tests), record"
    meta = {
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "run_type": run_type,
        "run_label": run_label,
        "git_commit": commit,
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
        elif statuses == {"skipped"}:
            verdict = "NOT RUN"
        elif statuses & {"failed", "xpass"}:
            verdict = "FAIL"
        elif "xfail" in statuses:
            verdict = "OPEN DEFECT"
        else:
            verdict = "PASS"
        rows.append({"req": rid, "stage": info["stage"], "text": info["text"],
                     "levels": _levels(tests),
                     "tests": len(tests),
                     "test_names": _test_names(tests).replace("`", ""),
                     "passed": sum(t["status"] == "passed" for t in tests),
                     "verdict": verdict,
                     "notes": "; ".join(sorted({t["note"] for t in tests if t["note"]}))})

    traced = sum(r["tests"] > 0 and r["verdict"] != "NOT RUN" for r in rows)
    counts = defaultdict(int)
    for r in _results:
        counts[r["status"]] += 1
    by_level = defaultdict(int)
    for r in _results:
        by_level[r["level"]] += 1
    summary = {**meta,
               "requirements_total": len(rows),
               "requirements_traced": traced,
               "requirements_traced_pct": round(100.0 * traced / len(rows), 1),
               "tests_total": len(_results),
               "tests_by_status": dict(counts),
               "tests_by_level": {lv: by_level[lv] for lv in LEVEL_ORDER if by_level[lv]},
               "untagged_tests": [r["test"] for r in _results if not r["reqs"]]}

    (out_dir / "test_summary.json").write_text(
        json.dumps({"summary": summary, "requirements": rows, "results": _results},
                   indent=2, default=str))

    with open(out_dir / "traceability.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    level_txt = ", ".join(f"{lv} {n}" for lv, n in summary["tests_by_level"].items())
    lines = [
        "# Requirements Traceability Matrix",
        "",
        f"- **Run: {run_label}**",
        f"- Generated: {meta['generated_utc']}",
        f"- Git commit: `{meta['git_commit']}`",
        f"- Config: `{meta['config_file']}` (sha256 `{meta['config_sha256_12']}`)",
        f"- ICD: {meta['airframe_icd']}",
        f"- Load conditions: {meta['load_conditions']}",
        f"- Requirements traced: {traced}/{len(rows)} ({summary['requirements_traced_pct']}%)",
        f"- Tests: {len(_results)} ({', '.join(f'{k} {v}' for k, v in sorted(counts.items()))})",
        f"- Tests by level: {level_txt}",
        f"- Suite runtime: {meta['suite_runtime_s']} s",
        "",
        "Levels: **Unit** = one component alone; **System** = components together in closed "
        "loop; **Bench** = real hardware data (Raspberry Pi over a real Ethernet cable). "
        f"Written procedures for every test: [docs/procedures/]({'../' if full else '../../'}docs/procedures/README.md).",
        "",
        "| Req | Stage | Requirement | Level | Tests | Test names | Passed | Verdict | Notes |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r, tests in ((r, by_req.get(r["req"], [])) for r in rows):
        lines.append(f"| {r['req']} | {r['stage']} | {r['text']} | {r['levels']} | {r['tests']} | "
                     f"{_test_names(tests)} | {r['passed']} | **{r['verdict']}** | {r['notes']} |")
    lines += ["", "## Test results", "", "| Test | Reqs | Level | Status | Measured |",
              "| --- | --- | --- | --- | --- |"]
    for r in _results:
        meas = ", ".join(f"{k}={v}" for k, v in r["measured"].items())
        lines.append(f"| `{r['test'].split('::', 1)[-1]}` | {', '.join(r['reqs'])} | "
                     f"{r['level']} | {r['status']} | {meas} |")
    (out_dir / "traceability.md").write_text("\n".join(lines) + "\n")
