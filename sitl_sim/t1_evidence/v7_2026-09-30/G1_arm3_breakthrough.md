# T1-G1 臂 3 重大突破：U3 失败条件命中——大消息带宽冲击致 roscpp 订阅端网络栈死亡（2026-09-30 夜 3）

状态：受控复现成立（两轮逐位一致 9 PASS/41 FAIL）；机制定位至"sub 进程活、socket 全关、
master 注册绿"形态；roscpp 内部挂点（哪行关的 socket）留夜 4 深挖。执行者：T1 v7 夜 3。

## 1. 复现器与条件

- sub：手编 roscpp 长活订阅（sensor_msgs/Image @/g1/img，tcpNoDelay，queue 2）——px4ctrl 同构
- pub：rospy 每轮新进程（anonymous），发 20 条 0.3MB Image（480×640 mono8）@20Hz
- master：共享 11311（稳定）；判定=3s 窗 GOT 计数增量
- 前两臂（String 小消息）双 master 50+50 轮零失败——**失败条件=大消息 payload，非 master 共享性**

## 2. 复现数据（两轮逐位一致）

| 轮批 | PASS/FAIL | GOT 总数 | 失败起点 |
|---|---|---|---|
| 第 1 次 | **9/41** | 180（=9 轮×20 条） | 第 10 轮起零投递 |
| 第 2 次（新干净 sub） | **9/41** | 180 | 同 |

**累积量阈值**：~180 帧 × 0.3MB ≈ 54MB 冲击后 sub 网络栈死亡，可复现率 2/2。

## 3. 失败形态（活体现场取证）

- **sub 进程活着**（pgrep 有、ros::spin 空转），**fd=3-4**（仅剩标准流+1）——**全部 socket 已关闭**
  （含 XML-RPC server socket 与 TCPROS）
- **master 注册绿**：`rostopic info` 显示 sub 在 Subscribers 列表——新 pub 被正常推送通知，
  但 sub 侧无人接听 → **建连永败**
- **排除项**：①非建连慢（单轮 20s 观察零投递）②非消息大小单条问题（rostopic pub 16 字节单条
  也零投递）③非 master 死（11311 系统级稳定）④非带宽拥塞（失败后零流量）
- **签名对账 U3**：v4 悬案"新建 pub 建连 ~50-71% 随机失败+零 TCP+进程在"——**同构**：
  U3 场景的 vins_node 图像流/odometry 持续大 payload 冲击 → 订阅端（px4ctrl/vins_to_mavros）
  网络栈死亡 → 后续所有新 pub（每轮重启的 vins 实例）建连永败。

## 4. 机制假设（夜 4 验证序列）

H-a：roscpp TransportTCP/ConnectionManager 在特定错误（写半关/大包分片超时/poll 错误）后
  走了**全局 cleanup 路径**（closeConnection 级联）但不退进程——嫌疑源码区
  `subscription.cpp:479-541 / transport_publisher_link.cpp / connection.cpp`（C04 overlay 三洞同域）
H-b：fd 泄漏反噬（ulimit -Sn=1024，大消息临时 fd 洪峰触顶后 roscpp 主动关栈自保）——
  复现时并行记录 sub 的 fd 数曲线可裁决
H-c：boost::asio/epoll 内部错误状态机卡死（poll 退化为忙等）

验证序列：①复现时逐秒记录 `ls /proc/pid/fd | wc -l`（H-b 一锤定音）②sub stderr 开
`roscpp_internal.connections` DEBUG（C04 D1 判别字典）③strace -f 跟 close/epoll 调用
④命中后对齐 roscpp 1.17.4 源码行→overlay 补丁（C04 D4 三洞齐封）

## 5. 对其他悬案的回灌

- **F4 SIGTERM 案**：vins_to_mavros"死亡"的另一候选形态=网络栈死亡而非进程死亡
  （10:40 案的 vins_estimator 是真 -15 杀，但**其他"节点死了"的观察**可能混入本形态——
  未来判定节点死亡必须 pgrep+fd 检查双确认，pgrep 活≠健康）
- **vins_smoke/smoke_probe 的 hz 探针**：探针自身是 roscpp 订阅端，长跑后同样可能栈死亡
  →**探针读数为零的轮不一定是链路断**（测量者已死）——t1 两轮"echo 字段假阴性"教训的新维度
- **C05 慢连**：不同形态（注册/连接慢 vs 建连死），不相混

## 6. 产物

- 复现器三件：/tmp/g1_sub_img(.cpp) /tmp/g1_pub_img.py /tmp/g1_arm3.sh（入库随提交拷 tools/g1/）
- 证据：/tmp/e2r_A.json~B.json（门禁）、/tmp/g1_arm3.log（两轮）、本文件
- 悬案池：U3 案状态 →"失败条件命中（大消息带宽），roscpp 内部挂点夜 4 定位"
