# REBUILD — v57 自测回归资产重建册（池件④）

- 生成日期：2026-10-04（NUC 远端时区）；执行：T4 池件④（回归资产 /tmp 依赖加固）
- 目的：`/tmp/t4_v57_selftest/` 重启即失；本目录为可重建凭据的耐久正本。重启后按本册复建工作区，md5 对账一致即视为凭据有效。
- 仓库路径：`~/catkin_ws/sitl_sim/t4_evidence/regress_assets_20261004/`
- 上传纪律：本地镜像两段式（scp → /tmp staging → cp 入仓 → 两侧 md5 对账）；全部对账一致后入库。

## 一、逐文件 md5（入库后实测）

```
3a13c6965f607a0f5e3a37cf95c47b65  results_base33.jsonl
7caa5fb9a1fc2321760b71ab21dfc903  expected_fix1.json
3699d2a00dc7cbea8fabf2fcc41fe168  expected_fix2.json
3699d2a00dc7cbea8fabf2fcc41fe168  expected_fix3.json
9d580c0450c71d4c4c0c5c8641ea1079  expected_fix4.json
ff8a210555e01c386f032e7998c8c645  check_fix1.py
2d9619497064871367e33c2413f6b9c0  check_fix2.py
9d4a6bed39759ebdc9d2b18d11a551fe  check_fix3.py
627d2a0778a96b79bd6e166129c950aa  check_fix4.py
239b89f091998e8fd2a023ad6f5566f9  build_and_run_v57.py
2afd3d55ccf3e7df77fe26082dbc7aa0  regress_fix1.sh
754d36308e6b14960fc47394ddddfe71  regress_fix2.sh
748f36c86daf906f2887d1aec2615b70  regress_fix3.sh
9db26ef0c28cb98e2232bcf4ab25f449  regress_fix4.sh
d9a09f931e313cd3d286997af9934e91  regress_audit_v58.sh
```

（本册 REBUILD.md 自身不入此清单。）

## 二、来源登记

| 文件 | 源 | 对账 |
|---|---|---|
| results_base33.jsonl | `/tmp/t4_v57_selftest/results_base33.jsonl`（在册正本，33 行） | cp 后两侧 md5 一致（3a13c696…） |
| expected_fix1..4.json、check_fix1..4.py、build_and_run_v57.py、regress_fix1..4.sh、regress_audit_v58.sh | `~/sitl_sim/t4_selftest/`（正本）；本地镜像 `D:/drone_VINS/t4_work_20261002/work_selftest/` 同 md5 | 本地 scp → staging → 入仓，三侧 md5 一致 |
| regress_*.sh（5 件） | 取锁修复后版本（2026-10-04 03:31，3529/3529/3703/3703/4867 B）；修复前旧版存 `~/sitl_sim/t4_selftest/.bak_lockfix_20261004/`（2027/2027/2201/2201/3322 B） | 同上 |

### 本地镜像分歧记录（诚实条款）

- 本地 `work_selftest/results.jsonl`：33 行，但为 v54 时代旧快照（各行 out_path 指向 `/tmp/t4_v54_selftest/`），**不作为 v57 基线入库源**；仅作"33 行口径"的历史旁证（md5 71aad0066764ecd3701605bb8fb6f727）。
- 本地 `work_selftest/results_v57_baseline.jsonl`：与在册正本 case/tool/rc/判定内容逐行一致，仅 elapsed_s 计时抖动差异（33/33 行均如此），md5 a73d0bc434a1b9e5b18c38490f40a707。
- /tmp 现存核对（2026-10-04 04:30 远端时间）：`results_base33.jsonl` / `results.jsonl`(45 行) / `results_ext12.jsonl`(12 行) / `cases/`（17 个合成 case 目录，可由 build_and_run_v57.py 重建）/ `logs/`。**无已丢失件**。`results.jsonl` 全量与 `results_ext12.jsonl` 属后续轮次产出，不在池件④清单，未入仓。

## 三、重启后复建 /tmp/t4_v57_selftest 步骤

```bash
# 0) 前置：NUC 本机；确认 HOME=/home/uav；df -h / 剩余 >25G
mkdir -p /tmp/t4_v57_selftest && cd /tmp/t4_v57_selftest
A=~/catkin_ws/sitl_sim/t4_evidence/regress_assets_20261004
cp $A/build_and_run_v57.py $A/check_fix*.py $A/expected_fix*.json $A/regress_*.sh .
chmod 755 *.py *.sh
# md5 对账：逐文件 md5sum 与本册第一节比对，一一对上才算复建到位
md5sum build_and_run_v57.py check_fix*.py expected_fix*.json regress_*.sh
# cases/ 与 logs/ 由构建器重建（纯合成 case，无外部依赖）：
python3 build_and_run_v57.py        # 用法见脚本内 usage/argparse
cp $A/results_base33.jsonl .        # 基线拷回作对账参考
# 复跑回归（按需）：
bash regress_fix1.sh                # regress_fix2.sh / fix3 / fix4 / regress_audit_v58.sh 同理
```

## 四、门环境注意（踩坑实录）

1. **NUC 本机 HOME**：脚本内 `~/sitl_sim`（锁、bags、STATUS）相对 NUC 用户 HOME=/home/uav；从其他用户/容器入口跑时 HOME 漂移会找不到资产与锁，先 `echo $HOME` 核实。
2. **ssh 别名不可用**：`nuc` / `nuc-ts` 别名只存在于本地 Windows `~/.ssh/config`；在 NUC 本机执行的脚本里**禁止** `ssh nuc` 类调用（别名解析失败）。
3. **set -u 作用域化**：若给回归脚本加 `set -u`，必须包在子 shell `( set -u; ... )` 中；禁止全局 set 后再 source 其他脚本（历史踩坑：未定义变量污染后续步骤）。
4. **CRLF 剥 \r**：任何从 Windows 侧拷入的 .sh/.py 先 `sed -i 's/\r$//'`（或 dos2unix）再执行；CRLF 会改变 md5，与第一节对不上即视为未剥净。本目录入库件均为 LF（本地镜像 file 实测无 CRLF，md5 与 NUC 正本一致即证）。
5. **版本标识**：本目录 regress_*.sh 为 2026-10-04 03:31 取锁修复后版本；与 `~/sitl_sim/t4_selftest/.bak_lockfix_20261004/` 内旧版（2027/2027/2201/2201/3322 B）勿混用。
6. **判读/重放纪律不变**：离线 0 锁（私有 roscore master 11314 + `nice -n 10` + `timeout` 包裹）；测试取锁必走 `SITL_LOCK_FILE` 侧锁文件，禁碰真锁（runbook 附录 E1 口径）。
7. **中文写 NUC 走 scp 通道**：本地写文件 → scp 到 nuc:/tmp/ → ssh cp/append；禁 ssh 命令行内联中文（乱码实锤坑）。本册即按此通道入仓。

——本册为登记性质产物（池件④资产加固），不涉及判据设计与判读面；md5 以入库时点实测为准。
