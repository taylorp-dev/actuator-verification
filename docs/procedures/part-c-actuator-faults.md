# Part C actuator faults: test procedures

These tests cover faults inside the actuation system: losing one of two motor channels (R11), a jammed screw and the tracking monitor that must catch it without false alarms (R12), and three actuator lanes pushing on one surface (R13). Every test here is **System** level: the actuator model and its monitor run together in closed loop, the R13 tests use the three-lane force-fight model in `sil/force_fight.py`, and two R12 tests run the full Part B loop through `run_scenario()`. Test file: `tests/test_part_c_actuator_faults.py`.

| TC | Requirement(s) | Test function | Cases | Last result |
|---|---|---|---|---|
| [TC-R11-S01](#tc-r11-s01-hold-position-after-losing-one-motor) | R11 | `test_r11_motor_channel_loss_hold` | 2 | 1 PASS, 1 OPEN DEFECT (FINDING-003) |
| [TC-R11-S02](#tc-r11-s02-position-loss-after-a-motor-loss-is-annunciated) | R11 | `test_r11_if_position_is_lost_it_is_annunciated` | 2 | PASS |
| [TC-R11-S03](#tc-r11-s03-corrective-option-a-holds-at-every-load) | R11 | `test_r11_corrective_option_verified` | 2 | PASS |
| [TC-R12-S01](#tc-r12-s01-jam-is-detected-and-motor-drive-is-removed) | R12 | `test_r12_jam_detected_and_drive_removed` | 6 | PASS |
| [TC-R12-S02](#tc-r12-s02-jam-with-a-still-command-stays-latent) | R12 | `test_r12_jam_with_stationary_command_is_latent` | 1 | PASS |
| [TC-R12-S03](#tc-r12-s03-no-false-alarm-on-a-rate-limited-move-at-rated-load) | R12 | `test_r12_no_false_alarm_on_rate_limited_move_at_rated_load` | 1 | PASS |
| [TC-R12-S04](#tc-r12-s04-no-false-alarm-on-a-bandwidth-sine) | R12 | `test_r12_no_false_alarm_on_bandwidth_sine` | 1 | PASS |
| [TC-R12-S05](#tc-r12-s05-no-false-alarm-across-all-part-b-sensor-faults) | R12 | `test_r12_no_false_alarm_across_part_b_faults` | 4 | PASS |
| [TC-R12-S06](#tc-r12-s06-baseline-actuator-gives-false-alarms-open-defect) | R12 | `test_r12_no_false_alarm_baseline_actuator` | 1 | OPEN DEFECT (FINDING-005) |
| [TC-R13-S01](#tc-r13-s01-healthy-lanes-share-load-with-equalization) | R13 | `test_r13_healthy_lanes_share_load_with_equalization` | 1 | PASS |
| [TC-R13-S02](#tc-r13-s02-without-equalization-healthy-lanes-fight-and-trip) | R13 | `test_r13_without_equalization_healthy_lanes_fight_and_trip` | 1 | PASS |
| [TC-R13-S03](#tc-r13-s03-faulty-lane-is-disengaged-and-only-that-lane) | R13 | `test_r13_faulty_lane_disengaged` | 15 | PASS |
| [TC-R13-S04](#tc-r13-s04-undetected-lane-fault-stays-small) | R13 | `test_r13_undetected_lane_fault_stays_small` | 6 | PASS |
| [TC-R13-S05](#tc-r13-s05-guard-test-for-finding-004-drops-only-the-largest-outlier) | R13 | `test_r13_guard_monitor_isolates_only_the_largest_outlier` | 1 | PASS |

**Common setup for this file** (pytest does this before every test):

| Item | Python command | Where |
|---|---|---|
| Mark every test in the file as a slow system test | `pytestmark = pytest.mark.system` | test file line 25 |
| Load settings once per session (shared, must not be changed) | `return load_config()` in fixture `cfg()` | conftest.py lines 56–59 |
| Load a private copy of the settings that a test may change | `return load_config()` in fixture `fresh_cfg()` | conftest.py lines 62–65 |
| Run the test once per load condition: `unloaded` (0 N) and `rated` (4550 N) | `return name, cfg["load_conditions"][name]` in fixture `load_condition` | conftest.py lines 72–76; loads from `load_conditions` in config/sil.yaml lines 18–20 |
| Record measured values into the report | `record_property(...)` (built into pytest) | used in each test |
| Simulation time step, 1 ms (1 kHz) | `DT = 0.001` | sil/sim.py line 26 |
| Build an actuator with a given load | `return EMA(EMAParams.from_dict(cfg["actuator"]), load_n=load_n)` in `make_ema()` | test file lines 28–29 |
| Build the tracking monitor (threshold 1.0 mm, "not moving" below 2.0 mm/s, persistence 0.10 s, speed window 0.02 s) | `ActuatorMonitor.from_cfg(cfg["actuator_monitor"], DT)` | used in the R11 and R12 tests; settings in config/sil.yaml lines 67–72 |
| Build the force-fight settings for R13, with optional overrides | `d = dict(cfg["force_fight"])` / `d.update(over)` / `return ForceFightParams.from_dict(d)` in `ff_params()` | test file lines 252–255 |

**How the tracking monitor decides** (sil/actuator_monitor.py lines 35–44, used by every R11 and R12 test): each 1 ms it stores the actuator's own feedback position, works out its speed over the last 0.02 s, and calls the actuator "stuck" when the command-vs-feedback error is above 1.0 mm **and** the speed is below 2.0 mm/s. If "stuck" holds for 0.10 s without a break, the monitor trips (`tripped = True`, `trip_t` = that time). Once tripped it stays tripped.

**How a single test is run:** a single test or a single file is a partial run. Its report goes to `reports/dev/`, not for record.

---

## TC-R11-S01: Hold position after losing one motor

| Field | Value |
| --- | --- |
| Requirement | R11: After loss of one of two motor channels, the actuator shall hold commanded position within 0.50 mm for 5 s at every load condition up to rated. |
| Level | System (actuator model + tracking monitor in closed loop) |
| Test file | `tests/test_part_c_actuator_faults.py` |
| Test function | `test_r11_motor_channel_loss_hold` (lines 68–71, marks on lines 62–67); helpers `motor_loss_run` (lines 33–48) and `r11_check` (lines 51–59) |

**Purpose:** hold the rod at 0 mm, lose one of the two motors at 1 s, and show the rod stays within 0.50 mm for the next 5 s. Baseline sizing: each motor gives half of the 6500 N total stall force (3250 N). Rated load is 4550 N, more than one motor can push, so the rated case is expected to fail (FINDING-003).

**How to run (PowerShell, from the repo folder):**
```
python -m pytest "tests/test_part_c_actuator_faults.py::test_r11_motor_channel_loss_hold" -v
```
Expected output: `1 passed, 1 xfailed`.

**Initial condition:** actuator at 0 mm, both motors healthy, integrator pre-loaded so a loaded actuator starts in balance.

**Cases** (set by `@pytest.mark.parametrize("load_name", ...)`, lines 63–67):

| Case | Load | Expected | Last result (2026-10-18) |
|---|---|---|---|
| `unloaded` | 0 N | Pass | PASS. Stall force after loss 3250 N, max deviation 0.0 mm, monitor did not trip (`None`). |
| `rated` | 4550 N | Expected fail (xfail), FINDING-003 | OPEN DEFECT (expected fail, FINDING-003): "FINDING-003: one motor's stall force is below rated load; rod is back-driven". Stall force after loss 3250 N, max deviation 1.697 mm, monitor tripped 2.97 s after the loss. |

**Steps:**

| Step | Action | Python command | Expected result | Line |
|---|---|---|---|---|
| 1 | Look up the load for this case and run the check | `r11_check(cfg, cfg["load_conditions"][load_name], record_property)` | Check runs | 71 |
| 2 | Run the motor-loss scenario: hold 0 mm, lose a motor at 1.0 s, run 6.0 s total (1.0 s + `R11_hold_s` 5.0 s) | `t, x, mon, ema = motor_loss_run(cfg, load_n)` | Run completes | 53 (helper 33–48) |
| 2a | *(inside the run)* Build the actuator with this load, put it at 0 mm, build the monitor | `ema = make_ema(cfg, load_n)` / `ema.reset(0.0)` / `mon = ActuatorMonitor.from_cfg(...)` | Actuator at rest at 0 mm | 37–39 |
| 2b | *(inside the run)* At the first step at or after 1.0 s, fail one motor. The usable stall force drops to half (3250 N); the no-load speed stays the same | `if t[k] >= t_fail and ema.motors_healthy == ema.p.n_motors:` / `ema.fail_motor()` | One motor left | 44–45; sil/ema.py lines 64–67, 78–79 |
| 2c | *(inside the run)* Each 1 ms, step the actuator with a command of 0 mm and save the rod position. The load always back-drives the motor side at 4550 / 13000 = 0.35 mm/s; the controller can only push back up to the speed one motor can give against the load (zero at rated load) | `x[k] = ema.step(0.0, DT)` | Rod position saved | 46; sil/ema.py lines 82–90, 99–132 |
| 2d | *(inside the run)* Feed the monitor the command (0 mm) and the actuator's own feedback. Observe only: the monitor does not cut the drive in this test | `mon.update(t[k], 0.0, ema.own_feedback)` | Monitor state updated | 47 |
| 3 | Find the largest rod deviation from 0 mm from 1.0 s on | `dev = float(np.max(np.abs(x[t >= 1.0])))` | Number found | 54 |
| 4 | Record load, stall force left, max deviation, and monitor trip time measured from 1.0 s | `record_property("load_n", load_n)` ... `record_property("monitor_trip_after_s", ...)` | Values recorded | 55–58 |
| 5 | Check the hold | `dev <= spec["R11_hold_max_mm"]` | `True`: max deviation ≤ 0.50 mm (limit from `system_spec.R11_hold_max_mm`) | 59 |

**Pass criteria:** step 5 is `True`. For the `rated` case the test is marked as an expected failure: the case is reported as "xfailed" when step 5 is `False`, and the run fails if it unexpectedly passes (`xfail_strict = true` in pytest.ini).

**Last result (2026-10-18):** unloaded PASS (0.0 mm). Rated OPEN DEFECT (expected fail, FINDING-003): rod drifted 1.697 mm, more than 3 times the 0.50 mm limit. See docs/rca/FINDING-003-motor-loss-at-rated-load.md.

---

## TC-R11-S02: Position loss after a motor loss is annunciated

| Field | Value |
| --- | --- |
| Requirement | R11 (as in TC-R11-S01) |
| Level | System (actuator model + tracking monitor in closed loop) |
| Test file | `tests/test_part_c_actuator_faults.py` |
| Test function | `test_r11_if_position_is_lost_it_is_annunciated` (lines 75–84, mark on line 74); helper `motor_loss_run` (lines 33–48) |

**Purpose:** when the actuator cannot hold after a motor loss, the tracking monitor must say so; it must never drift silently. The check works both ways: monitor trips if and only if the rod drifted past the monitor threshold.

**How to run (PowerShell, from the repo folder):**
```
python -m pytest "tests/test_part_c_actuator_faults.py::test_r11_if_position_is_lost_it_is_annunciated" -v
```
Expected output: `2 passed`.

**Initial condition:** as in TC-R11-S01.

**Cases** (from the `load_condition` fixture):

| Case | Load | Last result (2026-10-18) |
|---|---|---|
| `unloaded` | 0 N | PASS. Drifted past threshold: `False`; monitor did not trip (`None`). |
| `rated` | 4550 N | PASS. Drifted past threshold: `True`; monitor tripped 2.97 s after the loss. |

**Steps:**

| Step | Action | Python command | Expected result | Line |
|---|---|---|---|---|
| 1 | Get the load name and value for this case | `name, load_n = load_condition` | Load set | 78 |
| 2 | Run the motor-loss scenario (hold 0 mm, lose a motor at 1.0 s, 6.0 s total) | `t, x, mon, _ = motor_loss_run(cfg, load_n)` | Run completes | 79 |
| 2a–2d | *(inside the run)* Same as TC-R11-S01 steps 2a–2d: one motor fails at 1.0 s, the actuator is stepped every 1 ms with a 0 mm command, the monitor watches the actuator's own feedback (observe only) | see TC-R11-S01 | | 33–48 |
| 3 | Decide whether the rod drifted more than the monitor threshold after 1.0 s | `drifted = float(np.max(np.abs(x[t >= 1.0]))) > cfg["actuator_monitor"]["err_threshold_mm"]` | `True` or `False` (threshold 1.0 mm, from `actuator_monitor.err_threshold_mm`) | 80 |
| 4 | Record load name, drift flag, monitor trip time from 1.0 s | `record_property("load", name)` ... | Values recorded | 81–83 |
| 5 | Check the monitor agrees with the drift | `mon.tripped == drifted` | `True`: tripped when drifted past 1.0 mm, quiet when not | 84 |

**Pass criteria:** step 5 is `True` for both loads.

**Last result (2026-10-18):** PASS on both loads. Unloaded: no drift, no trip. Rated: drift past 1.0 mm and the monitor tripped 2.97 s after the loss.

---

## TC-R11-S03: Corrective option A holds at every load

| Field | Value |
| --- | --- |
| Requirement | R11 (as in TC-R11-S01) |
| Level | System (actuator model + tracking monitor in closed loop) |
| Test file | `tests/test_part_c_actuator_faults.py` |
| Test function | `test_r11_corrective_option_verified` (lines 88–94, mark on line 87); helpers `r11_check` (lines 51–59) and `motor_loss_run` (lines 33–48) |

**Purpose:** verify FINDING-003 corrective option A. Each motor is sized to carry rated load alone (total stall force doubled from 6500 N to 13000 N, so one motor gives 6500 N). With that change the actuator must hold at every load.

**How to run (PowerShell, from the repo folder):**
```
python -m pytest "tests/test_part_c_actuator_faults.py::test_r11_corrective_option_verified" -v
```
Expected output: `2 passed`.

**Initial condition:** as in TC-R11-S01, but on a private copy of the settings with doubled stall force.

**Cases** (from the `load_condition` fixture):

| Case | Load | Last result (2026-10-18) |
|---|---|---|
| `unloaded` | 0 N | PASS. Stall force after loss 6500 N, max deviation 0.0 mm, monitor did not trip (`None`). |
| `rated` | 4550 N | PASS. Stall force after loss 6500 N, max deviation 0.0 mm, monitor did not trip (`None`). |

**Steps:**

| Step | Action | Python command | Expected result | Line |
|---|---|---|---|---|
| 1 | Get the load name and value for this case | `name, load_n = load_condition` | Load set | 91 |
| 2 | Double the total stall force in the private copy of the settings (6500 N to 13000 N) | `fresh_cfg["actuator"]["stall_force_n"] *= 2` | Change applies to this test only | 92 |
| 3 | Record the load name | `record_property("load", name)` | Recorded | 93 |
| 4 | Run the same hold check as TC-R11-S01 on the changed settings | `r11_check(fresh_cfg, load_n, record_property)` | Check runs | 94 |
| 4a–4d | *(inside the run)* Same as TC-R11-S01 steps 2a–2d; after the loss one motor has 6500 N stall force, more than the 4550 N rated load | see TC-R11-S01 | | 33–48 |
| 5 | Find the max rod deviation from 1.0 s on, record values, check the hold | `dev <= spec["R11_hold_max_mm"]` | `True`: max deviation ≤ 0.50 mm (limit from `system_spec.R11_hold_max_mm`) | 54–59 |

**Pass criteria:** step 5 is `True` for both loads.

**Last result (2026-10-18):** PASS on both loads, 0.0 mm deviation.

---

## TC-R12-S01: Jam is detected and motor drive is removed

| Field | Value |
| --- | --- |
| Requirement | R12: The actuator monitor shall annunciate a jam within 0.30 s while the command is moving, remove motor drive, and not annunciate during normal operation (including rate-limited moves at rated load and all Part B fault cases). |
| Level | System (actuator model + tracking monitor in closed loop, monitor cuts the drive) |
| Test file | `tests/test_part_c_actuator_faults.py` |
| Test function | `test_r12_jam_detected_and_drive_removed` (lines 121–132, marks on lines 119–120); helper `jam_run` (lines 98–116) |

**Purpose:** command a 10 mm/s ramp, jam the screw at 0.5 s, and show the monitor annunciates within 0.30 s, the motor drive goes to zero, and the controller's integrator stops winding up. Run at three starting positions and both loads.

**How to run (PowerShell, from the repo folder):**
```
python -m pytest "tests/test_part_c_actuator_faults.py::test_r12_jam_detected_and_drive_removed" -v
```
Expected output: `6 passed`.

**Initial condition:** actuator at rest at the starting position, integrator pre-loaded for the load, no jam.

**Cases** (load from the `load_condition` fixture × start position from `@pytest.mark.parametrize("start_mm", ...)`, line 120):

| Case | Load | Start position | Last result (2026-10-18) |
|---|---|---|---|
| `unloaded-near-retract` | 0 N | -15.0 mm | PASS. Jam detected 0.171 s after the jam. |
| `unloaded-mid` | 0 N | -5.0 mm | PASS. 0.171 s. |
| `unloaded-near-extend` | 0 N | 5.0 mm | PASS. 0.171 s. |
| `rated-near-retract` | 4550 N | -15.0 mm | PASS. 0.171 s. |
| `rated-mid` | 4550 N | -5.0 mm | PASS. 0.171 s. |
| `rated-near-extend` | 4550 N | 5.0 mm | PASS. 0.171 s. |

**Steps:**

| Step | Action | Python command | Expected result | Line |
|---|---|---|---|---|
| 1 | Get the load and the limits | `name, load_n = load_condition` / `spec = cfg["system_spec"]` | Set | 122–123 |
| 2 | Run the jam scenario: ramp from the start position at 10 mm/s (`R12_cmd_rate_mm_s`), jam at 0.5 s, 1.5 s total | `t, _, _, demand, integ, mon = jam_run(cfg, load_n, start_mm=start_mm)` | Run completes | 124 (helper 98–116) |
| 2a | *(inside the run)* Build the actuator at the start position and the monitor; build the command ramp `start_mm + 10 × t` | `ema.reset(start_mm)` / `cmd = np.full(n, start_mm) if stationary else start_mm + rate * t` | Ramp ready | 102–107 |
| 2b | *(inside the run)* At the first step at or after 0.5 s, jam the screw. From then on the actuator does not move whatever the demand | `if t[k] >= t_jam and not ema.jammed:` / `ema.jam()` | Jammed | 110–111; sil/ema.py lines 69–71, 112–114 |
| 2c | *(inside the run)* Step the actuator each 1 ms | `x[k] = ema.step(cmd[k], DT)` | | 112 |
| 2d | *(inside the run)* Feed the monitor; the first time it reports tripped, cut the motor drive. After that the actuator sets demand to 0 and stops integrating | `if mon.update(t[k], cmd[k], ema.own_feedback) and not ema.drive_inhibited:` / `ema.inhibit_drive()` | Drive inhibited after the trip | 113–114; sil/ema.py lines 73–75, 105–109 |
| 2e | *(inside the run)* Save the motor demand and the integrator value each step | `demand[k], integ[k] = ema.last_demand, ema.s.integ` | Saved | 115 |
| 3 | Check the monitor tripped | `mon.tripped` | `True` (message "jam not annunciated" if not) | 125 |
| 4 | Work out the detection time from the jam | `latency = mon.trip_t - 0.5` | Number found | 126 |
| 5 | Pick the samples more than 10 ms after the trip. (The drive is cut after the actuator step on the trip tick, so the trip tick itself still has the old demand.) | `after = t > mon.trip_t + 0.01` | Samples picked | 127 |
| 6 | Record load and detection time | `record_property("jam_detect_s", round(latency, 3))` | Recorded | 128–129 |
| 7 | Check the detection time | `latency <= spec["R12_detect_max_s"]` | `True`: ≤ 0.30 s (limit from `system_spec.R12_detect_max_s`) | 130 |
| 8 | Check the motor drive is off | `np.all(demand[after] == 0.0)` | `True`: demand exactly 0 after the trip (message "motor drive not removed" if not) | 131 |
| 9 | Check the integrator stopped | `np.ptp(integ[after]) == 0.0` | `True`: integrator value does not change at all after the trip (message "controller still winding up after annunciation" if not) | 132 |

**Pass criteria:** steps 3, 7, 8 and 9 are all `True` in every case.

**Last result (2026-10-18):** PASS, all 6 cases. Detection 0.171 s in every case (limit 0.30 s).

---

## TC-R12-S02: Jam with a still command stays latent

| Field | Value |
| --- | --- |
| Requirement | R12 (as in TC-R12-S01) |
| Level | System (actuator model + tracking monitor in closed loop) |
| Test file | `tests/test_part_c_actuator_faults.py` |
| Test function | `test_r12_jam_with_stationary_command_is_latent` (lines 136–143, mark on line 135); helper `jam_run` (lines 98–116) |

**Purpose:** characterization, not a pass/fail on the design. A jam while the command is not moving cannot be seen by a tracking monitor: command and feedback stay equal, so there is no error. The jam stays latent until the next move. This test pins that behavior so nobody assumes otherwise (real systems add a periodic built-in test move).

**How to run (PowerShell, from the repo folder):**
```
python -m pytest "tests/test_part_c_actuator_faults.py::test_r12_jam_with_stationary_command_is_latent" -v
```
Expected output: `1 passed`.

**Initial condition:** actuator at rest at -5.0 mm (the `jam_run` default), rated load 4550 N.

**Steps:**

| Step | Action | Python command | Expected result | Line |
|---|---|---|---|---|
| 1 | Run the jam scenario at rated load with the command held still at -5.0 mm, jam at 0.5 s, 1.5 s total | `_, _, _, _, _, mon = jam_run(cfg, cfg["load_conditions"]["rated"], stationary=True)` | Run completes | 141 |
| 1a | *(inside the run)* The command is a flat -5.0 mm for the whole run | `cmd = np.full(n, start_mm) if stationary else ...` | Command does not move | 107 |
| 1b | *(inside the run)* Jam at 0.5 s, step the actuator, feed the monitor, cut drive if it trips; same as TC-R12-S01 steps 2b–2d | see TC-R12-S01 | | 109–115 |
| 2 | Record whether the monitor annunciated | `record_property("annunciated", mon.tripped)` | Recorded | 142 |
| 3 | Check the monitor did not trip | `not mon.tripped` | `True`: the jam is not seen | 143 |

**Pass criteria:** step 3 is `True`.

**Last result (2026-10-18):** PASS. Annunciated: `False`.

---

## TC-R12-S03: No false alarm on a rate-limited move at rated load

| Field | Value |
| --- | --- |
| Requirement | R12 (as in TC-R12-S01) |
| Level | System (actuator model + tracking monitor in closed loop) |
| Test file | `tests/test_part_c_actuator_faults.py` |
| Test function | `test_r12_no_false_alarm_on_rate_limited_move_at_rated_load` (lines 147–159, mark on line 146) |

**Purpose:** a big step at rated load leaves a big position error for about a second, but the actuator is moving at its rate limit, so the monitor must stay quiet.

**How to run (PowerShell, from the repo folder):**
```
python -m pytest "tests/test_part_c_actuator_faults.py::test_r12_no_false_alarm_on_rate_limited_move_at_rated_load" -v
```
Expected output: `1 passed`.

**Initial condition:** actuator at rest at -10.0 mm, rated load 4550 N, healthy.

**Steps:**

| Step | Action | Python command | Expected result | Line |
|---|---|---|---|---|
| 1 | Build the actuator at rated load and the monitor | `ema = make_ema(cfg, cfg["load_conditions"]["rated"])` / `mon = ActuatorMonitor.from_cfg(cfg["actuator_monitor"], DT)` | Built | 150–151 |
| 2 | Set the step size to 80 % of the 25 mm stroke | `span = 0.8 * ema.p.stroke_mm` | 20.0 mm | 152 |
| 3 | Build the command: -10 mm, then +10 mm from 0.05 s on, 3.0 s long. (`run_profile` also steps the actuator once through it; only the time and command arrays are kept.) | `t, cmd, _ = an.run_profile(ema, lambda ti: span / 2 if ti >= 0.05 else -span / 2, 3.0, -span / 2)` | Command ready | 153; sil/analysis.py lines 31–39 |
| 4 | Put the actuator back at rest at -10 mm | `ema.reset(-span / 2)` | Reset | 154 |
| 5 | Each 1 ms, step the actuator and feed the monitor. Observe only: no drive cut in this test | `ema.step(cmd[k], DT)` / `mon.update(t[k], cmd[k], ema.own_feedback)` | Run completes | 155–157 |
| 5a | *(inside the run)* The 20 mm extend is against the load, so the actuator runs at its loaded rate limit, 40 × (1 - 4550 / 6500) = 12 mm/s. The error is large but the speed is well above the 2.0 mm/s "not moving" limit, so "stuck" is never true | `lim_hi, lim_lo = self.v_max(1.0), -self.v_max(-1.0)` | No trip | sil/ema.py lines 82–90, 103; sil/actuator_monitor.py line 40 |
| 6 | Record the step size | `record_property("step_mm", span)` | Recorded | 158 |
| 7 | Check the monitor did not trip | `not mon.tripped` | `True` | 159 |

**Pass criteria:** step 7 is `True`.

**Last result (2026-10-18):** PASS. Step 20.0 mm, no trip.

---

## TC-R12-S04: No false alarm on a bandwidth sine

| Field | Value |
| --- | --- |
| Requirement | R12 (as in TC-R12-S01) |
| Level | System (actuator model + tracking monitor in closed loop) |
| Test file | `tests/test_part_c_actuator_faults.py` |
| Test function | `test_r12_no_false_alarm_on_bandwidth_sine` (lines 163–172, mark on line 162) |

**Purpose:** a ±1.0 mm sine at the 2.5 Hz bandwidth frequency is normal operation; the monitor must stay quiet.

**How to run (PowerShell, from the repo folder):**
```
python -m pytest "tests/test_part_c_actuator_faults.py::test_r12_no_false_alarm_on_bandwidth_sine" -v
```
Expected output: `1 passed`.

**Initial condition:** actuator at rest at 0 mm, unloaded (0 N), healthy.

**Steps:**

| Step | Action | Python command | Expected result | Line |
|---|---|---|---|---|
| 1 | Build the unloaded actuator and the monitor | `ema = make_ema(cfg)` / `mon = ActuatorMonitor.from_cfg(cfg["actuator_monitor"], DT)` | Built | 164–165 |
| 2 | Get the sine frequency from the Part A bandwidth limit | `f = cfg["actuator_spec"]["A4_bandwidth_min_hz"]` | 2.5 Hz (from `actuator_spec.A4_bandwidth_min_hz`) | 166 |
| 3 | Put the actuator at 0 mm | `ema.reset(0.0)` | Reset | 167 |
| 4 | For 4.0 s, each 1 ms: work out a 1.0 mm sine command, step the actuator, feed the monitor (observe only) | `c = 1.0 * math.sin(2 * math.pi * f * k * DT)` / `ema.step(c, DT)` / `mon.update(k * DT, c, ema.own_feedback)` | Run completes | 168–171 |
| 5 | Check the monitor did not trip | `not mon.tripped` | `True` | 172 |

**Pass criteria:** step 5 is `True`.

**Last result (2026-10-18):** PASS (no measured values recorded).

---

## TC-R12-S05: No false alarm across all Part B sensor faults

| Field | Value |
| --- | --- |
| Requirement | R12 (as in TC-R12-S01) |
| Level | System (full Part B loop via `run_scenario()`: sensors, ARINC 429, receivers, voter, command law, actuator, monitor) |
| Test file | `tests/test_part_c_actuator_faults.py` |
| Test function | `test_r12_no_false_alarm_across_part_b_faults` (lines 215–233, marks on lines 212–214); helpers `part_b_envelope` (lines 188–204), `worst_healthy_slow_error` (lines 175–185), `_envelope_fractions` (lines 207–209) |

**Purpose:** run every Part B sensor fault on every channel, maneuvering and steady, swept across load (the worst case is not at a corner). Sensor faults jerk the command around, but the actuator is healthy, so: no actuator alarm, and the 1.0 mm threshold must keep at least 0.25 mm of margin over the worst healthy case (FINDING-005 guard). Runs on the corrected actuator (RCA-001 anti-windup on), which the monitor needs.

**How to run (PowerShell, from the repo folder):**
```
python -m pytest "tests/test_part_c_actuator_faults.py::test_r12_no_false_alarm_across_part_b_faults" -v
```
Expected output: `4 passed`. Each case runs 48 full-system scenarios, about 2 s per case.

**Initial condition:** private copy of the settings with `anti_windup` on; each scenario starts in balance at the healthy commanded position.

**Cases** (load fractions from `actuator_monitor.envelope_load_fractions` = [0.0, 0.5, 0.75, 1.0], read at collection time by `_envelope_fractions()`, lines 207–209):

| Case | Load | Scenarios | False alarms | Worst healthy error | Worst case | Margin | Last result (2026-10-18) |
|---|---|---|---|---|---|---|---|
| `0pct_rated` | 0 N | 48 | 0 | 0.659 mm | frozen-chB-maneuver | 0.341 mm | PASS |
| `50pct_rated` | 2275 N | 48 | 0 | 0.659 mm | frozen-chB-maneuver | 0.341 mm | PASS |
| `75pct_rated` | 3412 N (recorded rounded; 3412.5 N used) | 48 | 0 | 0.659 mm | frozen-chB-maneuver | 0.341 mm | PASS |
| `100pct_rated` | 4550 N | 48 | 0 | 0.659 mm | frozen-chB-maneuver | 0.341 mm | PASS |

**Steps:**

| Step | Action | Python command | Expected result | Line |
|---|---|---|---|---|
| 1 | Turn on the RCA-001 anti-windup fix in the private copy of the settings | `fresh_cfg["actuator"]["anti_windup"] = True` | Change applies to this test only | 221 |
| 2 | Get the monitor settings and work out the load for this case | `mon_cfg = fresh_cfg["actuator_monitor"]` / `load = load_frac * fresh_cfg["load_conditions"]["rated"]` | Load = fraction × 4550 N | 222–223 |
| 3 | Run the fault sweep at this load | `tripped, worst, worst_case = part_b_envelope(fresh_cfg, load)` | Sweep completes | 224 (helper 188–204) |
| 3a | *(inside the sweep)* Loop over the 8 Part B fault kinds (frozen, drift, bias_jump, spike, bad_parity, ssm_fail, dropout, out_of_range, with their magnitudes from `FAULTS` in tests/test_part_b_system.py lines 24–33) × channels A, B, C × two pitch profiles: "maneuver" (-2° ± 3° sine at 0.3 Hz) and "steady" (-2°) | `for kind, (mag, _, _) in FAULTS.items():` ... `for pname, pfn in (("maneuver", maneuver), ("steady", lambda t: -2.0)):` | 48 scenarios | 193–195 |
| 3b | *(inside the sweep)* Run the whole system for 3.0 s at this load with the fault on pitch starting at 0.5 s | `run = run_scenario(cfg, duration_s=3.0, pitch_fn=pfn, load_n=load_n, faults=[Fault(kind, ch, "pitch", t_start=0.5, magnitude=mag)])` | Run completes | 196–197 |
| 3c | *(inside each run)* The faulty channel sends bad pitch words from 0.5 s; the receivers and mid-value voter handle it; the command law turns the voted pitch into an actuator command every 20 ms; the actuator steps every 1 ms | `ch.transmit(...)` / `voters["pitch"].update(...)` / `law.update(...)` / `ema.step(cur_cmd, DT)` | Command reacts to the sensor fault | sil/sources.py lines 85–104; sil/sim.py lines 129–146 |
| 3d | *(inside each run)* The tracking monitor runs alongside, observe only (no drive cut). If it trips, `ACT_NOT_TRACKING` is added to the run's annunciations | `if mon is not None and mon.update(tk, cur_cmd, fb[k]):` / `ann.add("ACT_NOT_TRACKING")` | Not added | sil/sim.py lines 114–116, 147–148 |
| 3e | *(inside the sweep)* If the run annunciated `ACT_NOT_TRACKING`, add its tag (e.g. `frozen-chB-maneuver`) to the false-alarm list | `if "ACT_NOT_TRACKING" in run.annunciations:` / `tripped.append(tag)` | | 198–200 |
| 3f | *(inside the sweep)* Work out the largest threshold this run would have tripped: over every 0.10 s window, take the smallest command-vs-feedback error while the actuator is "not moving" (under 2.0 mm/s over 0.02 s); keep the largest of those. Keep the worst over all runs | `w = worst_healthy_slow_error(run, mon_cfg)` | Worst healthy error and its case kept | 201–203 (helper 175–185) |
| 4 | Work out the margin | `margin = mon_cfg["err_threshold_mm"] - worst` | 1.0 mm minus worst healthy error | 225 |
| 5 | Record load, number of scenarios, false alarms, worst healthy error, worst case, margin | `record_property("load_n", round(load))` ... `record_property("margin_mm", round(margin, 3))` | Recorded | 226–231 |
| 6 | Check there were no false alarms | `not tripped` | `True`: list is empty (the list is printed if not) | 232 |
| 7 | Check the margin | `margin >= mon_cfg["margin_min_mm"]` | `True`: margin ≥ 0.25 mm (limit from `actuator_monitor.margin_min_mm`; threshold 1.0 mm from `actuator_monitor.err_threshold_mm`) | 233 |

**Pass criteria:** steps 6 and 7 are `True` in every case.

**Last result (2026-10-18):** PASS, all 4 loads. 0 false alarms in 48 scenarios at each load; worst healthy error 0.659 mm (frozen-chB-maneuver), margin 0.341 mm.

---

## TC-R12-S06: Baseline actuator gives false alarms (open defect)

| Field | Value |
| --- | --- |
| Requirement | R12 (as in TC-R12-S01) |
| Level | System (full Part B loop via `run_scenario()`) |
| Test file | `tests/test_part_c_actuator_faults.py` |
| Test function | `test_r12_no_false_alarm_baseline_actuator` (lines 239–248, marks on lines 236–238); helper `part_b_envelope` (lines 188–204) |

**Purpose:** the same false-alarm check as TC-R12-S05, but on the **baseline** actuator (windup still in, `anti_windup: false`) at the worst load found in the sweep, 75 % of rated. Kept as a strict expected failure: it closes when the RCA-001 fix is adopted.

**How to run (PowerShell, from the repo folder):**
```
python -m pytest "tests/test_part_c_actuator_faults.py::test_r12_no_false_alarm_baseline_actuator" -v
```
Expected output: `1 xfailed`.

**Initial condition:** baseline settings (shared `cfg`, not changed); each scenario starts in balance.

**Steps:**

| Step | Action | Python command | Expected result | Line |
|---|---|---|---|---|
| 1 | Set the load to 75 % of rated | `load = 0.75 * cfg["load_conditions"]["rated"]` | 3412.5 N | 242 |
| 2 | Run the fault sweep at this load on the baseline actuator | `tripped, worst, worst_case = part_b_envelope(cfg, load)` | Sweep completes | 243 |
| 2a–2f | *(inside the sweep)* Same as TC-R12-S05 steps 3a–3f: 48 full-system scenarios, monitor observe only. On the baseline actuator the integrator keeps winding up while the actuator is rate-limited (sil/ema.py lines 105–106), so it overshoots the command and creeps back slowly: big error, low speed, looks stuck | see TC-R12-S05 | | 188–204 |
| 3 | Record load, false alarms, worst healthy error, worst case | `record_property("load_n", round(load))` ... | Recorded | 244–247 |
| 4 | Check there were no false alarms | `not tripped` | `True` would mean no false alarms. Expected today: `False` (strict xfail) | 248 |

**Pass criteria:** marked `xfail(strict=True)`. The test is reported as "xfailed" when step 4 is `False`. If step 4 becomes `True` the run fails as "XPASS", which signals the finding should be closed.

**Last result (2026-10-18):** OPEN DEFECT (expected fail, FINDING-005): "FINDING-005: monitor needs the RCA-001 anti-windup fix; baseline windup gives false jam alarms". Load 3412 N, 2 false alarms, worst healthy error 4.895 mm (drift-chA-maneuver). See docs/rca/FINDING-005-jam-monitor-false-alarm.md.

---

## TC-R13-S01: Healthy lanes share load with equalization

| Field | Value |
| --- | --- |
| Requirement | R13: With three lanes active on one surface, equalization shall keep force fight between healthy lanes ≤ 500 N; a faulty lane shall be disengaged (only that lane) with surface error ≤ 0.25 mm after; a lane fault too small to detect shall cause ≤ 0.60 mm surface error. |
| Level | System (three-lane force-fight model, `sil/force_fight.py`) |
| Test file | `tests/test_part_c_actuator_faults.py` |
| Test function | `test_r13_healthy_lanes_share_load_with_equalization` (lines 259–265, mark on line 258) |

**Purpose:** three healthy lanes with worst-case rigging offsets (+0.2, 0.0, -0.2 mm) hold one surface against rated load for 10 s. With force equalization on, the force fight must stay at or under 500 N and no lane is disengaged.

**How to run (PowerShell, from the repo folder):**
```
python -m pytest "tests/test_part_c_actuator_faults.py::test_r13_healthy_lanes_share_load_with_equalization" -v
```
Expected output: `1 passed`.

**Initial condition:** surface at 0 mm, at rest; each lane's integrator pre-loaded to carry one third of the 4550 N load; all three lanes engaged.

**Steps:**

| Step | Action | Python command | Expected result | Line |
|---|---|---|---|---|
| 1 | Build the force-fight settings from config (equalization gain 0.001 mm/N, monitor 1000 N for 0.20 s) | `p = ff_params(cfg)` | Built | 260 |
| 2 | Hold the surface at 0 mm for 10.0 s with the rigging offsets, no fault | `r = run_force_fight(p, rig_offsets_mm=cfg["force_fight"]["rig_offsets_mm"], duration_s=10.0)` | Run completes | 261 |
| 2a | *(inside the run)* Every 0.5 ms each lane reads its own sensor (surface position + its offset) and works out a PI-plus-damping force, clipped to ±6500 N | `err = cmd_mm - (x + offs)` / `f = np.where(engaged, np.clip(raw, ...), 0.0)` | | sil/force_fight.py lines 82–84 |
| 2b | *(inside the run)* Force fight for each lane = its force minus the mean of the other engaged lanes | `fight[i] = f[i] - f[others].mean()` | | sil/force_fight.py lines 86–91 |
| 2c | *(inside the run)* Equalization: each lane's integrator is bled toward the others by 0.001 mm per N of fight (no integration while saturated) | `integ[i] += dt * (err[i] - p.eq_gain_mm_per_n * fight[i])` | Lanes share the load | sil/force_fight.py lines 93–95 |
| 2d | *(inside the run)* Force-fight monitor (only while all three lanes are engaged): a lane over 1000 N of fight for 0.20 s is disengaged; only the largest outlier | `if len(idx) == 3:` ... | No lane disengaged | sil/force_fight.py lines 97–108 |
| 2e | *(inside the run)* Surface moves under the sum of lane forces minus the load | `a = 1000.0 * (f.sum() - p.load_n) / p.surface_mass_kg` | | sil/force_fight.py line 110 |
| 3 | Find the largest force fight on any lane over the whole run | `fight = r.max_fight()` | Number found | 262 |
| 4 | Record it | `record_property("max_fight_n", round(fight))` | Recorded | 263 |
| 5 | Check the force fight | `fight <= cfg["system_spec"]["R13_fight_max_n"]` | `True`: ≤ 500 N (limit from `system_spec.R13_fight_max_n`) | 264 |
| 6 | Check no lane was disengaged | `not r.disengaged` | `True`: disengage list empty | 265 |

**Pass criteria:** steps 5 and 6 are `True`.

**Last result (2026-10-18):** PASS. Max force fight 300 N.

---

## TC-R13-S02: Without equalization healthy lanes fight and trip

| Field | Value |
| --- | --- |
| Requirement | R13 (as in TC-R13-S01) |
| Level | System (three-lane force-fight model, `sil/force_fight.py`) |
| Test file | `tests/test_part_c_actuator_faults.py` |
| Test function | `test_r13_without_equalization_healthy_lanes_fight_and_trip` (lines 269–278, mark on line 268) |

**Purpose:** show why equalization is required. With integrators and no equalization, two healthy lanes inside tolerance wind up against each other until the monitor disengages a lane that has nothing wrong with it. This test expects that bad outcome.

**How to run (PowerShell, from the repo folder):**
```
python -m pytest "tests/test_part_c_actuator_faults.py::test_r13_without_equalization_healthy_lanes_fight_and_trip" -v
```
Expected output: `1 passed`.

**Initial condition:** as in TC-R13-S01.

**Steps:**

| Step | Action | Python command | Expected result | Line |
|---|---|---|---|---|
| 1 | Build the force-fight settings with equalization turned off | `p = ff_params(cfg, eq_gain_mm_per_n=0.0)` | Equalization gain 0 | 273 |
| 2 | Hold the surface at 0 mm for 10.0 s with the rigging offsets, no fault | `r = run_force_fight(p, rig_offsets_mm=cfg["force_fight"]["rig_offsets_mm"], duration_s=10.0)` | Run completes | 274 |
| 2a | *(inside the run)* Same as TC-R13-S01 steps 2a–2e, but in step 2c the equalization term is zero, so each lane integrates its own offset error and the lanes wind up against each other | `integ[i] += dt * (err[i] - p.eq_gain_mm_per_n * fight[i])` | Fight grows; monitor disengages a lane | sil/force_fight.py lines 93–108 |
| 3 | Record the max fight and which lane was disengaged, and when | `record_property("max_fight_n", round(r.max_fight()))` / `record_property("healthy_lane_disengaged_at_s", ...)` | Recorded | 275–276 |
| 4 | Check the fight went over the limit | `r.max_fight() > cfg["system_spec"]["R13_fight_max_n"]` | `True`: more than 500 N (limit from `system_spec.R13_fight_max_n`) | 277 |
| 5 | Check a healthy lane was disengaged | `r.disengaged` | `True`: disengage list not empty (message "expected a false disengage without equalization" if empty) | 278 |

**Pass criteria:** steps 4 and 5 are `True`.

**Last result (2026-10-18):** PASS. Max force fight 8454 N; lane 0 (A) disengaged at 0.67 s.

---

## TC-R13-S03: Faulty lane is disengaged, and only that lane

| Field | Value |
| --- | --- |
| Requirement | R13 (as in TC-R13-S01) |
| Level | System (three-lane force-fight model, `sil/force_fight.py`) |
| Test file | `tests/test_part_c_actuator_faults.py` |
| Test function | `test_r13_faulty_lane_disengaged` (lines 287–296, marks on lines 284–286); case list `FF_CASES` (line 281) |

**Purpose:** at 1.0 s, one lane's sensor offset jumps by a large amount (a sensor or rigging fault). The monitor must disengage that lane and only that lane, and the surface must end within 0.25 mm of the command.

**How to run (PowerShell, from the repo folder):**
```
python -m pytest "tests/test_part_c_actuator_faults.py::test_r13_faulty_lane_disengaged" -v
```
Expected output: `15 passed`.

**Initial condition:** as in TC-R13-S01.

**Cases** (3 lanes × offsets +2, -2, +5, -5, +10 mm from `FF_CASES`, line 281). "Disengaged" is the lane index and time after the fault (lane 0 = A, 1 = B, 2 = C):

| Case | Lane | Offset | Disengaged | Peak surface (from 1.0 s) | Final surface | Last result (2026-10-18) |
|---|---|---|---|---|---|---|
| `laneA+2mm` | A | +2.0 mm | lane 0 at 0.2 s | 0.83 mm | 0.1 mm | PASS |
| `laneA-2mm` | A | -2.0 mm | lane 0 at 0.2 s | 0.74 mm | 0.1 mm | PASS |
| `laneA+5mm` | A | +5.0 mm | lane 0 at 0.2 s | 1.85 mm | 0.1 mm | PASS |
| `laneA-5mm` | A | -5.0 mm | lane 0 at 0.2 s | 1.85 mm | 0.1 mm | PASS |
| `laneA+10mm` | A | +10.0 mm | lane 0 at 0.2 s | 3.69 mm | 0.1 mm | PASS |
| `laneB+2mm` | B | +2.0 mm | lane 1 at 0.2 s | 0.9 mm | -0.0 mm | PASS |
| `laneB-2mm` | B | -2.0 mm | lane 1 at 0.2 s | 0.74 mm | -0.0 mm | PASS |
| `laneB+5mm` | B | +5.0 mm | lane 1 at 0.2 s | 1.85 mm | -0.0 mm | PASS |
| `laneB-5mm` | B | -5.0 mm | lane 1 at 0.2 s | 1.85 mm | -0.0 mm | PASS |
| `laneB+10mm` | B | +10.0 mm | lane 1 at 0.2 s | 3.69 mm | -0.0 mm | PASS |
| `laneC+2mm` | C | +2.0 mm | lane 2 at 0.2 s | 0.98 mm | -0.1 mm | PASS |
| `laneC-2mm` | C | -2.0 mm | lane 2 at 0.2 s | 0.82 mm | -0.1 mm | PASS |
| `laneC+5mm` | C | +5.0 mm | lane 2 at 0.2 s | 1.85 mm | -0.1 mm | PASS |
| `laneC-5mm` | C | -5.0 mm | lane 2 at 0.2 s | 1.85 mm | -0.1 mm | PASS |
| `laneC+10mm` | C | +10.0 mm | lane 2 at 0.2 s | 3.69 mm | -0.1 mm | PASS |

**Steps:**

| Step | Action | Python command | Expected result | Line |
|---|---|---|---|---|
| 1 | Get the limits and build the force-fight settings from config | `spec = cfg["system_spec"]` / `p = ff_params(cfg)` | Built | 288–289 |
| 2 | Hold the surface at 0 mm for 4.0 s; at 1.0 s add the case offset to the case lane's sensor | `r = run_force_fight(p, rig_offsets_mm=..., duration_s=4.0, fault_lane=lane, fault_offset_mm=offset_mm, fault_t=1.0)` | Run completes | 290–291 |
| 2a | *(inside the run)* From 1.0 s the faulty lane sees a wrong position and pushes against the other two | `offs[fault_lane] += fault_offset_mm` | Fight on the faulty lane grows | sil/force_fight.py lines 80–81 |
| 2b | *(inside the run)* Once a lane has been over 1000 N of fight for 0.20 s, the monitor disengages only the lane with the largest fight (`isolate_largest_only: true`), sets its force to zero, and stops monitoring (it needs three lanes to pick an outlier) | `ready = [max(ready, key=lambda i: abs(fight[i]))]` / `engaged[i] = False` | Faulty lane disengaged | sil/force_fight.py lines 97–108 |
| 2c | *(inside the run)* The two healthy lanes carry the load and bring the surface back | | Surface settles | sil/force_fight.py lines 110–112 |
| 3 | Record which lanes were disengaged and when (from 1.0 s), the peak surface position from 1.0 s, and the final position | `record_property("disengaged", ...)` / `record_property("peak_surface_mm", round(r.max_abs_x(1.0), 2))` / `record_property("final_surface_mm", round(float(r.x[-1]), 3))` | Recorded | 292–294 |
| 4 | Check only the faulty lane was disengaged | `list(r.disengaged) == [lane]` | `True` (message "wrong lane(s) disengaged" if not) | 295 |
| 5 | Check the final surface position | `abs(r.x[-1]) <= spec["R13_final_err_max_mm"]` | `True`: within 0.25 mm of 0 at 4.0 s (limit from `system_spec.R13_final_err_max_mm`) | 296 |

**Pass criteria:** steps 4 and 5 are `True` in every case.

**Last result (2026-10-18):** PASS, all 15 cases. The right lane every time, 0.2 s after the fault; final surface within 0.1 mm. Peak surface movement before disengage reached 3.69 mm on the 10 mm cases (no limit is checked on the peak; see the open item in FINDING-004).

---

## TC-R13-S04: Undetected lane fault stays small

| Field | Value |
| --- | --- |
| Requirement | R13 (as in TC-R13-S01) |
| Level | System (three-lane force-fight model, `sil/force_fight.py`) |
| Test file | `tests/test_part_c_actuator_faults.py` |
| Test function | `test_r13_undetected_lane_fault_stays_small` (lines 301–314, marks on lines 299–300) |

**Purpose:** below the monitor threshold, the other two lanes outvote the bad one, so the surface moves by about a third of the offset. A lane fault too small to detect must not move the surface more than 0.60 mm. Each offset is tried on every lane and the worst undetected result is kept.

**How to run (PowerShell, from the repo folder):**
```
python -m pytest "tests/test_part_c_actuator_faults.py::test_r13_undetected_lane_fault_stays_small" -v
```
Expected output: `6 passed`.

**Initial condition:** as in TC-R13-S01.

**Cases** (from `@pytest.mark.parametrize("offset_mm", ...)`, line 300; each case runs lanes A, B and C):

| Case | Offset | Worst undetected final surface | Last result (2026-10-18) |
|---|---|---|---|
| `0.5` | +0.5 mm | 0.167 mm | PASS |
| `1.0` | +1.0 mm | 0.333 mm | PASS |
| `1.5` | +1.5 mm | 0.5 mm | PASS |
| `-1.5` | -1.5 mm | 0.5 mm | PASS |
| `1.6` | +1.6 mm | 0.533 mm | PASS |
| `-1.6` | -1.6 mm | 0.533 mm | PASS |

**Steps:**

| Step | Action | Python command | Expected result | Line |
|---|---|---|---|---|
| 1 | Build the force-fight settings and start the worst value at 0 | `p = ff_params(cfg)` / `worst = 0.0` | Set | 304–305 |
| 2 | For each lane A, B, C: hold 0 mm for 4.0 s, add the case offset to that lane's sensor at 1.0 s | `r = run_force_fight(p, rig_offsets_mm=..., duration_s=4.0, fault_lane=lane, fault_offset_mm=offset_mm, fault_t=1.0)` | 3 runs complete | 306–308 |
| 2a | *(inside each run)* Same as TC-R13-S03 steps 2a–2c; with a small offset the fight may stay under 1000 N and no lane is disengaged | | | sil/force_fight.py lines 80–112 |
| 3 | If no lane was disengaged, keep the largest final surface position so far | `if not r.disengaged:` / `worst = max(worst, abs(float(r.x[-1])))` | Worst updated | 309–310 |
| 4 | If a lane was disengaged, check it was the faulty one | `list(r.disengaged) == [lane]` | `True` | 311–312 |
| 5 | Record the worst undetected surface position | `record_property("worst_undetected_surface_mm", round(worst, 3))` | Recorded | 313 |
| 6 | Check the worst undetected surface position | `worst <= cfg["system_spec"]["R13_undetected_err_max_mm"]` | `True`: ≤ 0.60 mm (limit from `system_spec.R13_undetected_err_max_mm`) | 314 |

**Pass criteria:** step 4 (when it applies) and step 6 are `True` in every case.

**Last result (2026-10-18):** PASS, all 6 cases. Worst 0.533 mm at ±1.6 mm offset (limit 0.60 mm). Which lanes, if any, were disengaged is not recorded.

---

## TC-R13-S05: Guard test for FINDING-004 drops only the largest outlier

| Field | Value |
| --- | --- |
| Requirement | R13 (as in TC-R13-S01) |
| Level | System (three-lane force-fight model, `sil/force_fight.py`) |
| Test file | `tests/test_part_c_actuator_faults.py` |
| Test function | `test_r13_guard_monitor_isolates_only_the_largest_outlier` (lines 318–331, mark on line 317) |

**Purpose:** FINDING-004 regression guard. The first monitor version disengaged every lane over the threshold. On a large fault all three lanes cross together and all three were dropped, so the surface was lost. The test re-runs the old logic to prove the guard still catches it, then checks the fixed logic drops only the faulty lane.

**How to run (PowerShell, from the repo folder):**
```
python -m pytest "tests/test_part_c_actuator_faults.py::test_r13_guard_monitor_isolates_only_the_largest_outlier" -v
```
Expected output: `1 passed`.

**Initial condition:** as in TC-R13-S01.

**Steps:**

| Step | Action | Python command | Expected result | Line |
|---|---|---|---|---|
| 1 | Build the settings with the OLD monitor logic (disengage every lane over threshold) | `old = ff_params(cfg, isolate_largest_only=False)` | Old logic | 323 |
| 2 | Hold 0 mm for 3.0 s; at 1.0 s add +5.0 mm to lane A's sensor | `r_old = run_force_fight(old, rig_offsets_mm=..., duration_s=3.0, fault_lane=0, fault_offset_mm=5.0, fault_t=1.0)` | Run completes | 324–325 |
| 2a | *(inside the run)* The 5 mm fault on lane A pulls the healthy lanes' fight over 1000 N too; all three timers reach 0.20 s together and the old logic disengages every lane on the list | `for i in ready:` / `engaged[i] = False` | All three disengaged | sil/force_fight.py lines 101–107 |
| 3 | Record how many lanes the old logic dropped | `record_property("old_logic_lanes_disengaged", len(r_old.disengaged))` | Recorded | 326 |
| 4 | Check the defect is reproduced | `len(r_old.disengaged) == 3` | `True`: all three lanes dropped | 327 |
| 5 | Build the settings with the FIXED logic from config (`isolate_largest_only: true`) | `new = ff_params(cfg)` | Fixed logic | 328 |
| 6 | Run the same fault again | `r_new = run_force_fight(new, rig_offsets_mm=..., duration_s=3.0, fault_lane=0, fault_offset_mm=5.0, fault_t=1.0)` | Run completes | 329–330 |
| 6a | *(inside the run)* Only the lane with the largest fight is disengaged | `ready = [max(ready, key=lambda i: abs(fight[i]))]` | Lane A disengaged | sil/force_fight.py lines 103–104 |
| 7 | Check only lane A was disengaged | `list(r_new.disengaged) == [0]` | `True` | 331 |

**Pass criteria:** steps 4 and 7 are `True`.

**Last result (2026-10-18):** PASS. Old logic dropped 3 lanes (defect reproduced). The fixed-logic result is checked but not recorded.
