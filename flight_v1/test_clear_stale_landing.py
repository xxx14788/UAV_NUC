#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""clear_stale_landing 单测（不依赖 ROS）：上一轮 landing.requested 的清理边界。"""
import importlib.util
import os
import tempfile
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "fsm", os.path.join(HERE, "flight_shape_mission.py"))
fsm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fsm)

TMP = Path(tempfile.mkdtemp(prefix="landing_test_"))
fsm.LANDING_FILE = TMP / "landing.requested"
fsm.STOP_FILE = TMP / "stopping"


class St(object):
    connected = True
    armed = False


class Ext(object):
    landed_state = 1


class ExtAir(object):
    landed_state = 2


class Flight(object):
    pass


def make(armed=False, ext=Ext(), state_raises=False):
    f = object.__new__(fsm.RosFlight)
    f.cache = {"/mavros/extended_state": ext}
    f.times = {}
    f.logs = []
    f._log = lambda stage, msg: f.logs.append((stage, msg))
    if state_raises:
        def boom():
            raise RuntimeError("state stale")
        f._state = boom
    else:
        f._state = lambda: type("S", (), {"armed": armed, "connected": True})()
    f._fresh = lambda *a, **k: True
    f._fresh_stamp = lambda *a, **k: True
    return f


def case(name, armed, ext, expect_clear, state_raises=False):
    fsm.LANDING_FILE.write_text("requested\n")
    f = make(armed=armed, ext=ext, state_raises=state_raises)
    got = f.clear_stale_landing()
    exists = fsm.LANDING_FILE.exists()
    ok = (got is expect_clear) and (exists is (not expect_clear))
    print("%s %s: clear=%s exists=%s" % ("PASS" if ok else "FAIL", name, got, exists))
    assert ok, name


if __name__ == "__main__":
    case("disarmed on ground -> clear", False, Ext(), True)
    case("armed -> keep", True, Ext(), False)
    case("in air disarmed -> keep", False, ExtAir(), False)
    case("state stale -> keep", False, Ext(), False, state_raises=True)
    # 文件不存在 -> False 且不报错
    if fsm.LANDING_FILE.exists():
        fsm.LANDING_FILE.unlink()
    f = make()
    assert f.clear_stale_landing() is False
    print("PASS no-file: clear=False")
    print("CLEAR_STALE_LANDING PASS")
