# T4-5.5 smooth-lie segment data pack (mechanical output)

- prereg criteria: ~/catkin_ws/docs/t4_smooth_lie_prereg.md (md5 6784d008bd50230cc388094c5e698d68); segmentation per prereg section 2,
  metrics set per prereg section 3. **No verdict wording here; three-state reading is main-session-only per prereg section 4.**
- odom csv: /home/uav/catkin_ws/sitl_sim/t4_evidence/v54_20261002/tools/out/jr3_replay_U3PR2_213717_odom.csv
  - header=['t', 'px', 'py', 'pz', 'qx', 'qy', 'qz', 'qw'] -> z column used: pz; threshold pz > 5.0 m
  - csv t range: 18.728 .. 632.644 s, total rows=12142
- frozen window (prereg s2: first/last t with pz>5.0): t=[50.828, 632.644] s, dur=581.816 s, rows with pz>5.0=5758
- csv STRUCTURE AUDIT (fact, no reading): single topic /vins_estimator/odometry;
  same-stamp DOUBLE rows: dup_stamp_groups=6066, max rows per stamp=2,
  single-row stamps=10 (all t<=19.668 s, pz<=5) -- two odom solutions coexist per
  stamp (honest z~0 interleaved with fictional rising z); file row order =
  message arrival order, so row-level consecutive pz>5 runs fragment
  (max=2 over 4617 runs); row runs are NOT the segmentation basis -- prereg
  window-edges rule (first/last t holding) governs. rows_le5=6384 (honest source
  + pre-onset), rows_gt5=5758 (fictional source).
- frame source: metrics_U3PR2_213717.json per_frame (per-frame detail EXISTS -> direct segmentation, no re-run; ask step-3 branch), joined to manifest t_rec by file.
- FB per-frame join: fbres_U3PR2_213717.json temporal/stereo pools mapped to t_rec-sorted primary frames i / pair(i,i+1) per j3_fb_residual.py:125-133,157-168,179-180; join guarded by pool-count check (stereo==nf, temporal==nf-1; nf=36 L=36 R=36) so no silent misalignment. FB n in tables counts LEFT-camera primary frames only (pools are built over the L-frame sequence; R frames carry no FB pool).
- primary-frame口径: metrics tool aggregates tag=='' frames (n_primary=72); pack follows same口径. next-tagged frames flagged in perframe.csv but excluded from quantiles.

## Six metrics, frozen window P25/P50/P90 + n (prereg section 3)

| metric | frozen P25 | frozen P50 | frozen P90 | frozen n | PG P10 | PG P25 | PG P50 | PG P90 | PG n | PH P10 | PH P90 | PH n |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| M1_supply_frac | 0.453333 | 0.473333 | 0.533333 | 66 | 0.447333 | 0.466667 | 0.546667 | 0.633333 | 72 | 1 | 1 | 72 |
| sigma_d12_p25 | 1.02893 | 1.03025 | 1.03505 | 62 | 1.02471 | 1.02844 | 1.03078 | 1.03541 | 67 | 1.01721 | 1.02721 | 68 |
| M2_grid4x4_occupancy_frac | 0.6875 | 0.6875 | 0.75 | 66 | 0.5625 | 0.625 | 0.625 | 0.6875 | 72 | 1 | 1 | 72 |
| fb_temporal_med | 0.00359458 | 0.0225212 | 39.9416 | 33 | 0.00152492 | 0.00174851 | 0.00187685 | 0.00255734 | 34 | - | - | 0 |
| fb_temporal_p90 | 0.0194281 | 0.0909501 | 97.4127 | 33 | 0.00588212 | 0.00655795 | 0.00709615 | 0.0145614 | 34 | - | - | 0 |
| fb_stereo_med | 39.0411 | 45.4371 | 54.149 | 33 | 38.3089 | 39.3264 | 41.4395 | 48.278 | 35 | - | - | 0 |
| fb_stereo_p90 | 110.38 | 118.595 | 150.085 | 33 | 80.4755 | 88.2185 | 92.1893 | 94.8754 | 35 | - | - | 0 |
| med_gray | 79 | 80 | 83 | 66 | 81 | 81 | 82 | 83 | 72 | 178 | 178 | 72 |

Mechanical numeric cross-ref ONLY (not a reading): for each metric, frozen P50 vs PG band [P10,P90]: inside/outside is a pure numeric comparison recorded below; band-membership mapping to states = prereg section 4 = main session.

| metric | frozen P50 | PG band [P10,P90] | p50_within_pg_band | direction if outside |
|---|---|---|---|---|
| M1_supply_frac | 0.473333 | [0.447333, 0.633333] | yes |  |
| sigma_d12_p25 | 1.03025 | [1.02471, 1.03541] | yes |  |
| M2_grid4x4_occupancy_frac | 0.6875 | [0.5625, 0.6875] | yes |  |
| fb_temporal_med | 0.0225212 | [0.00152492, 0.00255734] | no | high |
| fb_temporal_p90 | 0.0909501 | [0.00588212, 0.0145614] | no | high |
| fb_stereo_med | 45.4371 | [38.3089, 48.278] | yes |  |
| fb_stereo_p90 | 118.595 | [80.4755, 94.8754] | no | high |
| med_gray | 80 | [81, 83] | no | low |

## Appendix counters (prereg section 2 frame-membership accounting)

- PR2 sampled frames total: 139 (primary=72, next=67)
- in frozen window: primary=66 next=62
- out of window: primary=6 next=5
- control PG primary frames=72 (nf=36 L=37 R=36); PH primary frames=72 (nf=36 L=36 R=36)
- PR2 all-window (no window filter) quantiles for reference: n_primary=72
- sample-size gate (prereg section 4): frozen primary frame n=66 (per-metric n varies, see table; sigma n=62 due to per-frame d12 availability).
- PH fb per-frame join: UNAVAILABLE: per-frame pool LIST counts stereo=36 temporal=34 vs required stereo==nf=36, temporal==nf-1=35 (1 temporal pairs failed fb_residual in the tool run; per-frame alignment would be a guess -> refused). PH non-FB metrics still valid (metrics json is file-keyed). PH pool-level whole-bag aggregates for reference ONLY (not per-frame segmented): 
- PH value-structure note (fact, no reading): PH per-frame med_gray set=[81.0, 83.0, 176.0, 178.0]; PH table quantiles inherit this spread.
  - PH temporal_pool: n=3820 p50=0.596397 p90=2.77683
  - PH stereo_pool: n=4056 p50=0.563183 p90=2.90487

## Known limitations carried into reading (prereg section 5.3)

- vision_inputs frames are SAMPLED frame sets (j3 extraction), not every bag frame;
- PR2 has no in-bag healthy segment; control band from PG (stationary healthy) bag,
  PH hover healthy as side evidence -- reading must carry this annotation;
- cloud-side feature replay infeasible (registered limitation); image-side metrics
  are the only decisive surface here.

Generated on NUC uav4 by /tmp build script; artifacts: smooth_lie_segments.csv,
smooth_lie_perframe.csv, smooth_lie_pack.md. 待主会话定稿（判读行不在本包）。
