# 代码与配置规范

参照 [ROS C++ Style Guide](http://wiki.ros.org/CppStyleGuide)、[ROS Naming Conventions](http://wiki.ros.org/NamingConventions)、[PX4 Coding Standards](https://docs.px4.io/main/en/contribute/coding_style.html)，按本仓库实情裁剪。

## 0. 最高原则：入乡随俗 + 上游 diff 最小化

本仓库主体是上游 Fast-Drone-250 / EGO-Planner / VINS-Fusion 代码。**编辑既有文件时，遵循该文件现有的缩进、命名、大括号风格**；不做风格化改动。新增文件按本文第 1–4 节执行。理由：保持"与上游差异可枚举"（见 [workflow.md](workflow.md) §3）。

## 1. 命名（ROS 官方约定）

- 包名 / 文件名 / 话题 / 服务 / 参数 / 节点：`snake_case`（小写下划线）
- 类与类型：`PascalCase`；变量与函数：`snake_case`（或文件既有惯例）
- 常量与宏：`ALL_CAPS`（宏尽量避免使用）
- 话题名尽量带命名空间前缀防冲突（仓库现有惯例：`/vins_estimator/...`、`/px4ctrl/...`）
- 类成员可用前缀区分作用域（如 grid_map 的 `mp_`、订阅器 `_sub` 后缀），同一文件内保持一致

## 2. C++（新增文件）

- 4 空格缩进；`#include` 顺序：对应头 → C 系统库 → C++ 标准库 → 第三方 → ROS → 本项目
- 日志一律用 `ROS_DEBUG / ROS_INFO / ROS_WARN / ROS_ERROR`，禁止 `printf` / `std::cout` 调试输出
- 头文件内禁 `using namespace`；优先 C++14（noetic / gcc-9 环境）
- 公共接口写 Doxygen 风格注释（`/** */`）；实现里只注释"为什么"，不复述"做什么"
- 错误处理：不吞返回值；ROS 回调里不抛异常

## 3. Python / Bash 脚本

- Python：PEP 8，4 空格；顶层脚本带 shebang 与一行用途说明
- Bash：沿用 `sitl_sim/00–06` 的模板——`#!/usr/bin/env bash`、中文块注释说明用途与前置条件、`set -u`、显式 `source` 并注明原因、失败路径给出兜底提示；路径一律 `$HOME` 展开，不硬编码 `/home/uav`

## 4. launch / XML / YAML

- 新增参数必须带注释：含义、单位、默认值来源（标定/实验/上游默认）
- SITL 与真机配置**永远分离成不同文件**（先例：`run_ctrl.launch` vs `run_ctrl_sitl.launch`、`ctrl_param.yaml` vs `ctrl_param_sitl.yaml`）
- remap 显式写在 launch 内，不在代码里写死别人的话题名（上游 grid_map 的 extrinsic 话题是教训：宁可 remap，不改源码）

## 5. 禁止清单

- 注释掉的死代码、`gdb` launch-prefix 之类的临时调试残留（历史教训，见 git log）
- 功能提交里混入无关 whitespace / 缩进 / 重命名改动
- `package.xml` 不写依赖却 include 别的包的头文件（隐形依赖）
- 硬编码 IP、密码、绝对路径进源码（公开仓库红线，同 CONTRIBUTING §1）

## 6. 工具（可选，不强制）

- XML/YAML 快查：`xmllint --noout file.xml`
- C++ 静态检查：`cppcheck`；新文件可套 `clang-format`（上游文件不要批量格式化）
- 依赖自查：`rospack deps <pkg>` 与 `package.xml` 对照
