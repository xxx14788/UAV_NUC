# 卡点法证：depth 传感器渲染全 NaN 回退（2026-10-16 18:56-20:25，甲合流册执行者）

## 现象
- /iris_stereo_vins/camera/depth/image_raw 全像素 NaN（32FC1 逐字 unpack 实证）；/camera/depth/points 同为全 Inf。
- depth-rig 的 RGB（/camera/rgb/image_raw）= 均匀暗帧（~51-76 亮度）= 传感器渲染空场景；对照组 vins_cam_left/right（type=camera 传感器）渲染正常（ASCII 帧结构完整）。
- 判定：depth 型传感器（depth_camera.sdf，type=depth）的渲染通道失效；camera 型正常。planner（ego_planner grid_map 唯一障碍源=depth）因此全盲。

## 已排除（每项实测）
1. world 无关：v9/v73/obstacles 三世界全 NaN（obstacles=T 战役数周在役世界）。
2. 本会话部署物无关：c3_lab.material+4 PNG（/usr/share/gazebo-11）隔离后仍 NaN；~/.gazebo/models/c3_lab 隔离后仍 NaN（均已恢复原位）。
3. 显示器无关：Xvfb :99（-screen 0 1280x1024x24）与真 GPU :1（Xorg, RTX3090+535 驱动）均 NaN。
4. 位姿无关：地面/teleport 空中 z=1.5 均 NaN+RGB 黑。
5. 非首帧：连续 10 帧全 NaN；栈起 5min 后（rtshader 缓存重建毕）仍 NaN。
6. 包/驱动未变：dpkg 无 gazebo/ogre/mesa/nvidia 更新（最后 10-12 python3.8-venv）；dmesg 无 GPU Xid；无 suspend/resume；uptime 连续 10-09 19:30 起。
7. 资源充足：28 核 load~3、内存 29G 可用、磁盘 367G、/dev/shm 空、CPU 3.4GHz 无热限频（39°C）。
8. OGRE 初始化正常：ogre.log RenderSystem_GL 加载、GLX 窗口建立、FBO 全格式（含 PF_FLOAT16_R/D32S0）支持。
9. PX4/SDF 未动：stereo_vins_rig.sdf=974a7533、iris_stereo_vins.sdf=dfb94ea4、depth_camera.sdf=26941dbf、px4 二进制+插件 .so mtime 全为 09-29。
10. 丙册无话题级干扰：其重放在私 master 11314，本侧 /clock 唯一发布者=/gazebo（实测 rostopic info）。
11. 缓存清理无效：/tmp/gazebo-ghj-rtshaderlibcache 删除重建后仍 NaN；~/.gazebo 会话残留清理无效。

## 昨日在案的对照
- 昨晨 05:42-08:07 终版批 25 轮中存在 geom 实证的 S 形绕行（如 C3F73NE2 三箱交互+maxlat 0.8+ndetour≥3）——planner 非盲 ⇒ depth 当时工作。
- 本卡点回退窗口 = 10-16 08:07-19:12 之间，触发因素不明。

## 建议处置（用户域）
- 首选整机重启（up 7 天，X/GPU/内核状态复位；:1 桌面会话与在跑任务须先收）。
- 重启后复测法（3min）：跑 /tmp/obs_dry_start.sh（obstacles 干测栈）+ 探针脚本（见 /tmp/depth_probe_result.txt 生成法）看 depth nonzero>0。

## 对本册影响
- v9 试录/终版批（§二.3/§三）暂停=primary 层语料待机修；13m 扩展层语料（final_v73_jia 25/25）完备 ⇒ 保底交付路线启动（§四扩展层判读先行）。
