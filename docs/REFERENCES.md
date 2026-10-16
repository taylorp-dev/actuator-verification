# References

Public sources used to size and scope this project, and what each one informed. Nothing here comes from non-public material. This project does not model any company's actual actuator or architecture.

## Actuator force class and architecture (Skyryse, public)

| Source | What it informed |
| --- | --- |
| [SkyOS – Skyryse](https://skyryse.com/skyos) | Force class for the flight-class actuator: triply redundant electric actuators, over 1,000 lbf, jam-tolerant. Stall force and rated load in `config/sil.yaml` are sized to this class (rated 4,550 N, about 1,020 lbf). |
| [Patents assigned to Skyryse (Justia)](https://patents.justia.com/assignee/skyryse-inc) | Actuator-internal redundancy (multiple motors on one screw, dual nuts) behind Part C: motor channel loss (R11) and jam (R12). Voter patents for context on fully analyzable voting. |
| [Lead Motor Control Engineer (Built In)](https://builtin.com/job/lead-motor-control-engineer/3716726) | Context: field-oriented control, encoders, actuator modeling, frequency-domain work, HIL (dSpace), DO-178C / DO-331. Supports a frequency-response test (A4) and a model-plus-HIL approach. |
| [Mechanical Engineer, Actuators & Controls (Built In)](https://builtin.com/job/mechanical-design-engineer-integration/2255860) | Context: ballscrews, gears, potentiometers, LVDTs/RVDTs. Supports the independent rod position (truth) sensor. |
| [Senior Mechanical Engineer, Mechanisms (Built In)](https://builtin.com/job/mechanical-engineer-mechanisms/6987594) | Context: vibration, fatigue and shock testing, root cause analysis. |
| [Skyryse raises $300M+ (Raptor Group)](https://www.raptorgroup.com/news/skyryse-raises-300m-for-its-ai-flight-control-system/) | Context: linear electromechanical actuators plus a motor control assembly. |
| [FAA special conditions, Federal Register (PDF)](https://public-inspection.federalregister.gov/2025-20611.pdf) | Context: four-axis full-authority digital fly-by-wire on a certified rotorcraft. |
| [FAA proposes special conditions for Skyryse's fly-by-wire R66 (AIN)](https://backend.ainonline.com/aviation-news/futureflight/2026-08-28/faa-proposes-special-conditions-skyryses-fly-wire-r66) | Context: crew awareness of control-authority limits. Relevant to annunciation requirements (R11, R12). |

## Force fight and equalization (R13)

| Source | What it informed |
| --- | --- |
| [US 11,745,858 B2, "Managing force equalization via force-fight cycle detection" (Bell / Textron)](https://patents.google.com/patent/US11745858) | Monitor design: compare each actuator's force to the mean of the others, threshold plus persistence, then disengage. The patent counts fight cycles; this project uses a simpler threshold-and-persistence monitor. |
| [Kowalski et al., "Force Fight Compensation for Redundant Electro-Mechanical Flight Control Actuators," ICAS 2018 (DLR / Liebherr)](https://www.icas.org/icas_archive/ICAS2018/data/papers/ICAS2018_0271_paper.pdf) | Electric actuators running active/active on one surface need force-fight compensation. |
| [Li, Lin, Tian, "Force fighting equalisation for aircraft rudder's triple active actuation system," Aeronautical Journal, 2022](https://cambridge.org/core/journals/aeronautical-journal/article/abs/research-and-modeling-of-force-fighting-equalisation-for-aircraft-rudders-triple-active-actuation-system/F9555CCC8F849A2DE75379BF32FD5BE9) | Triple-active actuation on one surface, equalization to minimize fight force. |
| [Hall et al., "Investigating Actuation Force Fight with Asynchronous and Synchronous Redundancy Management Techniques" (Honeywell / SRI for NASA)](https://ntrs.nasa.gov/archive/nasa/casi.ntrs.nasa.gov/20130012913.pdf) | Force fight from timing and command disagreement between redundant channels. |
| [Progress in Redundant Electromechanical Actuators for Aerospace Applications (review)](https://www.open-access.bcu.ac.uk/14809) | Background on redundant EMA architectures (torque-summed and force-summed). |

## Bench actuator (model correlation, M1)

| Source | What it informed |
| --- | --- |
| [Actuonix L16 datasheet (PDF)](https://cdn.robotshop.com/media/F/Fir/RB-Fir-111/pdf/ActuonixL16Datasheet.pdf) | L16-P profile, 35:1 gear: 32 mm/s no load, 50 N @ 16 mm/s, 24 N @ 24 mm/s, 0.25 mm backlash, 0.3 mm repeatability, pot linearity < 2 %, 12 V. |
| [Actuonix L16-P 100 mm 35:1 12 V (RobotShop)](https://www.robotshop.com/products/actuonix-l16-linear-actuator-100mm-351-12v-w-potentiometer-feedback) | Part selected for the desk rig. |
