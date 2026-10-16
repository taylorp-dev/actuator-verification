"""Bench link (L1): channel A from a real Raspberry Pi over a real Ethernet cable.

Two ways to feed these tests:

  python -m pytest tests/test_bench_link.py            replay the recordings in bench_data/
  python -m pytest tests/test_bench_link.py --live     drive the real Pi now

--live: pytest logs in to the Pi (SSH over Wi-Fi), starts the channel A sender,
records live over the Ethernet cable, and halfway through takes the Pi's
Ethernet port down for a few seconds and back up (automated cable pull). The
fresh recording is saved to bench_data/ (so CI replays the latest live run) and
the same tests below run on it.

    healthy.csv     part of the run before the link drop
    cable_pull.csv  the whole run, including the drop and recovery

If no recording exists and --live isn't given, tests are skipped (verdict
NOT RUN), never passed. ARINC 429 is software-encoded; the physical layer is
Ethernet.
"""

from __future__ import annotations

import datetime as dt
import os
import platform
from pathlib import Path

import numpy as np
import pytest

from sil.arinc429 import SSM, decode_bnr
from sil.bench import PiRemote, capture_udp
from sil.link import ReplayChannel, label_lookup, label_of, read_capture, write_capture
from sil.receiver import Receiver
from sil.sim import label_defs, run_scenario
from sil.voter import Mode

ROOT = Path(__file__).resolve().parent.parent
BENCH = Path(os.environ.get("BENCH_DATA_DIR", ROOT / "bench_data"))
TRUE_PITCH = -2.0          # what tools/pi_channel_a.py sends by default
PULL_MIN_GAP_S = 0.5       # a gap this long in cable_pull.csv is the pull
REPLAY_MAX_S = 30.0        # cap closed-loop replay length to keep the suite fast


def run_live(cfg, opt) -> dict:
    """Automated live run against the real Pi. Returns {name: (rows, meta)}."""
    labels = label_defs(cfg)
    pi = PiRemote(target=opt.getoption("--pi"), data_host=opt.getoption("--data-host"))
    drop_at, drop_for = opt.getoption("--drop-at"), opt.getoption("--drop-for")
    record_s = drop_at + drop_for + 12.0
    pi.check_ready()
    pi_commit = pi.update_code()
    pi.stop_sender()

    def start():
        pi.start_sender(duration_s=record_s + 8.0)
        pi.schedule_link_drop(at_s=drop_at, for_s=drop_for)

    print(f"\n[live] Pi {pi.target} (code {pi_commit}) -> {pi.data_host}; "
          f"link drop at {drop_at:g} s for {drop_for:g} s; recording {record_s:g} s")
    try:
        rows, sender = capture_udp(labels, cfg["icd"]["stale_intervals"], record_s,
                                   after_bind=start, first_word_timeout_s=25.0)
    finally:
        pi.stop_sender()
        pi.link_up()
    pt = pitch_times(rows, labels)
    gaps = np.diff(pt)
    i = int(np.argmax(gaps)) if len(gaps) else 0
    if not len(gaps) or gaps[i] < PULL_MIN_GAP_S:
        raise RuntimeError("live run saw no link drop: check the sudo rule for 'ip link' on the Pi")
    healthy = [r for r in rows if r[0] < pt[i] - 0.5]
    meta = {
        "recorded_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "mode": "live, automated (pytest --live)",
        "sender": sender,
        "pi_ssh": pi.target,
        "pi_code": pi_commit,
        "receiver_host": platform.node(),
        "receiver_os": f"{platform.system()} {platform.release()}",
        "link": "direct Ethernet cable, UDP, one ARINC 429 word per datagram",
        "link_drop": f"Pi eth0 down at {drop_at:g} s for {drop_for:g} s (ip link set)",
        "config_sha256_12": cfg["_hash"],
    }
    out = {"healthy": (healthy, {**meta, "capture": "healthy", "words": len(healthy),
                                 "note": "portion of the live run before the link drop"}),
           "cable_pull": (rows, {**meta, "capture": "cable_pull", "words": len(rows)})}
    for name, (r, m) in out.items():
        write_capture(BENCH / f"{name}.csv", r, m)
    return out


@pytest.fixture(scope="session")
def bench(request, cfg):
    if request.config.getoption("--live"):
        return run_live(cfg, request.config)
    out = {}
    for name in ("healthy", "cable_pull"):
        path = BENCH / f"{name}.csv"
        if path.exists():
            out[name] = read_capture(path)
    return out


def capture(bench, name: str):
    if name not in bench:
        pytest.skip(f"no bench recording {name}.csv yet: run with --live, "
                    f"or tools/bench_capture.py --name {name}")
    return bench[name]


def pitch_times(rows, labels):
    lookup = label_lookup(labels)
    return np.array([t for t, w in rows if lookup.get(label_of(w)) == "pitch"])


def receiver_trace(rows, cfg, labels, t_end, step=0.001):
    """Run the SIL receiver over the capture; return sample times and validity."""
    rx = Receiver(labels, stale_intervals=cfg["icd"]["stale_intervals"])
    lookup = label_lookup(labels)
    ts = np.arange(0.0, t_end, step)
    valid = np.zeros(len(ts), dtype=bool)
    i = 0
    for k, t in enumerate(ts):
        while i < len(rows) and rows[i][0] <= t:
            name = lookup.get(label_of(rows[i][1]))
            if name:
                rx.receive(name, rows[i][1], rows[i][0])
            i += 1
        valid[k] = rx.read("pitch", t)[0]
    return ts, valid


def replay(cfg, rows, duration):
    labels = label_defs(cfg)
    return run_scenario(cfg, duration_s=duration, pitch_fn=lambda t: TRUE_PITCH,
                        channel_override={0: ReplayChannel(rows, labels)})


# --------------------------------------------------------------- the words
@pytest.mark.req("ICD-1")
@pytest.mark.req("L1")
def test_l1_words_on_the_wire_decode_per_icd(cfg, bench, record_property):
    rows, meta = capture(bench, "healthy")
    labels = label_defs(cfg)
    lookup = label_lookup(labels)
    bad_label = [w for _, w in rows if label_of(w) not in lookup]
    decoded = [decode_bnr(w, labels[lookup[label_of(w)]]) for _, w in rows if label_of(w) in lookup]
    expect = TRUE_PITCH + cfg["sensors"]["bias_deg"][0]
    pitch = [d.value for (_, w), d in zip([r for r in rows if label_of(r[1]) in lookup], decoded)
             if lookup[label_of(w)] == "pitch"]
    record_property("words", len(rows))
    record_property("sender", meta.get("sender"))
    record_property("pitch_mean_deg", round(float(np.mean(pitch)), 3))
    assert not bad_label, f"{len(bad_label)} words with labels not in the ICD"
    assert all(d.parity_ok for d in decoded), "parity error on the wire"
    assert all(d.sdi == 1 for d in decoded), "channel A must send SDI 1"
    assert all(d.ssm == SSM.NORMAL for d in decoded)
    assert abs(np.mean(pitch) - expect) < 0.05


# --------------------------------------------------------------- the timing
@pytest.mark.req("L1")
def test_l1_rate_and_jitter_on_real_link(cfg, bench, record_property):
    rows, _ = capture(bench, "healthy")
    labels = label_defs(cfg)
    ld = labels["pitch"]
    dt = np.diff(pitch_times(rows, labels))
    nominal = 1.0 / ld.rate_hz
    stale_limit = cfg["icd"]["stale_intervals"] / ld.rate_hz
    jitter = np.abs(dt - nominal)
    record_property("intervals", len(dt))
    record_property("mean_ms", round(float(dt.mean()) * 1000, 3))
    record_property("p99_jitter_ms", round(float(np.percentile(jitter, 99)) * 1000, 2))
    record_property("max_interval_ms", round(float(dt.max()) * 1000, 2))
    record_property("stale_limit_ms", round(stale_limit * 1000, 1))
    assert abs(dt.mean() - nominal) / nominal <= 0.02
    assert dt.max() < stale_limit, "a healthy-link gap would trip the stale check"


@pytest.mark.req("L1")
@pytest.mark.req("R3")
def test_l1_no_false_stale_on_healthy_link(cfg, bench, record_property):
    rows, _ = capture(bench, "healthy")
    labels = label_defs(cfg)
    ts, valid = receiver_trace(rows, cfg, labels, rows[-1][0])
    after_first = ts > 0.001
    record_property("invalid_samples", int((~valid[after_first]).sum()))
    assert valid[after_first].all()


# --------------------------------------------------------------- cable pull
@pytest.mark.req("L1")
@pytest.mark.req("R3")
def test_l1_cable_pull_flagged_stale_and_recovers(cfg, bench, record_property):
    rows, _ = capture(bench, "cable_pull")
    labels = label_defs(cfg)
    ld = labels["pitch"]
    pt = pitch_times(rows, labels)
    gaps = np.diff(pt)
    i = int(np.argmax(gaps))
    if gaps[i] < PULL_MIN_GAP_S:
        pytest.skip("cable_pull.csv has no gap: re-record and pull the cable mid-run")
    t_last, t_back = pt[i], pt[i + 1]
    stale_limit = cfg["icd"]["stale_intervals"] / ld.rate_hz
    ts, valid = receiver_trace(rows, cfg, labels, rows[-1][0])
    went_invalid = ts[(ts > t_last) & ~valid]
    t_flag = float(went_invalid[0]) if len(went_invalid) else None
    back_valid = ts[(ts >= t_back) & valid]
    record_property("cable_out_s", round(float(gaps[i]), 2))
    record_property("flagged_after_ms", None if t_flag is None else round((t_flag - t_last) * 1000, 1))
    record_property("recovered_after_reconnect_ms",
                    None if not len(back_valid) else round((back_valid[0] - t_back) * 1000, 1))
    assert t_flag is not None, "receiver never flagged the pulled link"
    assert t_flag - t_last <= stale_limit + 0.002
    assert len(back_valid) and back_valid[0] - t_back <= 0.002, "no recovery after reconnect"


# --------------------------------------------------------------- closed loop
@pytest.mark.req("L1")
@pytest.mark.req("R5")
@pytest.mark.system
def test_l1_closed_loop_with_real_channel_a(cfg, bench, record_property):
    rows, _ = capture(bench, "healthy")
    dur = min(rows[-1][0], REPLAY_MAX_S)
    run = replay(cfg, rows, dur)
    settled = run.t > 0.2
    err = np.abs(run.voted[settled] - TRUE_PITCH)
    record_property("replayed_s", round(dur, 1))
    record_property("max_voted_error_deg", round(float(err.max()), 3))
    assert not run.failed
    assert all(m == Mode.TRIPLEX for m, s in zip(run.mode, settled) if s)
    assert err.max() <= cfg["voter"]["tolerance_deg"] + 0.35


@pytest.mark.req("L1")
@pytest.mark.req("R8")
@pytest.mark.req("R10")
@pytest.mark.system
def test_l1_closed_loop_cable_pull(cfg, bench, record_property):
    rows, _ = capture(bench, "cable_pull")
    labels = label_defs(cfg)
    pt = pitch_times(rows, labels)
    if np.diff(pt).max() < PULL_MIN_GAP_S:
        pytest.skip("cable_pull.csv has no gap: re-record and pull the cable mid-run")
    dur = rows[-1][0]
    run = replay(cfg, rows, dur)
    settled = run.t > 0.2
    modes = {m for m, s in zip(run.mode, settled) if s}
    law = cfg["command_law"]
    record_property("modes_seen", sorted(m.value for m in modes))
    record_property("ended_in", run.mode[-1].value)
    record_property("actuator_span_mm", round(float(np.ptp(run.pos[settled])), 3))
    assert Mode.DUAL in modes, "voter never dropped to dual while the cable was out"
    assert run.mode[-1] == Mode.TRIPLEX, "voter didn't return to triplex after reconnect"
    assert not run.failed, "a link loss must exclude channel A, not latch it failed"
    assert "DEGRADED_DUAL" in run.annunciations
    assert np.max(np.abs(run.cmd)) <= law["pos_limit_mm"] + 1e-9
    err = np.abs(run.voted[settled] - TRUE_PITCH)
    assert err.max() <= cfg["voter"]["tolerance_deg"] + 0.35
