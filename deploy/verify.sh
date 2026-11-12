#!/bin/bash
# 对比 deploy/ 快照与实机文件（sha256）。输出 OK/DIFF/MISSING。
cd "$(dirname "$0")" || exit 1
fail=0
chk() { # $1=repo file, $2=live path
  if [ ! -f "$2" ]; then echo "MISSING $2"; fail=1; return; fi
  a=$(sha256sum "$1" | cut -d' ' -f1); b=$(sha256sum "$2" | cut -d' ' -f1)
  if [ "$a" = "$b" ]; then echo "OK      $2"; else echo "DIFF    $2"; fail=1; fi
}
for f in home/*; do chk "$f" "$HOME/$(basename "$f")"; done
for f in config/*; do chk "$f" "$HOME/sitl_realmachine/03_realmachine_config/$(basename "$f")"; done
exit $fail
