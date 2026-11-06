Header header

float64 des_v_x
float64 des_v_y
float64 des_v_z

float64 fb_a_x
float64 fb_a_y
float64 fb_a_z

float64 des_a_x
float64 des_a_y
float64 des_a_z

float64 des_q_x
float64 des_q_y
float64 des_q_z
float64 des_q_w

float64 des_thr
float64 hover_percentage
float64 thr_scale_compensate
float64 voltage

float64 err_axisang_x
float64 err_axisang_y
float64 err_axisang_z
float64 err_axisang_ang

float64 fb_rate_x
float64 fb_rate_y
float64 fb_rate_z

# T1-P0D.2 (2026-10-01, C10-X2 channel B): odom latency/staleness instrumentation, unit ms.
# odom_delay_ms = odom rcv_stamp - odom msg.header.stamp (feed-time pipeline delay, factor 1.1);
# odom_staleness_ms = now - rcv_stamp at debug-publish (consumption staleness, factor 1.4).
# Filled in FSM debug path only (idle else-branch): idle/spin-up blind zone per C10 r3 caveat.
float64 odom_delay_ms
float64 odom_staleness_ms

# 2026-11-06: v2 串级观测（顾问加）。legacy 下 i_z 恒 0、v_d_z = des_v_z。
# i_z 是垂直速度环积分 [m/s^2]，是判断"积分有没有在干活"的唯一直接证据。
float64 i_z
float64 v_d_z
