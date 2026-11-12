# deploy/：机上部署件快照（2026-11-12）

这里存的是**真正在 NUC 上运行的部署件**的快照，来源不在本仓（原先散落在 ~/ 与 ~/sitl_realmachine/）。
- deploy/home/   ← 对应 ~/<同名文件>（realflight_*.sh、preflight.sh、set_imu_rate.sh 等）
- deploy/config/ ← 对应 ~/sitl_realmachine/03_realmachine_config/<同名文件>（VINS 双目 yaml 等）

语义：**快照，不是唯一源**。跑  可逐文件对比实机副本的 sha256；
若列出 DIFF，说明实机改过而未回写本仓 —— 收口时请把实机版本拷回并提交。
