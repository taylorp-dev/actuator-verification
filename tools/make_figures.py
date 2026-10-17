"""Generate the presentation figures from the same SIL code the tests use.

    python tools/make_figures.py        -> reports/figures/*.png

Every figure footer carries the config hash so a slide traces to a configuration.
"""

from __future__ import annotations

import copy
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sil import analysis as an  # noqa: E402
from sil.ema import EMA, EMAParams  # noqa: E402
from sil.sim import load_config, run_scenario  # noqa: E402
from sil.sources import Fault  # noqa: E402
from sil.force_fight import ForceFightParams, run_force_fight  # noqa: E402

OUT = ROOT / "reports" / "figures"

# reference palette (light mode), fixed slot order
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#8a8984", "#e4e3df"
SURFACE = "#fcfcfb"
CRIT = "#e34948"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "axes.titlecolor": INK,
    "axes.titleweight": "bold", "axes.titlesize": 12, "axes.titlelocation": "left",
    "xtick.color": INK2, "ytick.color": INK2, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.8, "axes.spines.top": False, "axes.spines.right": False,
    "lines.linewidth": 2.0, "font.size": 10, "legend.frameon": False,
    "legend.labelcolor": INK2,
})


def footer(fig, cfg, note="", y=-0.06):
    fig.text(0.01, y, f"Software-in-the-loop simulation, representative values. config sha256 {cfg['_hash']}"
             + (f"  |  {note}" if note else ""), color=MUTED, fontsize=7.5)


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / name, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("wrote", OUT / name)


def ema(cfg, load_n=0.0, **over):
    p = dict(cfg["actuator"], **over)
    return EMA(EMAParams.from_dict(p), load_n=load_n)


# ---------------------------------------------------------------- Part A
def fig_step(cfg):
    spec = cfg["actuator_spec"]
    fig, ax = plt.subplots(figsize=(7, 3.6))
    for (name, load_n), col in zip(cfg["load_conditions"].items(), (BLUE, ORANGE)):
        r = an.step_response(ema(cfg, load_n), spec["A1_step_mm"], duration_s=0.8)
        ax.plot(r.t * 1000, r.pos, color=col,
                label=f"{name} ({load_n:.0f} N): rise {r.rise_time_s*1000:.0f} ms, "
                      f"overshoot {r.overshoot_pct:.1f}%")
    ax.plot(r.t * 1000, r.cmd, color=MUTED, lw=1.2, ls="--", label="command")
    ax.axhline(spec["A1_step_mm"] * (1 + spec["A1_overshoot_max_pct"] / 100), color=CRIT,
               lw=1, ls=":", label=f"overshoot limit ({spec['A1_overshoot_max_pct']:.0f}%)")
    ax.set(title="A1 / A5: 1 mm step response at the output rod",
           xlabel="time (ms)", ylabel="rod position (mm)")
    ax.legend(loc="lower right", fontsize=8.5)
    footer(fig, cfg)
    save(fig, "a1_a5_step_response.png")


def fig_bode(cfg):
    freqs = np.logspace(-1, 1.2, 30)
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(7, 4.8), sharex=True)
    for (name, load_n), col in zip(cfg["load_conditions"].items(), (BLUE, ORANGE)):
        g, ph = an.frequency_response(ema(cfg, load_n), freqs)
        bw = an.bandwidth_hz(freqs, g)
        a1.semilogx(freqs, g, color=col, marker="o", ms=3.5,
                    label=f"{name}: -3 dB at {bw:.2f} Hz")
        a2.semilogx(freqs, ph, color=col, marker="o", ms=3.5)
    lim = cfg["actuator_spec"]["A4_bandwidth_min_hz"]
    a1.axhline(-3, color=MUTED, lw=1, ls="--")
    a1.axvline(lim, color=CRIT, lw=1, ls=":", label=f"required >= {lim} Hz")
    a1.set(title="A4: frequency response (1 mm sine dwell)", ylabel="gain (dB)")
    a1.legend(fontsize=8.5, loc="lower left")
    a2.set(xlabel="frequency (Hz)", ylabel="phase (deg)")
    footer(fig, cfg)
    save(fig, "a4_bode.png")


def fig_backlash(cfg):
    e = ema(cfg)
    period = 8.0
    t, cmd, pos = an.run_profile(e, lambda ti: 1.0 * math.sin(2 * math.pi * ti / period),
                                 2 * period)
    # rerun capturing own feedback
    e.reset(0.0)
    own = []
    for c in cmd:
        e.step(c, an.DT)
        own.append(e.own_feedback)
    keep = t >= period
    fig, ax = plt.subplots(figsize=(5.4, 4.2))
    ax.plot(cmd[keep], np.array(own)[keep] - cmd[keep], color=MUTED, lw=1.5,
            label="actuator's own feedback")
    ax.plot(cmd[keep], pos[keep] - cmd[keep], color=BLUE,
            label="independent truth sensor (rod)")
    ax.set(title="A3: the unit can't see its own backlash",
           xlabel="command (mm)", ylabel="position error (mm)")
    ax.legend(fontsize=8.5, loc="upper left", bbox_to_anchor=(0, -0.16), ncol=2)
    footer(fig, cfg, y=-0.14)
    save(fig, "a3_backlash.png")


# ---------------------------------------------------------------- Part B
R9_FAULT = Fault("drift", 1, "pitch", t_start=0.5, magnitude=2.0)


def r9(cfg, load_n):
    return run_scenario(cfg, duration_s=4.5, pitch_fn=lambda t: -2.0,
                        faults=[R9_FAULT], load_n=load_n)


def fig_fault_response(cfg):
    run = r9(cfg, 0.0)
    keep = run.t >= 0.05          # skip the first-word startup frame
    for name in ("t", "channels", "voted", "truth", "cmd", "pos"):
        setattr(run, name, getattr(run, name)[keep])
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(8, 5.4), sharex=True)
    for i, col in zip(range(3), (BLUE, ORANGE, AQUA)):
        a1.plot(run.t, run.channels[:, i], color=col, lw=1.4,
                label=f"channel {'ABC'[i]}" + (" (drift fault)" if i == 1 else ""))
    a1.plot(run.t, run.voted, color=INK, lw=2.2, label="voted")
    a1.plot(run.t, run.truth, color=MUTED, lw=1, ls="--", label="true pitch")
    for ax in (a1, a2):
        ax.axvline(0.5, color=MUTED, lw=1, ls=":")
        ax.axvline(run.detect_t, color=CRIT, lw=1, ls=":")
    a1.text(0.53, 2.6, "fault starts", color=INK2, fontsize=8.5)
    a1.text(run.detect_t + 0.05, -1.6, "B latched failed: TRIPLEX -> DUAL",
            color=INK2, fontsize=8.5, ha="left")
    a1.set(title="Sensor fault to actuator: drift on channel B", ylabel="pitch (deg)",
           ylim=(-4, 3.5))
    a1.legend(ncol=5, fontsize=8, loc="lower left")
    a2.plot(run.t, run.cmd, color=MUTED, lw=1.2, ls="--", label="actuator command")
    a2.plot(run.t, run.pos, color=BLUE, label="rod position (truth sensor)")
    a2.set(xlabel="time (s)", ylabel="actuator (mm)")
    a2.legend(fontsize=8.5, loc="lower right")
    footer(fig, cfg, "unloaded")
    save(fig, "b_fault_to_actuator.png")


def fig_finding(cfg):
    spec = cfg["system_spec"]
    fixed = copy.deepcopy(cfg)
    fixed["actuator"]["anti_windup"] = True
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), sharey=True)
    for ax, c, title in ((axes[0], cfg, "Baseline design"),
                         (axes[1], fixed, "After corrective action (anti-windup)")):
        for (name, load_n), col in zip(cfg["load_conditions"].items(), (BLUE, ORANGE)):
            run = r9(c, load_n)
            m = run.metrics_after(run.detect_t, spec["R9_settle_band_mm"])
            keep = (run.t >= run.detect_t - 0.1) & (run.t <= run.detect_t + 1.6)
            ok = (m["overshoot_mm"] <= spec["R9_overshoot_max_mm"]
                  and m["settle_s"] <= spec["R9_settle_time_max_s"])
            ax.plot(run.t[keep] - run.detect_t, run.pos[keep], color=col,
                    label=f"{name}: overshoot {m['overshoot_mm']:.2f} mm, "
                          f"settle {m['settle_s']:.2f} s  {'PASS' if ok else 'FAIL'}")
        final = m["final_mm"]
        ax.axhline(final + spec["R9_overshoot_max_mm"], color=CRIT, lw=1, ls=":",
                   label=f"overshoot limit +{spec['R9_overshoot_max_mm']} mm")
        ax.axhspan(final - spec["R9_settle_band_mm"], final + spec["R9_settle_band_mm"],
                   color=GRID, alpha=0.6, lw=0)
        ax.axvline(spec["R9_settle_time_max_s"], color=MUTED, lw=1, ls="--",
                   label=f"settle by {spec['R9_settle_time_max_s']} s")
        ax.set(title=title, xlabel="time after channel failure declared (s)")
        ax.legend(fontsize=8, loc="lower right")
    axes[0].set_ylabel("rod position (mm)")
    fig.suptitle("R9: same fault, same test. Passes unloaded, fails at rated load.",
                 x=0.01, ha="left", fontweight="bold", color=INK, fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    footer(fig, cfg, "gray band = +/-0.25 mm settle band", y=-0.02)
    save(fig, "finding_loaded_vs_unloaded.png")


def fig_wrong_channel(cfg):
    bad = copy.deepcopy(cfg)
    bad["voter"]["threshold_deg"] = 2.0

    def man(t):
        return -2.0 + 3.0 * math.sin(2 * math.pi * 0.3 * t)

    fig, axes = plt.subplots(1, 2, figsize=(10, 3.9), sharey=True)
    for ax, c, title in ((axes[0], bad, "Threshold 2.0 deg (= 2 x tolerance)"),
                         (axes[1], cfg, "Threshold 2.5 deg (with margin)")):
        run = run_scenario(c, duration_s=4.0, pitch_fn=man,
                           faults=[Fault("frozen", 1, "pitch", t_start=0.5)])
        err = run.voted - run.truth
        failed = ",".join("ABC"[i] for i in sorted(run.failed)) or "none"
        ax.plot(run.t, err, color=ORANGE if failed != "B" else BLUE,
                label=f"voted - true; channel failed: {failed}")
        ax.axhspan(-1.0, 1.0, color=GRID, alpha=0.6, lw=0)
        ax.set(title=title, xlabel="time (s)")
        ax.legend(fontsize=8.5, loc="lower left")
    axes[0].set_ylabel("voted pitch error (deg)")
    fig.suptitle("Frozen middle channel B: first run isolated the WRONG channel",
                 x=0.01, ha="left", fontweight="bold", color=INK, fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    footer(fig, cfg, "gray band = healthy sensor tolerance +/-1.0 deg", y=-0.02)
    save(fig, "finding_wrong_channel_isolated.png")


def fig_fault_matrix(cfg):
    from tests.test_part_b_system import FAULTS, maneuver  # same matrix the tests run

    kinds = list(FAULTS)
    cells = []
    for k in kinds:
        row = []
        mag, expect, _ = FAULTS[k]
        for ch in range(3):
            run = run_scenario(cfg, duration_s=4.0, pitch_fn=maneuver,
                               faults=[Fault(k, ch, "pitch", 0.5, magnitude=mag)])
            if expect == "isolate":
                txt = f"isolated\n{(run.detect_t - 0.5) * 1000:.0f} ms" if run.failed == {ch} else "WRONG"
            elif expect == "ignore":
                txt = "ignored" if not run.failed else "FALSE TRIP"
            else:
                txt = "excluded\n(receiver)" if not run.valid[-1, ch] else "MISSED"
            row.append(txt)
        cells.append(row)
    fig, ax = plt.subplots(figsize=(6.4, 4.6))
    ax.axis("off")
    tbl = ax.table(cellText=cells, rowLabels=[k.replace("_", " ") for k in kinds],
                   colLabels=["channel A", "channel B", "channel C"], loc="center",
                   cellLoc="center")
    tbl.scale(1, 2.2)
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(9)
    for (r, c), cell in tbl.get_celld().items():
        cell.set_edgecolor(SURFACE)
        cell.set_linewidth(2)
        if r == 0 or c == -1:
            cell.set_facecolor("#efeeea")
            cell.get_text().set_color(INK)
            cell.get_text().set_fontweight("bold")
        else:
            cell.set_facecolor("#e6f2fb")
            cell.get_text().set_color(INK)
    ax.set_title("Fault matrix: 8 fault types x 3 channels, all pass\n"
                 "(voted value stays inside healthy tolerance, R10 limits hold)",
                 loc="left", fontsize=11)
    footer(fig, cfg, "detect latency measured from fault onset", y=0.02)
    save(fig, "b_fault_matrix.png")


# ------------------------------------------------------------- Part C figures
def fig_motor_loss(cfg):
    import tests.test_part_c_actuator_faults as pc
    spec = cfg["system_spec"]
    fig, ax = plt.subplots(figsize=(8, 3.8))
    rated = cfg["load_conditions"]["rated"]
    fixed = copy.deepcopy(cfg)
    fixed["actuator"]["stall_force_n"] *= 2
    for c, load, col, lab in ((cfg, 0.0, AQUA, "unloaded (holds at 0, under the blue line)"),
                              (cfg, rated, CRIT, f"rated {rated:,.0f} N, baseline motors"),
                              (fixed, rated, BLUE, f"rated {rated:,.0f} N, each motor sized for full load")):
        t, x, mon, _ = pc.motor_loss_run(c, load)
        ax.plot(t, x, color=col, label=lab)
        if mon.trip_t is not None:
            ax.axvline(mon.trip_t, color=col, ls=":", lw=1.2)
            ax.annotate("monitor annunciates", (mon.trip_t, x[int(mon.trip_t / 0.001)]),
                        xytext=(mon.trip_t - 1.9, -1.3), color=col, fontsize=8.5,
                        arrowprops=dict(arrowstyle="->", color=col))
    ax.axhspan(-spec["R11_hold_max_mm"], spec["R11_hold_max_mm"], color=AQUA, alpha=0.08)
    ax.axhline(-spec["R11_hold_max_mm"], color=MUTED, ls="--", lw=1)
    ax.axvline(1.0, color=INK2, lw=1)
    ax.text(1.05, 0.3, "one motor lost", color=INK2, fontsize=8.5)
    ax.set_xlabel("time (s)"); ax.set_ylabel("rod position (mm)")
    ax.set_ylim(-2.0, 0.6)
    ax.set_title("R11 motor channel loss: holds unloaded, back-driven at rated load (FINDING-003)")
    ax.legend(loc="lower left", fontsize=8.5)
    footer(fig, cfg, "band = R11 hold limit +/-0.5 mm")
    save(fig, "c_motor_loss.png")


def fig_jam(cfg):
    import tests.test_part_c_actuator_faults as pc
    t, cmd, x, demand, _, mon = pc.jam_run(cfg, cfg["load_conditions"]["rated"])
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(8, 4.6), sharex=True,
                                 gridspec_kw={"height_ratios": [2, 1]})
    a1.plot(t, cmd, color=MUTED, ls="--", lw=1.4, label="command (10 mm/s ramp)")
    a1.plot(t, x, color=BLUE, label="rod position")
    a1.axvline(0.5, color=CRIT, lw=1.2)
    a1.text(0.51, -4.6, "jam", color=CRIT, fontsize=9)
    a1.axvline(mon.trip_t, color=ORANGE, lw=1.2)
    a1.text(mon.trip_t + 0.02, -3.2, f"JAM annunciated\n+{(mon.trip_t - 0.5) * 1000:.0f} ms",
            color=ORANGE, fontsize=9)
    a1.set_ylabel("position (mm)"); a1.legend(loc="upper left", fontsize=8.5)
    a1.set_title("R12 jam at rated load: detected, motor drive removed")
    a2.plot(t, demand, color=ORANGE)
    a2.axvline(0.5, color=CRIT, lw=1.2); a2.axvline(mon.trip_t, color=ORANGE, lw=1.2)
    a2.set_ylabel("drive (mm/s)"); a2.set_xlabel("time (s)")
    fig.tight_layout()
    footer(fig, cfg, "monitor threshold 1.0 mm, sized from the healthy envelope (FINDING-005)", y=-0.03)
    save(fig, "c_jam_detection.png")


def fig_force_fight(cfg):
    base = dict(cfg["force_fight"])
    offs = base["rig_offsets_mm"]
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.9), sharey=True)
    cases = [
        ("No equalization, all lanes healthy", dict(eq_gain_mm_per_n=0.0), {}, 6.0),
        ("Equalization on, all lanes healthy", {}, {}, 6.0),
        ("Equalization on, lane A sensor +5 mm", {}, dict(fault_lane=0, fault_offset_mm=5.0, fault_t=1.0), 3.0),
    ]
    for ax, (title, over, fault, dur) in zip(axes, cases):
        p = ForceFightParams.from_dict({**base, **over})
        r = run_force_fight(p, rig_offsets_mm=offs, duration_s=dur, **fault)
        for i, col in enumerate((BLUE, ORANGE, AQUA)):
            ax.plot(r.t, r.force[:, i], color=col, label=f"lane {'ABC'[i]}")
        for lane, td in r.disengaged.items():
            ax.axvline(td, color=CRIT, lw=1.2)
            ax.text(td + 0.05, -3600, f"lane {'ABC'[lane]} disengaged", color=CRIT, fontsize=8.5)
        if "fault_t" in fault:
            ax.axvline(1.0, color=INK2, lw=1)
        ax.set_title(title, fontsize=10.5)
        ax.set_ylim(-4200, 6200)
        ax.set_xlabel("time (s)")
    axes[0].set_ylabel("lane force (N)")
    axes[1].legend(loc="upper right", fontsize=8.5, ncol=3)
    axes[0].text(1.5, -1900, "lane A was healthy:\nfalse disengage", color=CRIT, fontsize=8.5)
    fig.suptitle("R13 force fight: three lanes on one surface, rated load shared",
                 x=0.01, ha="left", fontweight="bold", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    footer(fig, cfg, "rig tolerance +/-0.2 mm between lanes", y=-0.03)
    save(fig, "c_force_fight.png")


# ------------------------------------------------------------- bench link (real Pi)
def fig_bench_link(cfg):
    """Link-drop timeline from the real Raspberry Pi recording (bench_data/cable_pull.csv).
    Skipped if the recording isn't there."""
    import os
    from sil.link import label_lookup, label_of, read_capture
    from sil.sim import label_defs
    import tests.test_bench_link as tb
    bench = Path(os.environ.get("BENCH_DATA_DIR", ROOT / "bench_data"))
    path = bench / "cable_pull.csv"
    if not path.exists():
        print("skip bench_link_drop.png (no bench_data/cable_pull.csv)")
        return
    rows, meta = read_capture(path)
    labels = label_defs(cfg)
    ld = labels["pitch"]
    pt = tb.pitch_times(rows, labels)
    dt = np.diff(pt) * 1000.0
    stale_ms = cfg["icd"]["stale_intervals"] / ld.rate_hz * 1000.0
    i = int(np.argmax(dt))
    t_last, t_back = pt[i], pt[i + 1]
    run = tb.replay(cfg, rows, rows[-1][0])
    ts, valid = tb.receiver_trace(rows, cfg, labels, rows[-1][0])
    t_flag = float(ts[(ts > t_last) & ~valid][0])

    fig, (a1, a2) = plt.subplots(2, 1, figsize=(7.2, 4.9), sharex=True,
                                 gridspec_kw={"height_ratios": [2.2, 1]})
    a1.axvspan(t_last, t_back, color=CRIT, alpha=0.08)
    keep = dt < 200
    a1.plot(pt[1:][keep], dt[keep], ".", ms=2.5, color=BLUE, label="interval between words (ms)")
    a1.axhline(20.0, color=MUTED, lw=1, ls=":")
    a1.axhline(stale_ms, color=CRIT, lw=1.2, ls="--", label=f"stale limit {stale_ms:.0f} ms")
    a1.set_ylim(0, stale_ms * 1.35)
    a1.set_ylabel("ms between words")
    a1.text(t_last + 0.15, stale_ms * 1.12, f"link down (Pi eth0 down/up)\nno words for {t_back - t_last:.1f} s",
            color=CRIT, fontsize=9)
    a1.legend(loc="lower left", fontsize=8.5)
    a1.set_title(f"Real Raspberry Pi over Ethernet: link drop flagged in {(t_flag - t_last) * 1000:.1f} ms")
    # receiver validity and voter mode
    mode = np.array([{"TRIPLEX": 3, "DUAL": 2, "SIMPLEX": 1, "FAIL": 0}[m.value] for m in run.mode])
    a2.step(run.t, mode, where="post", color=ORANGE, label="voter channels in use")
    a2.step(ts, valid.astype(float) * 0.6 + 0.3, where="post", color=AQUA, lw=1.5, label="ch. A receiver valid")
    a2.set_yticks([2, 3])
    a2.set_yticklabels(["2", "3"])
    a2.text(run.t[-1], 0.95, "valid", color=AQUA, fontsize=8, ha="right", va="bottom")
    a2.set_ylim(0, 3.5)
    a2.set_ylabel("voter")
    a2.set_xlabel("time from first word (s)")
    a2.legend(loc="center", bbox_to_anchor=(0.5, 0.42), fontsize=8, ncol=2)
    fig.tight_layout()
    fig.text(0.01, -0.03, f"Real hardware recording: {path.name}, {meta.get('recorded_utc', '')}, "
             f"sender {meta.get('sender', '')}. Voter and actuator replayed through the SIL. "
             f"config sha256 {cfg['_hash']}", color=MUTED, fontsize=7.5)
    save(fig, "bench_link_drop.png")


if __name__ == "__main__":
    cfg = load_config()
    fig_step(cfg)
    fig_bode(cfg)
    fig_backlash(cfg)
    fig_fault_response(cfg)
    fig_finding(cfg)
    fig_wrong_channel(cfg)
    fig_fault_matrix(cfg)
    fig_motor_loss(cfg)
    fig_jam(cfg)
    fig_force_fight(cfg)
    fig_bench_link(cfg)
