#!/usr/bin/env bash
# param_hygiene.sh — 实机配置零 GPS 依赖静态扫描（T1-v5 V2，README §0 R5 落地）。
# 扫描对象（默认，仓库自动定位）：
#   1. 实机控制参数:  src/px4ctrl/config/ctrl_param_fpv.yaml
#   2. 实机实验链:    src/planner/plan_manage/launch/single_run_in_exp.launch
#                     src/planner/plan_manage/launch/advanced_param_exp.xml
#                     src/launch/full_vins_px4.launch
#   3. VINS 实机配置: src/VINS-Fusion/config/realsense_d435/*
#   4. PX4 实机参数导出: 环境变量 PX4_PARAM_EXPORT 指向文件（未设则 WARN 跳过）
# 用法: param_hygiene.sh [--selftest] [file ...]
# 判定（逐行）：
#   FAIL   = 活代码含 GPS 依赖字样（gps / EKF2_GPS / MAV_CMD 176 /
#            GPS course / global origin / MAV_FRAME GLOBAL 类）
#   INFO   = 显式关闭形态（gps...: false/0/no/off/none）——不算依赖但列出
#   EXEMPT = 注释行（# // <!-- -->，含跨行 xml 注释）或行内 hygiene-exempt 标记
# 退出码: 0=无 FAIL  1=有 FAIL  2=用法/对象缺失
REPO="${REPO_ROOT:-$HOME/catkin_ws}"
FAILS=0

scan_files() {  # 参数: 文件列表; 输出报告行; 返回 0/1(有 FAIL)
    python3 - "$@" <<'PYEOF'
import re, sys

PAT_FAIL = [
    (re.compile(r'gps', re.I), 'GPS 字样'),
    (re.compile(r'mavcmd.{0,40}\b176\b|\b176\b.{0,40}mavcmd|ma_?v_?cmd.?\s*176', re.I), 'MAV_CMD 176'),
    (re.compile(r'\bcourse\b', re.I), 'GPS course 类'),
    (re.compile(r'global[_ ]?origin|set_gps_global_origin|gps[_ ]?origin', re.I), 'global origin 类'),
    (re.compile(r'mav_frame.{0,20}global|global[_ ]?frame|world[_ ]?geodetic', re.I), 'MAV_FRAME GLOBAL 类'),
]
PAT_DISABLE = re.compile(r'(gps\w*)\s*[:=]\s*["\']?(false|0|no|off|none)\b|use_gps.{0,12}(false|0|no|off|none)', re.I)
PAT_EXEMPT_MARK = re.compile(r'hygiene-exempt\s*:\s*(.*)', re.I)

def strip_comment(line, in_xml_comment):
    """返回 (code, is_comment, in_xml_comment_after)。"""
    s = line.lstrip()
    if in_xml_comment:
        if '-->' in line:
            return (re.sub(r'^.*?-->', '', line).strip(), False, False)
        return ('', True, True)
    if '<!--' in s:
        body = s.split('<!--', 1)[1]
        if '-->' not in body:
            return ('', True, True)          # 跨行注释开始
        s = re.sub(r'<!--.*?-->', '', s)
    if s.startswith('#') or s.startswith('//'):
        return ('', True, False)
    code = re.sub(r'<!--.*?-->', '', s)     # 行内 xml 注释剔除
    code = re.sub(r'(^|\s)#.*$', r'\1', code)  # bash/yaml 行内注释剔除
    return (code.strip(), False, False)

def classify(path):
    hits = []
    in_xml = False
    try:
        with open(path, 'r', errors='replace') as f:
            for i, line in enumerate(f, 1):
                m = PAT_EXEMPT_MARK.search(line)
                code, is_comment, in_xml = strip_comment(line, in_xml)
                if m:                         # 行内豁免标记：登记后不再判 FAIL
                    hits.append((i, 'EXEMPT', 'hygiene-exempt: %s' % m.group(1).strip()[:60]))
                    continue
                if is_comment or not code:
                    continue
                for pat, tag in PAT_FAIL:
                    if pat.search(code):
                        if PAT_DISABLE.search(code):
                            hits.append((i, 'INFO', '%s（显式关闭形态）: %s' % (tag, code[:70])))
                        else:
                            hits.append((i, 'FAIL', '%s: %s' % (tag, code[:70])))
                        break
    except OSError as e:
        print('  [FAIL] %s: 读取失败 %s' % (path, e))
        return True
    has_fail = any(h[1] == 'FAIL' for h in hits)
    if not hits:
        print('  [PASS] %s（0 命中）' % path)
    else:
        print('  [%s] %s' % ('FAIL' if has_fail else 'PASS', path))
        for i, cls, msg in hits:
            print('      line %-4d %s %s' % (i, cls, msg))
    return has_fail

any_fail = False
for p in sys.argv[1:]:
    if classify(p):
        any_fail = True
sys.exit(1 if any_fail else 0)
PYEOF
}

discover_targets() {
    TARGETS=()
    local d f n=0
    for d in \
        "src/px4ctrl/config/ctrl_param_fpv.yaml" \
        "src/planner/plan_manage/launch/single_run_in_exp.launch" \
        "src/planner/plan_manage/launch/advanced_param_exp.xml" \
        "src/launch/full_vins_px4.launch"; do
        if [ -f "$REPO/$d" ]; then TARGETS+=("$REPO/$d");
        else echo "  [FAIL] 缺失对象 $d"; FAILS=$((FAILS+1)); fi
    done
    for f in "$REPO"/src/VINS-Fusion/config/realsense_d435/*; do
        [ -f "$f" ] && { TARGETS+=("$f"); n=$((n+1)); }
    done
    [ "$n" -gt 0 ] || { echo "  [FAIL] realsense_d435 目录无文件"; FAILS=$((FAILS+1)); }
    if [ -n "${PX4_PARAM_EXPORT:-}" ]; then
        if [ -f "$PX4_PARAM_EXPORT" ]; then TARGETS+=("$PX4_PARAM_EXPORT");
        else echo "  [FAIL] PX4_PARAM_EXPORT 指向的文件不存在"; FAILS=$((FAILS+1)); fi
    else
        echo "  [WARN] 未设 PX4_PARAM_EXPORT，PX4 实机参数导出未扫描（有导出后: export PX4_PARAM_EXPORT=<file>）"
    fi
}

selftest() {
    local TMP rc ok=1
    TMP=$(mktemp -d /tmp/param_hygiene_st.XXXX) || return 2
    cp "$REPO/src/px4ctrl/config/ctrl_param_fpv.yaml"        "$TMP/clean.yaml"
    cp "$REPO/src/planner/plan_manage/launch/single_run_in_exp.launch" "$TMP/clean.launch"
    cp "$REPO/src/VINS-Fusion/config/realsense_d435/left.yaml" "$TMP/clean_vins.yaml" 2>/dev/null \
        || cp "$TMP/clean.yaml" "$TMP/clean_vins.yaml"
    cp "$TMP/clean.yaml" "$TMP/inj_param.yaml";  printf 'ekf2_gps_aid_mask: 3\n' >> "$TMP/inj_param.yaml"
    cp "$TMP/clean.launch" "$TMP/inj.launch";    printf '<param name="use_gps" value="true"/>\n' >> "$TMP/inj.launch"
    cp "$TMP/clean_vins.yaml" "$TMP/inj_vins.yaml"; printf 'gps_topic: /mavros/gps/fix\n' >> "$TMP/inj_vins.yaml"
    cp "$TMP/clean.yaml" "$TMP/inj_cmd.yaml";    printf 'rosrun mavros mavcmd long 176 105 5000 0 0 0 0 0\n' >> "$TMP/inj_cmd.yaml"
    cp "$TMP/clean.yaml" "$TMP/disable.yaml";    printf 'use_gps: false\n' >> "$TMP/disable.yaml"
    cp "$TMP/clean.yaml" "$TMP/comment.yaml";    printf '# 架构: 纯视觉, 无 GPS 依赖\n' >> "$TMP/comment.yaml"
    { printf '<!--\n  GPS course 备注在注释里, 不算依赖\n-->\n'; cat "$TMP/clean.launch"; } > "$TMP/xmlcomment.launch"
    cp "$TMP/clean.yaml" "$TMP/exempt.yaml";     printf 'rosrun mavros mavcmd long 176 105 5000 0 0 0 0 0  # hygiene-exempt: 自测标记\n' >> "$TMP/exempt.yaml"

    echo "== param_hygiene selftest =="
    scan_files "$TMP/clean.yaml" "$TMP/clean.launch" "$TMP/clean_vins.yaml" >/dev/null 2>&1; rc=$?
    echo "  干净副本(3 文件)     期望 PASS(0) 实际 $rc"; [ $rc -eq 0 ] || ok=0
    scan_files "$TMP/inj_param.yaml"  >/dev/null 2>&1; rc=$?
    echo "  注入 EKF2_GPS 参数   期望 FAIL(1) 实际 $rc"; [ $rc -eq 1 ] || ok=0
    scan_files "$TMP/inj.launch"      >/dev/null 2>&1; rc=$?
    echo "  注入 use_gps:true    期望 FAIL(1) 实际 $rc"; [ $rc -eq 1 ] || ok=0
    scan_files "$TMP/inj_vins.yaml"   >/dev/null 2>&1; rc=$?
    echo "  注入 gps_topic       期望 FAIL(1) 实际 $rc"; [ $rc -eq 1 ] || ok=0
    scan_files "$TMP/inj_cmd.yaml"    >/dev/null 2>&1; rc=$?
    echo "  注入 mavcmd 176      期望 FAIL(1) 实际 $rc"; [ $rc -eq 1 ] || ok=0
    scan_files "$TMP/disable.yaml"    >/dev/null 2>&1; rc=$?
    echo "  显式关闭 use_gps: false 期望 PASS(0) 实际 $rc"; [ $rc -eq 0 ] || ok=0
    scan_files "$TMP/comment.yaml"    >/dev/null 2>&1; rc=$?
    echo "  注释行 GPS           期望 PASS(0) 实际 $rc"; [ $rc -eq 0 ] || ok=0
    scan_files "$TMP/xmlcomment.launch" >/dev/null 2>&1; rc=$?
    echo "  xml 跨行注释 GPS     期望 PASS(0) 实际 $rc"; [ $rc -eq 0 ] || ok=0
    scan_files "$TMP/exempt.yaml"     >/dev/null 2>&1; rc=$?
    echo "  hygiene-exempt 行内标记 期望 PASS(0) 实际 $rc"; [ $rc -eq 0 ] || ok=0
    rm -rf "$TMP"
    if [ $ok -eq 1 ]; then echo "  SELFTEST PASS (10/10)"; return 0; else echo "  SELFTEST FAIL"; return 1; fi
}

case "${1:-}" in
    --selftest) selftest; exit $? ;;
    -h|--help) sed -n '2,15p' "$0"; exit 0 ;;
esac

echo "== param_hygiene ($(date '+%F %T')) 实机零 GPS 静态扫描 =="
if [ $# -gt 0 ]; then
    scan_files "$@"; rc=$?
else
    discover_targets
    scan_files "${TARGETS[@]}"; rc=$?
fi
echo "== param_hygiene 结果: FAIL=$rc 缺失对象=$FAILS =="
[ $rc -eq 0 ] && [ $FAILS -eq 0 ] && exit 0 || exit 1
