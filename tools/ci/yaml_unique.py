#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""yaml_unique.py - 带"重复键检测"的 YAML 加载器（两个 CI 工具共用）。

为什么需要：PyYAML 的 safe_load 遇到同一 mapping 里的重复键会**静默取最后一个**。
本仓库真实发生过：整改时给实机 yaml 补一个 `takeoff_tilt_max_deg: -1.0`，
而该键已存在（10.0）——重复键让"补键"变成了"把实机起飞倾角限幅关掉"，
yaml 解析、roslaunch 启动、逐键 diff 全部无感。只有"旧值 vs 新值"对比才抓到。

用法：
    from yaml_unique import safe_load_unique, DuplicateKeyError
    doc = safe_load_unique(path_or_bytes)      # 重复键 -> 抛 DuplicateKeyError（带文件:行）
"""

import yaml

__all__ = ["DuplicateKeyError", "safe_load_unique", "UniqueKeyLoader"]


class DuplicateKeyError(Exception):
    """同一 mapping 内出现重复键。message 形如 '<file>:<line>: 重复键 "k"（首次在 <line>）'。"""


class UniqueKeyLoader(yaml.SafeLoader):
    """SafeLoader + 重复键检测。构造完成的 mapping 里，重复键直接报错而不是后者覆盖。"""

    def __init__(self, stream, name="<yaml>"):
        super().__init__(stream)
        self._source_name = name

    def construct_mapping(self, node, deep=False):
        if not isinstance(node, yaml.MappingNode):
            raise yaml.constructor.ConstructorError(
                None, None, "expected a mapping node, but found %s" % node.id, node.start_mark
            )
        seen = {}
        for key_node, _value_node in node.value:
            if not isinstance(key_node, yaml.ScalarNode):
                continue  # 非标量键（极少见）交给 SafeLoader 处理
            key = key_node.value
            line = key_node.start_mark.line + 1
            if key in seen:
                raise DuplicateKeyError(
                    "%s:%d: 重复键 %r（首次出现在第 %d 行）—— PyYAML/roslaunch 会静默取后者，"
                    "等价于悄悄改配置" % (self._source_name, line, key, seen[key])
                )
            seen[key] = line
        return super().construct_mapping(node, deep=deep)


def safe_load_unique(source, name=None):
    """source 可以是路径(str)、bytes 或已打开的文件对象。

    重复键抛 DuplicateKeyError；其余 YAML 错误原样抛 yaml.YAMLError。
    """
    if isinstance(source, (bytes, bytearray)):
        return yaml.load(bytes(source), Loader=_make_loader(name or "<bytes>"))
    if isinstance(source, str) and ("\n" not in source) and ("\r" not in source):
        with open(source, "rb") as fh:
            raw = fh.read()
        return yaml.load(raw, Loader=_make_loader(name or source))
    # 当作 YAML 文本
    return yaml.load(source, Loader=_make_loader(name or "<string>"))


def _make_loader(name):
    def _loader(stream):
        return UniqueKeyLoader(stream, name=name)

    return _loader
