set auto-load safe-path /
set pagination off
set confirm off
set $n = 0
break operator new(unsigned long) if $rdi > 9500 && $rdi < 13500
commands
silent
set $n = $n + 1
printf "=== HIT %d size=%lu ===\n", $n, $rdi
bt 14
if $n >= 20
detach
quit
end
continue
end
continue
