#!/usr/bin/env python3
"""Run the preregistered static/hover/nav baseline in the SITL container only."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import signal
import subprocess
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--modes', nargs='+', choices=['static', 'hover', 'nav'],
                        default=['static', 'hover', 'nav'])
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if not Path('/.dockerenv').exists():
        parser.error('must run inside the Docker SITL container')
    for process in ('px4', 'gzserver', 'rosmaster'):
        if subprocess.run(['pgrep', '-x', process], stdout=subprocess.DEVNULL).returncode == 0:
            parser.error('existing process; refusing to touch another run: ' + process)
    with socket.socket() as sock:
        sock.settimeout(1)
        if sock.connect_ex(('127.0.0.1', 11311)) == 0:
            parser.error('ROS master port already occupied')
    if os.environ.get('ROS_MASTER_URI', 'http://localhost:11311') != 'http://localhost:11311':
        parser.error('requires the local default ROS domain')
    overrides = [k for k in os.environ if k.startswith(('T2_', 'T1_E', 'VINS_SMOKE_', 'C3A_'))]
    if overrides:
        parser.error('unexpected experiment overrides: ' + ','.join(overrides))
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    output = root / 'runtime' / 'baselines' / run_id
    subprocess.run(['python3', str(root / 'docker/scripts/freeze_baseline.py'), str(output)], check=True)
    (output / 'environment.txt').write_text(subprocess.check_output(
        ['bash', str(root / 'docker/scripts/verify_environment.sh'), '--require-built'], text=True))
    status = {'run_id': run_id, 'image_id': os.environ.get('BASELINE_CONTAINER_IMAGE_ID'), 'runs': [],
              'protocol': 'docs/2026-10-25_baseline-protocol.md',
              'gpu_scope': 'simulator only; no GPU change in this suite'}
    print('BASELINE_SUITE=' + str(output), flush=True)
    runtime = Path.home() / 'sitl_sim'
    try:
        for mode in args.modes:
            seconds = 180 if mode == 'nav' else 40
            tag = 'BASELINE_' + run_id + '_' + mode
            command = ['bash', str(runtime / 'vins_smoke.sh'), '--tag', tag,
                       '--baseline-mode', mode, '--baseline-seconds', str(seconds)]
            if mode == 'nav':
                command += ['--goal', '7', '-4', '1', '--budget', '180']
            started = time.monotonic()
            print('START ' + mode, flush=True)
            with (output / (mode + '_driver.log')).open('w') as log:
                process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                           start_new_session=True)
                try:
                    rc = process.wait(timeout=1000)
                except subprocess.TimeoutExpired:
                    # TERM the owner shell first so its existing EXIT cleanup can run.
                    process.terminate()
                    try:
                        process.wait(timeout=25)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait()
                    rc = 124
            runs = sorted((runtime / 'vins_smoke_runs').glob('run_' + tag + '_*'))
            run = runs[-1] if runs else None
            entry = {'mode': mode, 'returncode': rc, 'driver_wall_s': time.monotonic() - started,
                     'run_path': str(run) if run else None}
            for name in ('RESULT.txt', 'timing_summary.json', 'landing.json'):
                if run and (run / name).exists():
                    raw = (run / name).read_text()
                    (output / (mode + '_' + name)).write_text(raw)
                    entry[name] = json.loads(raw) if name.endswith('.json') else raw
            status['runs'].append(entry)
            (output / 'suite.json').write_text(json.dumps(status, indent=2) + '\n')
            print('END ' + mode + ' rc=' + str(rc), flush=True)
            if rc == 124:
                print('Timeout: stop suite; inspect owned simulation processes before retry.', flush=True)
                break
    finally:
        (output / 'suite.json').write_text(json.dumps(status, indent=2) + '\n')
    return 0 if len(status['runs']) == len(args.modes) and all(r['returncode'] == 0 for r in status['runs']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
