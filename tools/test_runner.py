"""將測試輸出與退出碼保存，強制隔離玩家資料。"""
from pathlib import Path
import os
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent


def main():
    (ROOT / 'artifacts').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='air-defense-tests-') as profile_root:
        env = dict(os.environ, AIR_DEFENSE_V2_SAVE_DIR=profile_root, LOCALAPPDATA=profile_root, PYTHONUTF8='1')
        env.pop('AIR_DEFENSE_SAVE_DIR', None)
        commands = [[sys.executable, '-m', 'compileall', '-q', 'air_defense', 'tools', 'tests'],
                    [sys.executable, '-m', 'unittest', *(sys.argv[1:] or ['discover', '-v'])]]
        result = 0
        with (ROOT / 'artifacts' / 'tests.log').open('w', encoding='utf-8') as log:
            for cmd in commands:
                log.write('指令：' + subprocess.list2cmdline(cmd) + '\n')
                p = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, encoding='utf-8', errors='replace')
                text = p.stdout + p.stderr
                print(text, end='')
                log.write(text + '\n退出碼：' + str(p.returncode) + '\n')
                result = result or p.returncode
    evidence = ROOT / 'artifacts' / '002-gameplay-expansion'
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / 'tests.log').write_bytes((ROOT / 'artifacts' / 'tests.log').read_bytes())
    return result


if __name__ == '__main__':
    raise SystemExit(main())
