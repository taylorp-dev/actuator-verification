# Requirements Traceability Matrix

- Generated: 2026-10-16T21:01:35+00:00
- Git commit: `c92fb10-dirty`
- Config: `config/sil.yaml` (sha256 `761c1ae3c552`)
- ICD: Generic Rotorcraft A
- Load conditions: {'unloaded': 0.0, 'rated': 4550.0}
- Requirements traced: 20/21 (95.2%)
- Tests: 124 (passed 115, skipped 6, xfail 3)
- Suite runtime: 18.9 s

| Req | Stage | Requirement | Tests | Passed | Verdict | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| ICD-1 | Interface | ARINC 429 BNR words shall be encoded per the ICD (label, SDI, sign, resolution, SSM, odd parity). | 11 | 10 | **PASS** |  |
| A1 | Actuator | Small-signal step response (1 mm, unloaded) shall have rise time <= 0.15 s and overshoot <= 10 %. | 1 | 1 | **PASS** |  |
| A2 | Actuator | Maximum rate shall be >= 35 mm/s unloaded and >= 10 mm/s at rated opposing load. | 2 | 2 | **PASS** |  |
| A3 | Actuator | Static position accuracy shall be <= 0.10 mm and backlash <= 0.15 mm, measured at the output rod. | 2 | 2 | **PASS** |  |
| A4 | Actuator | Position bandwidth (-3 dB) shall be >= 2.5 Hz. | 1 | 1 | **PASS** |  |
| A5 | Actuator | At rated opposing load, small-signal step overshoot shall be <= 10 %, rise time <= 0.15 s, accuracy <= 0.10 mm. | 2 | 2 | **PASS** |  |
| M1 | Model | The bench actuator model (Actuonix L16-P) shall reproduce the manufacturer datasheet speed-force points within 5 % and use the datasheet backlash. | 4 | 4 | **PASS** |  |
| R1 | Receiver | The receiver shall reject words with bad parity. | 4 | 4 | **PASS** |  |
| R2 | Receiver | The receiver shall treat SSM Failure Warning or No Computed Data as invalid. | 6 | 6 | **PASS** |  |
| R3 | Receiver | The receiver shall declare a label stale if not updated within 3 nominal transmit intervals. | 6 | 4 | **PASS** |  |
| R4 | Receiver | The receiver shall reject values outside the physical range. | 7 | 7 | **PASS** |  |
| R5 | Voter | With three valid sources, the voter shall output the middle value. | 7 | 6 | **PASS** |  |
| R6 | Voter | The voter shall fail a channel that miscompares beyond threshold for longer than the persistence time. | 12 | 12 | **PASS** |  |
| R7 | Voter | The voter shall not fail a channel on a single short spike. | 5 | 5 | **PASS** |  |
| R8 | Voter | After one channel failure, the voter shall continue on the remaining two and annunciate. | 25 | 24 | **PASS** |  |
| R9 | System | After a single-channel failure, the actuator reconfiguration transient shall overshoot <= 0.60 mm and settle within +/-0.25 mm in <= 0.80 s. | 4 | 3 | **OPEN DEFECT** | RCA-001: integrator windup during rate saturation at rated load |
| R10 | System | The actuator command shall never exceed the position or rate limits, whatever the input. | 26 | 25 | **PASS** |  |
| L1 | Bench link | Channel A sent from a separate computer over a real Ethernet link shall decode per the ICD, arrive at the nominal label rate (mean interval within 2 %) without gaps long enough to trip the stale check, and a link loss shall be flagged stale within 3 intervals and recover automatically. | 6 | 0 | **NOT RUN** |  |
| R11 | Actuator fault | After loss of one of two motor channels, the actuator shall hold commanded position within 0.50 mm for 5 s at every load condition up to rated. | 6 | 5 | **OPEN DEFECT** | FINDING-003: one motor's stall force is below rated load; rod is back-driven |
| R12 | Actuator fault | The actuator monitor shall annunciate a jam within 0.30 s while the command is moving, remove motor drive, and not annunciate during normal operation (including rate-limited moves at rated load and all Part B fault cases). | 14 | 13 | **OPEN DEFECT** | FINDING-005: monitor needs the RCA-001 anti-windup fix; baseline windup gives false jam alarms |
| R13 | Actuator fault | With three lanes active on one surface, equalization shall keep force fight between healthy lanes <= 500 N; a faulty lane shall be disengaged (only that lane) with surface error <= 0.25 mm after; a lane fault too small to detect shall cause <= 0.60 mm surface error. | 24 | 24 | **PASS** |  |

## Test results

| Test | Reqs | Status | Measured |
| --- | --- | --- | --- |
| `test_l1_words_on_the_wire_decode_per_icd` | L1, ICD-1 | skipped |  |
| `test_l1_rate_and_jitter_on_real_link` | L1 | skipped |  |
| `test_l1_no_false_stale_on_healthy_link` | R3, L1 | skipped |  |
| `test_l1_cable_pull_flagged_stale_and_recovers` | R3, L1 | skipped |  |
| `test_l1_closed_loop_with_real_channel_a` | R5, L1 | skipped |  |
| `test_l1_closed_loop_cable_pull` | R10, R8, L1 | skipped |  |
| `test_m1_speed_force_matches_datasheet[no_load]` | M1 | passed | force_n=0.0, datasheet_mm_s=32.0, model_mm_s=32.0, error_pct=0.0 |
| `test_m1_speed_force_matches_datasheet[peak_power]` | M1 | passed | force_n=50.0, datasheet_mm_s=16.0, model_mm_s=15.5, error_pct=3.1 |
| `test_m1_speed_force_matches_datasheet[peak_efficiency]` | M1 | passed | force_n=24.0, datasheet_mm_s=24.0, model_mm_s=24.1, error_pct=0.3 |
| `test_m1_backlash_matches_datasheet` | M1 | passed | model_backlash_param_mm=0.25, predicted_bench_hysteresis_mm=0.19 |
| `test_a1_small_signal_step_unloaded` | A1 | passed | rise_s=0.108, overshoot_pct=4.4 |
| `test_a2_max_rate[unloaded]` | A2 | passed | load=unloaded, rate_mm_s=40.0 |
| `test_a2_max_rate[rated]` | A2 | passed | load=rated, rate_mm_s=11.7 |
| `test_a3_accuracy_and_backlash` | A3 | passed | accuracy_mm=0.05, backlash_mm=0.101 |
| `test_a3_own_feedback_cannot_see_backlash` | A3 | passed | own_feedback_hysteresis_mm=0.001, truth_hysteresis_mm=0.101 |
| `test_a4_bandwidth` | A4 | passed | bandwidth_hz=2.99 |
| `test_a5_small_signal_step_rated_load` | A5 | passed | rise_s=0.108, overshoot_pct=5.1 |
| `test_a5_accuracy_rated_load` | A5 | passed | accuracy_mm=0.051 |
| `test_icd_bnr_round_trip[0.0]` | ICD-1 | passed |  |
| `test_icd_bnr_round_trip[2.5]` | ICD-1 | passed |  |
| `test_icd_bnr_round_trip[-2.5]` | ICD-1 | passed |  |
| `test_icd_bnr_round_trip[45.37]` | ICD-1 | passed |  |
| `test_icd_bnr_round_trip[-89.99]` | ICD-1 | passed |  |
| `test_icd_bnr_round_trip[89.99]` | ICD-1 | passed |  |
| `test_icd_bnr_round_trip[179.9]` | ICD-1 | passed |  |
| `test_icd_bnr_round_trip[-180.0]` | ICD-1 | passed |  |
| `test_icd_label_bits_are_reversed` | ICD-1 | passed |  |
| `test_icd_odd_parity` | ICD-1 | passed |  |
| `test_r1_bad_parity_rejected` | R1 | passed |  |
| `test_r2_ssm_invalid[0]` | R2 | passed |  |
| `test_r2_ssm_invalid[1]` | R2 | passed |  |
| `test_r2_ssm_normal_valid` | R2 | passed |  |
| `test_r3_stale_boundary` | R3 | passed | stale_limit_ms=60.0 |
| `test_r4_physical_range[90.0-True]` | R4 | passed |  |
| `test_r4_physical_range[-90.0-True]` | R4 | passed |  |
| `test_r4_physical_range[90.5-False]` | R4 | passed |  |
| `test_r4_physical_range[-120.0-False]` | R4 | passed |  |
| `test_fault_matrix[frozen-chA]` | R6, R8, R10 | passed | max_voted_error_deg=0.69, final_mode=DUAL, detect_latency_ms=1099 |
| `test_fault_matrix[frozen-chB]` | R6, R8, R10 | passed | max_voted_error_deg=1.25, final_mode=DUAL, detect_latency_ms=1459 |
| `test_fault_matrix[frozen-chC]` | R6, R8, R10 | passed | max_voted_error_deg=1.25, final_mode=DUAL, detect_latency_ms=1659 |
| `test_fault_matrix[drift-chA]` | R6, R8, R10 | passed | max_voted_error_deg=0.69, final_mode=DUAL, detect_latency_ms=839 |
| `test_fault_matrix[drift-chB]` | R6, R8, R10 | passed | max_voted_error_deg=1.25, final_mode=DUAL, detect_latency_ms=1859 |
| `test_fault_matrix[drift-chC]` | R6, R8, R10 | passed | max_voted_error_deg=1.25, final_mode=DUAL, detect_latency_ms=2299 |
| `test_fault_matrix[bias_jump-chA]` | R6, R8, R10 | passed | max_voted_error_deg=0.69, final_mode=DUAL, detect_latency_ms=99 |
| `test_fault_matrix[bias_jump-chB]` | R6, R8, R10 | passed | max_voted_error_deg=0.96, final_mode=DUAL, detect_latency_ms=99 |
| `test_fault_matrix[bias_jump-chC]` | R6, R8, R10 | passed | max_voted_error_deg=0.96, final_mode=DUAL, detect_latency_ms=99 |
| `test_fault_matrix[spike-chA]` | R7, R10 | passed | max_voted_error_deg=0.21, final_mode=TRIPLEX |
| `test_fault_matrix[spike-chB]` | R7, R10 | passed | max_voted_error_deg=0.94, final_mode=TRIPLEX |
| `test_fault_matrix[spike-chC]` | R7, R10 | passed | max_voted_error_deg=0.94, final_mode=TRIPLEX |
| `test_fault_matrix[bad_parity-chA]` | R1, R8, R10 | passed | max_voted_error_deg=0.69, final_mode=DUAL |
| `test_fault_matrix[bad_parity-chB]` | R1, R8, R10 | passed | max_voted_error_deg=0.24, final_mode=DUAL |
| `test_fault_matrix[bad_parity-chC]` | R1, R8, R10 | passed | max_voted_error_deg=0.73, final_mode=DUAL |
| `test_fault_matrix[ssm_fail-chA]` | R2, R8, R10 | passed | max_voted_error_deg=0.69, final_mode=DUAL |
| `test_fault_matrix[ssm_fail-chB]` | R2, R8, R10 | passed | max_voted_error_deg=0.21, final_mode=DUAL |
| `test_fault_matrix[ssm_fail-chC]` | R2, R8, R10 | passed | max_voted_error_deg=0.73, final_mode=DUAL |
| `test_fault_matrix[dropout-chA]` | R3, R8, R10 | passed | max_voted_error_deg=0.69, final_mode=DUAL |
| `test_fault_matrix[dropout-chB]` | R3, R8, R10 | passed | max_voted_error_deg=0.24, final_mode=DUAL |
| `test_fault_matrix[dropout-chC]` | R3, R8, R10 | passed | max_voted_error_deg=0.73, final_mode=DUAL |
| `test_fault_matrix[out_of_range-chA]` | R4, R8, R10 | passed | max_voted_error_deg=0.69, final_mode=DUAL |
| `test_fault_matrix[out_of_range-chB]` | R4, R8, R10 | passed | max_voted_error_deg=0.21, final_mode=DUAL |
| `test_fault_matrix[out_of_range-chC]` | R4, R8, R10 | passed | max_voted_error_deg=0.73, final_mode=DUAL |
| `test_r9_reconfiguration_transient_baseline[unloaded]` | R9 | passed | load=unloaded, step_mm=4.04, overshoot_mm=0.307, settle_s=0.619 |
| `test_r9_reconfiguration_transient_baseline[rated]` | R9 | xfail | load=rated, step_mm=4.06, overshoot_mm=0.922, settle_s=1.164 |
| `test_r9_corrective_action_verified[unloaded]` | R9 | passed | load=unloaded, step_mm=4.04, overshoot_mm=0.259, settle_s=0.527 |
| `test_r9_corrective_action_verified[rated]` | R9 | passed | load=rated, step_mm=4.03, overshoot_mm=0.017, settle_s=0.366 |
| `test_r10_command_limits_worst_case_inputs` | R10 | passed | max_cmd_mm=22.0, max_rate_mm_s=60.0 |
| `test_r5_mid_value_select[perm0]` | R5 | passed |  |
| `test_r5_mid_value_select[perm1]` | R5 | passed |  |
| `test_r5_mid_value_select[perm2]` | R5 | passed |  |
| `test_r5_mid_value_select[perm3]` | R5 | passed |  |
| `test_r5_mid_value_select[perm4]` | R5 | passed |  |
| `test_r5_mid_value_select[perm5]` | R5 | passed |  |
| `test_r6_fail_after_persistence` | R6 | passed | frames_to_latch=5 |
| `test_r6_threshold_has_margin_over_tolerance_stack` | R6 | passed | margin_deg=0.5 |
| `test_r6_within_threshold_never_fails` | R6 | passed |  |
| `test_r7_single_spike_ignored` | R7 | passed |  |
| `test_r7_intermittent_spikes_reset_counter` | R7 | passed |  |
| `test_r8_dual_mode_average_and_annunciate` | R8 | passed |  |
| `test_r8_second_fault_in_dual_is_annunciated` | R8 | passed |  |
| `test_r8_invalid_channel_excluded` | R8 | passed |  |
| `test_r11_motor_channel_loss_hold[unloaded]` | R11 | passed | load_n=0.0, stall_after_loss_n=3250, max_deviation_mm=0.0, monitor_trip_after_s=None |
| `test_r11_motor_channel_loss_hold[rated]` | R11 | xfail | load_n=4550.0, stall_after_loss_n=3250, max_deviation_mm=1.697, monitor_trip_after_s=2.97 |
| `test_r11_if_position_is_lost_it_is_annunciated[unloaded]` | R11 | passed | load=unloaded, drifted_past_threshold=False, monitor_trip_after_s=None |
| `test_r11_if_position_is_lost_it_is_annunciated[rated]` | R11 | passed | load=rated, drifted_past_threshold=True, monitor_trip_after_s=2.97 |
| `test_r11_corrective_option_verified[unloaded]` | R11 | passed | load=unloaded, load_n=0.0, stall_after_loss_n=6500, max_deviation_mm=0.0, monitor_trip_after_s=None |
| `test_r11_corrective_option_verified[rated]` | R11 | passed | load=rated, load_n=4550.0, stall_after_loss_n=6500, max_deviation_mm=0.0, monitor_trip_after_s=None |
| `test_r12_jam_detected_and_drive_removed[unloaded-near-retract]` | R12 | passed | load=unloaded, jam_detect_s=0.171 |
| `test_r12_jam_detected_and_drive_removed[unloaded-mid]` | R12 | passed | load=unloaded, jam_detect_s=0.171 |
| `test_r12_jam_detected_and_drive_removed[unloaded-near-extend]` | R12 | passed | load=unloaded, jam_detect_s=0.171 |
| `test_r12_jam_detected_and_drive_removed[rated-near-retract]` | R12 | passed | load=rated, jam_detect_s=0.171 |
| `test_r12_jam_detected_and_drive_removed[rated-mid]` | R12 | passed | load=rated, jam_detect_s=0.171 |
| `test_r12_jam_detected_and_drive_removed[rated-near-extend]` | R12 | passed | load=rated, jam_detect_s=0.171 |
| `test_r12_jam_with_stationary_command_is_latent` | R12 | passed | annunciated=False |
| `test_r12_no_false_alarm_on_rate_limited_move_at_rated_load` | R12 | passed | step_mm=20.0 |
| `test_r12_no_false_alarm_on_bandwidth_sine` | R12 | passed |  |
| `test_r12_no_false_alarm_across_part_b_faults[0pct_rated]` | R12 | passed | load_n=0, cases=48, false_alarms=0, worst_healthy_mm=0.659, worst_case=frozen-chB-maneuver, margin_mm=0.341 |
| `test_r12_no_false_alarm_across_part_b_faults[50pct_rated]` | R12 | passed | load_n=2275, cases=48, false_alarms=0, worst_healthy_mm=0.659, worst_case=frozen-chB-maneuver, margin_mm=0.341 |
| `test_r12_no_false_alarm_across_part_b_faults[75pct_rated]` | R12 | passed | load_n=3412, cases=48, false_alarms=0, worst_healthy_mm=0.659, worst_case=frozen-chB-maneuver, margin_mm=0.341 |
| `test_r12_no_false_alarm_across_part_b_faults[100pct_rated]` | R12 | passed | load_n=4550, cases=48, false_alarms=0, worst_healthy_mm=0.659, worst_case=frozen-chB-maneuver, margin_mm=0.341 |
| `test_r12_no_false_alarm_baseline_actuator` | R12 | xfail | load_n=3412, false_alarms=2, worst_healthy_mm=4.895, worst_case=drift-chA-maneuver |
| `test_r13_healthy_lanes_share_load_with_equalization` | R13 | passed | max_fight_n=300 |
| `test_r13_without_equalization_healthy_lanes_fight_and_trip` | R13 | passed | max_fight_n=8454, healthy_lane_disengaged_at_s={0: 0.67} |
| `test_r13_faulty_lane_disengaged[laneA+2mm]` | R13 | passed | disengaged={0: 0.2}, peak_surface_mm=0.83, final_surface_mm=0.1 |
| `test_r13_faulty_lane_disengaged[laneA-2mm]` | R13 | passed | disengaged={0: 0.2}, peak_surface_mm=0.74, final_surface_mm=0.1 |
| `test_r13_faulty_lane_disengaged[laneA+5mm]` | R13 | passed | disengaged={0: 0.2}, peak_surface_mm=1.85, final_surface_mm=0.1 |
| `test_r13_faulty_lane_disengaged[laneA-5mm]` | R13 | passed | disengaged={0: 0.2}, peak_surface_mm=1.85, final_surface_mm=0.1 |
| `test_r13_faulty_lane_disengaged[laneA+10mm]` | R13 | passed | disengaged={0: 0.2}, peak_surface_mm=3.69, final_surface_mm=0.1 |
| `test_r13_faulty_lane_disengaged[laneB+2mm]` | R13 | passed | disengaged={1: 0.2}, peak_surface_mm=0.9, final_surface_mm=-0.0 |
| `test_r13_faulty_lane_disengaged[laneB-2mm]` | R13 | passed | disengaged={1: 0.2}, peak_surface_mm=0.74, final_surface_mm=-0.0 |
| `test_r13_faulty_lane_disengaged[laneB+5mm]` | R13 | passed | disengaged={1: 0.2}, peak_surface_mm=1.85, final_surface_mm=-0.0 |
| `test_r13_faulty_lane_disengaged[laneB-5mm]` | R13 | passed | disengaged={1: 0.2}, peak_surface_mm=1.85, final_surface_mm=-0.0 |
| `test_r13_faulty_lane_disengaged[laneB+10mm]` | R13 | passed | disengaged={1: 0.2}, peak_surface_mm=3.69, final_surface_mm=-0.0 |
| `test_r13_faulty_lane_disengaged[laneC+2mm]` | R13 | passed | disengaged={2: 0.2}, peak_surface_mm=0.98, final_surface_mm=-0.1 |
| `test_r13_faulty_lane_disengaged[laneC-2mm]` | R13 | passed | disengaged={2: 0.2}, peak_surface_mm=0.82, final_surface_mm=-0.1 |
| `test_r13_faulty_lane_disengaged[laneC+5mm]` | R13 | passed | disengaged={2: 0.2}, peak_surface_mm=1.85, final_surface_mm=-0.1 |
| `test_r13_faulty_lane_disengaged[laneC-5mm]` | R13 | passed | disengaged={2: 0.2}, peak_surface_mm=1.85, final_surface_mm=-0.1 |
| `test_r13_faulty_lane_disengaged[laneC+10mm]` | R13 | passed | disengaged={2: 0.2}, peak_surface_mm=3.69, final_surface_mm=-0.1 |
| `test_r13_undetected_lane_fault_stays_small[0.5]` | R13 | passed | worst_undetected_surface_mm=0.167 |
| `test_r13_undetected_lane_fault_stays_small[1.0]` | R13 | passed | worst_undetected_surface_mm=0.333 |
| `test_r13_undetected_lane_fault_stays_small[1.5]` | R13 | passed | worst_undetected_surface_mm=0.5 |
| `test_r13_undetected_lane_fault_stays_small[-1.5]` | R13 | passed | worst_undetected_surface_mm=0.5 |
| `test_r13_undetected_lane_fault_stays_small[1.6]` | R13 | passed | worst_undetected_surface_mm=0.533 |
| `test_r13_undetected_lane_fault_stays_small[-1.6]` | R13 | passed | worst_undetected_surface_mm=0.533 |
| `test_r13_guard_monitor_isolates_only_the_largest_outlier` | R13 | passed | old_logic_lanes_disengaged=3 |
