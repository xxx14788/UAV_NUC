#!/usr/bin/env python3
"""Freeze source/config/binary identities without changing the tested stack."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile
from datetime import datetime, timezone


def command(args, cwd=None):
    return subprocess.check_output(args, cwd=cwd, text=True).strip()


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=False)
    tracked = command(['git', 'ls-files', '-z'], root).split('\0')
    source_hashes = {p: digest(root / p) for p in tracked if p and (root / p).is_file()}
    keys = ['devel/lib/vins/vins_node', 'devel/lib/libvins_lib.so',
            'devel/lib/px4ctrl/px4ctrl_node', 'devel/lib/ego_planner/ego_planner_node',
            'devel/lib/ego_planner/traj_server',
            'devel/lib/vins_to_mavros/vins_to_mavros_node']
    px4 = Path(os.environ.get('PX4_DIR', str(Path.home() / 'PX4-Autopilot')))
    binaries = {p: digest(root / p) for p in keys if (root / p).is_file()}
    libraries = {}
    for path in (root / 'devel/lib').glob('*.so*'):
        if path.is_file():
            libraries[str(path.relative_to(root))] = digest(path)
    px4_binary = px4 / 'build/px4_sitl_default/bin/px4'
    if px4_binary.is_file():
        binaries['px4_sitl_default/bin/px4'] = digest(px4_binary)
    manifest = {'captured_utc': datetime.now(timezone.utc).isoformat(),
                'git_head': command(['git', 'rev-parse', 'HEAD'], root),
                'git_branch': command(['git', 'branch', '--show-current'], root),
                'git_status': command(['git', 'status', '--porcelain'], root),
                'px4_head': command(['git', 'rev-parse', 'HEAD'], px4),
                'px4_status': command(['git', 'status', '--porcelain'], px4),
                'source_sha256': source_hashes, 'binary_sha256': binaries,
                'workspace_library_sha256': libraries,
                'binary_dependencies': {p: command(['ldd', str(root / p)]) for p in keys},
                'scope': 'default headless; Gazebo depth; no GPU/bridge/R7 changes'}
    required = set(keys) - set(binaries)
    if required or not px4_binary.is_file():
        raise SystemExit('Missing baseline binaries: ' + str(sorted(required)))
    with tarfile.open(out / 'config_binary_snapshot.tar.gz', 'w:gz') as archive:
        for p in tracked:
            if p and (root / p).is_file() and (p.startswith('docker/') or
                    p in ('compose.yaml', '.devcontainer/devcontainer.json') or
                    (p.startswith(('src/', 'sitl_sim/')) and
                     ('/config/' in p or '/launch/' in p or '/models/' in p or
                      '/worlds/' in p or p.endswith('.sh')))):
                archive.add(root / p, arcname='workspace/' + p, recursive=False)
        for p in keys:
            archive.add((root / p).resolve(), arcname='workspace/' + p, recursive=False)
        for p in libraries:
            if p not in keys:
                archive.add((root / p).resolve(), arcname='workspace/' + p, recursive=False)
        archive.add(px4_binary.resolve(), arcname='px4/px4', recursive=False)
    manifest['snapshot_sha256'] = digest(out / 'config_binary_snapshot.tar.gz')
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'output': str(out), 'head': manifest['git_head'],
                      'sources': len(source_hashes), 'binaries': len(binaries)}))


if __name__ == '__main__':
    main()
