# Requirements Traceability Matrix

- Generated: 2026-10-14T05:20:10+00:00
- Git commit: `84abada`
- Config: `config/sil.yaml` (sha256 `3efda6d32f2d`)
- ICD: Generic Rotorcraft A
- Load conditions: {'unloaded': 0.0, 'rated': 700.0}
- Requirements traced: 16/16 (100.0%)
- Tests: 70 (passed 69, xfail 1)
- Suite runtime: 7.4 s

| Req | Stage | Requirement | Tests | Passed | Verdict | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| ICD-1 | Interface | ARINC 429 BNR words shall be encoded per the ICD (label, SDI, sign, resolution, SSM, odd parity). | 10 | 10 | **PASS** |  |
| A1 | Actuator | Small-signal step response (1 mm, unloaded) shall have rise time <= 0.15 s and overshoot <= 10 %. | 1 | 1 | **PASS** |  |
| A2 | Actuator | Maximum rate shall be >= 35 mm/s unloaded and >= 10 mm/s at rated opposing load. | 2 | 2 | **PASS** |  |
| A3 | Actuator | Static position accuracy shall be <= 0.10 mm and backlash <= 0.15 mm, measured at the output rod. | 2 | 2 | **PASS** |  |
| A4 | Actuator | Position bandwidth (-3 dB) shall be >= 2.5 Hz. | 1 | 1 | **PASS** |  |
| A5 | Actuator | At rated opposing load, small-signal step overshoot shall be <= 10 %, rise time <= 0.15 s, accuracy <= 0.10 mm. | 2 | 2 | **PASS** |  |
| R1 | Receiver | The receiver shall reject words with bad parity. | 4 | 4 | **PASS** |  |
| R2 | Receiver | The receiver shall treat SSM Failure Warning or No Computed Data as invalid. | 6 | 6 | **PASS** |  |
| R3 | Receiver | The receiver shall declare a label stale if not updated within 3 nominal transmit intervals. | 4 | 4 | **PASS** |  |
| R4 | Receiver | The receiver shall reject values outside the physical range. | 7 | 7 | **PASS** |  |
| R5 | Voter | With three valid sources, the voter shall output the middle value. | 6 | 6 | **PASS** |  |
| R6 | Voter | The voter shall fail a channel that miscompares beyond threshold for longer than the persistence time. | 12 | 12 | **PASS** |  |
| R7 | Voter | The voter shall not fail a channel on a single short spike. | 5 | 5 | **PASS** |  |
| R8 | Voter | After one channel failure, the voter shall continue on the remaining two and annunciate. | 24 | 24 | **PASS** |  |
| R9 | System | After a single-channel failure, the actuator reconfiguration transient shall overshoot <= 0.60 mm and settle within +/-0.25 mm in <= 0.80 s. | 4 | 3 | **OPEN DEFECT** | RCA-001: integrator windup during rate saturation at rated load |
| R10 | System | The actuator command shall never exceed the position or rate limits, whatever the input. | 25 | 25 | **PASS** |  |

## Test results

| Test | Reqs | Status | Measured |
| --- | --- | --- | --- |
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
