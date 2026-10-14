"""Part A: actuator characterization, bench acceptance test style (A1-A5).

Measurements are taken at the output rod (independent truth sensor), never
from the actuator's own feedback.
"""

import numpy as np
import pytest

from sil import analysis as an
from sil.ema import EMA, EMAParams


def make_ema(cfg, load_n=0.0):
    return EMA(EMAParams.from_dict(cfg["actuator"]), load_n=load_n)


@pytest.mark.req("A1")
def test_a1_small_signal_step_unloaded(cfg, record_property):
    spec = cfg["actuator_spec"]
    r = an.step_response(make_ema(cfg), spec["A1_step_mm"])
    record_property("rise_s", round(r.rise_time_s, 3))
    record_property("overshoot_pct", round(r.overshoot_pct, 1))
    assert r.rise_time_s <= spec["A1_rise_time_max_s"]
    assert r.overshoot_pct <= spec["A1_overshoot_max_pct"]


@pytest.mark.req("A2")
def test_a2_max_rate(cfg, load_condition, record_property):
    name, load_n = load_condition
    spec = cfg["actuator_spec"]
    limit = spec["A2_rate_min_unloaded_mm_s"] if load_n == 0 else spec["A2_rate_min_rated_mm_s"]
    rate = an.max_rate(make_ema(cfg, load_n), direction=+1.0)   # extend, against the load
    record_property("load", name)
    record_property("rate_mm_s", round(rate, 1))
    assert rate >= limit


@pytest.mark.req("A3")
def test_a3_accuracy_and_backlash(cfg, record_property):
    spec = cfg["actuator_spec"]
    acc, backlash = an.backlash_and_accuracy(make_ema(cfg))
    record_property("accuracy_mm", round(acc, 3))
    record_property("backlash_mm", round(backlash, 3))
    assert acc <= spec["A3_accuracy_max_mm"]
    assert backlash <= spec["A3_backlash_max_mm"]


@pytest.mark.req("A3")
def test_a3_own_feedback_cannot_see_backlash(cfg, record_property):
    """Why the truth sensor matters: the unit's own sensor reports ~zero error."""
    ema = make_ema(cfg)
    readings = []
    for start in (-2.0, 2.0):
        an.run_profile(ema, lambda t: 0.0, 3.0, start)
        readings.append(ema.own_feedback)
    own_hyst = abs(readings[0] - readings[1])
    _, truth_hyst = an.backlash_and_accuracy(make_ema(cfg), points_mm=(0,))
    record_property("own_feedback_hysteresis_mm", round(own_hyst, 3))
    record_property("truth_hysteresis_mm", round(truth_hyst, 3))
    assert own_hyst < 0.25 * truth_hyst


@pytest.mark.req("A4")
def test_a4_bandwidth(cfg, record_property):
    freqs = np.logspace(-1, 1.2, 22)
    gains, _ = an.frequency_response(make_ema(cfg), freqs)
    bw = an.bandwidth_hz(freqs, gains)
    record_property("bandwidth_hz", round(bw, 2))
    assert bw >= cfg["actuator_spec"]["A4_bandwidth_min_hz"]


@pytest.mark.req("A5")
def test_a5_small_signal_step_rated_load(cfg, record_property):
    spec = cfg["actuator_spec"]
    r = an.step_response(make_ema(cfg, cfg["load_conditions"]["rated"]), spec["A1_step_mm"])
    record_property("rise_s", round(r.rise_time_s, 3))
    record_property("overshoot_pct", round(r.overshoot_pct, 1))
    assert r.rise_time_s <= spec["A5_rise_time_max_s"]
    assert r.overshoot_pct <= spec["A5_overshoot_max_pct"]


@pytest.mark.req("A5")
def test_a5_accuracy_rated_load(cfg, record_property):
    acc, _ = an.backlash_and_accuracy(make_ema(cfg, cfg["load_conditions"]["rated"]))
    record_property("accuracy_mm", round(acc, 3))
    assert acc <= cfg["actuator_spec"]["A3_accuracy_max_mm"]
