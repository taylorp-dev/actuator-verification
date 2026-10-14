# Actuator Verification SIL

[![SIL regression](https://github.com/taylorp-dev/actuator-verification/actions/workflows/ci.yml/badge.svg)](https://github.com/taylorp-dev/actuator-verification/actions/workflows/ci.yml)

EMA characterization and triplex ARINC 429 sensor fault response, in a Python/pytest software-in-the-loop.

> Simplified plant, representative numbers. The point is the **test method**, not the actuator model or anyone's real architecture.

## What it does

```
 3 x attitude sources --ARINC 429--> receivers --> mid-value voter --> attitude-hold --> EMA --> rod position
   (bias, noise,          (parity, SSM,           (miscompare +        command law      (PI loop,     (independent
    fault injection)       staleness, range)        persistence)        (limits R10)     rate limit,    truth sensor)
                                                                                         load, backlash)
         ^                                                                                                  |
         +------------------------------ pytest: fixtures, fault matrix, req markers -----------------------+
```

- **Part A, actuator acceptance (A1-A5):** step response, max rate, accuracy and backlash, bandwidth, performance at rated load. Measured at the output rod, never the unit's own feedback.
- **Part B, system fault response (ICD-1, R1-R10):** receiver validity checks, voter isolation, then the effect of each fault at the actuator.

## Results (current baseline)

- 16/16 requirements traced, 70 tests, full suite ~3 s
- **RCA-001:** R9 reconfiguration transient passes unloaded, **fails at rated load** (integrator windup during rate saturation). The actuator passes all its own acceptance tests. Corrective action (anti-windup) verified in the SIL.
- **FINDING-002:** first fault-matrix run isolated the **wrong** channel. Threshold had zero margin over the sensor tolerance stack. Fixed, guarded by a test.

## Test evidence

| What | Where |
| --- | --- |
| Requirements traceability matrix (every requirement, its tests, verdict, measured values, commit + config fingerprint) | [reports/traceability.md](reports/traceability.md) |
| Full test run log (every test name and result) | [reports/test_log.txt](reports/test_log.txt) |
| Requirements, full text | [requirements/requirements.yaml](requirements/requirements.yaml) |
| Test cases: actuator acceptance (A1-A5) | [tests/test_part_a_actuator.py](tests/test_part_a_actuator.py) |
| Test cases: ARINC 429 receiver (ICD-1, R1-R4) | [tests/test_part_b_receiver.py](tests/test_part_b_receiver.py) |
| Test cases: voter (R5-R8) | [tests/test_part_b_voter.py](tests/test_part_b_voter.py) |
| Test cases: fault matrix and system level (R9, R10) | [tests/test_part_b_system.py](tests/test_part_b_system.py) |
| Written test procedure (bandwidth) | [docs/procedures/TP-A4-bandwidth.md](docs/procedures/TP-A4-bandwidth.md) |
| RCA-001: loaded reconfiguration transient | [docs/rca/RCA-001-reconfig-transient-under-load.md](docs/rca/RCA-001-reconfig-transient-under-load.md) |
| FINDING-002: wrong channel isolated | [docs/rca/FINDING-002-wrong-channel-isolated.md](docs/rca/FINDING-002-wrong-channel-isolated.md) |
| Figures | [reports/figures/](reports/figures/) |
| Configuration under control (all parameters and limits) | [config/sil.yaml](config/sil.yaml) |
| Automated runs on GitHub (fresh run on every push, full logs, downloadable reports) | [Actions tab](https://github.com/taylorp-dev/actuator-verification/actions) |

## Run it

New to Python or the terminal? Start with **[docs/USER-GUIDE.md](docs/USER-GUIDE.md)**: setup, running, reading results, experiments, troubleshooting.


```bash
pip install -r requirements.txt
python tools/run_tests.py        # tests + reports/test_log.txt + reports/traceability.md
python -m pytest                 # same tests, no saved log
python tools/make_figures.py     # reports/figures/*.png
```

## Layout

| Path | What |
| --- | --- |
| `sil/` | EMA model, ARINC 429 encode/decode, sources + faults, receiver, voter, command law, closed-loop sim |
| `config/sil.yaml` | All parameters and limits, under version control; its hash is stamped on every report |
| `requirements/requirements.yaml` | Requirement text, source for the traceability matrix |
| `tests/` | Part A and Part B suites; `conftest.py` holds fixtures and the traceability hook |
| `docs/USER-GUIDE.md` | Step-by-step setup, running, experiments, troubleshooting |
| `docs/procedures/` | Written test procedure (TP-A4) |
| `docs/rca/` | RCA-001 and FINDING-002 |
| `tools/make_figures.py` | Presentation figures from the same code the tests run |
| `.github/workflows/ci.yml` | Runs the suite on every push, publishes the matrix and report artifact |

## Framework design

- **Fixtures** give each test a fresh, known configuration (config control in code). `load_condition` runs a test once per load.
- **Parametrize** drives the fault matrix: 8 fault types x 3 channels.
- **`@pytest.mark.req("R6")`** tags each test; a hook builds the traceability matrix with git commit, config hash, and measured values.
- **Strict xfail** keeps a known open defect in regression, tied to its RCA.

## How it was built

Designed, directed, and verified by Taylor Park. Built with AI coding assistance (Claude) for much of the code. Every finding was reproduced, and every result in this repo comes from the tests here.

## Next steps

Real bus hardware (bus-in-the-loop), RS-422 actuator command link and CAN health bus as plug-ins, actuator HIL on a load stand, dissimilar sensors, second-fault and common-mode cases, a second airframe ICD.
