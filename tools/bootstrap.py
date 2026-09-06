"""雙擊入口共用環境管理；只在專案目錄建立依賴。"""
from pathlib import Path
import hashlib
import importlib.metadata
import os
import subprocess
import sys
import traceback
import venv

ROOT = Path(__file__).resolve().parent.parent


def ensure_environment():
    if sys.version_info[:2] != (3, 12):
        print('需要 Python 3.12.x；目前為 ' + sys.version.split()[0])
        return None, 2
    python = ROOT / '.venv' / 'Scripts' / 'python.exe'
    if not python.exists():
        print('正在建立專案專用環境 .venv…')
        try:
            venv.EnvBuilder(with_pip=True).create(ROOT / '.venv')
        except (OSError, subprocess.SubprocessError) as exc:
            print('無法建立環境：', exc)
            return None, 3
    requirements = ROOT / 'requirements-game.txt'
    digest = hashlib.sha256(requirements.read_bytes()).hexdigest()
    expected = [line.strip().split('==') for line in requirements.read_text(encoding='utf-8').splitlines()
                if line.strip() and not line.startswith('#')]
    check = 'import importlib.metadata as m, sys; sys.exit(0 if all(m.version(n)==v for n,v in ' + repr(expected) + ') else 1)'
    ready = subprocess.run([str(python), '-c', check], capture_output=True).returncode == 0
    if not ready:
        print('正在安裝固定依賴…首次需要網路，或 tools/wheels 中的完整套件快取。')
        command = [str(python), '-m', 'pip', 'install', '--disable-pip-version-check', '-r', str(requirements)]
        wheels = ROOT / 'tools' / 'wheels'
        if wheels.is_dir() and any(wheels.glob('*.whl')):
            command += ['--no-index', '--find-links', str(wheels)]
        with (ROOT / 'artifacts' / 'dependency-install.log').open('w', encoding='utf-8') as log:
            if subprocess.run([str(python), '-m', 'pip', '--version'], stdout=log, stderr=subprocess.STDOUT).returncode:
                repair = subprocess.run([str(python), '-m', 'ensurepip', '--upgrade'], stdout=log, stderr=subprocess.STDOUT)
                if repair.returncode:
                    print('套件安裝工具修復失敗；請查看 artifacts/dependency-install.log。')
                    return None, 4
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
            if not result.returncode:
                result = subprocess.run([str(python), '-c', check], stdout=log, stderr=subprocess.STDOUT)
        if result.returncode:
            print('依賴安裝失敗；請查看 artifacts/dependency-install.log。')
            return None, 4
    (ROOT / '.venv' / 'requirements.sha256').write_text(digest, encoding='ascii')
    return python, 0


def main():
    os.chdir(ROOT)
    (ROOT / 'artifacts').mkdir(exist_ok=True)
    python, error = ensure_environment()
    if error:
        return error
    if len(sys.argv) < 2 or sys.argv[1] not in ('game', 'test', 'check'):
        print('請使用 start_game.cmd 或 run_tests.cmd。')
        return 2
    mode = sys.argv[1]
    if mode == 'check':
        print('Python 3.12.x 與固定依賴已就緒。')
        return 0
    args = ['-m', 'air_defense.main'] if mode == 'game' else [str(ROOT / 'tools' / 'test_runner.py')]
    return subprocess.call([str(python), *args, *sys.argv[2:]], cwd=ROOT)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception:
        (ROOT / 'artifacts').mkdir(exist_ok=True)
        (ROOT / 'artifacts' / 'launcher-error.log').write_text(traceback.format_exc(), encoding='utf-8')
        print('啟動失敗，詳細原因保留於 artifacts/launcher-error.log。')
        raise SystemExit(4)
