"""環境修復分支以隔離目錄驗證，不建立或變動系統 Python。"""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import Mock, patch
from tools import bootstrap


class LauncherContractTests(TestCase):
    def test_existing_environment_without_pip_is_repaired_before_install(self):
        with TemporaryDirectory() as directory:
            root=Path(directory); python=root/'.venv'/'Scripts'/'python.exe'
            python.parent.mkdir(parents=True); python.touch()
            (root/'artifacts').mkdir()
            (root/'requirements-game.txt').write_text('ursina==8.3.0\n',encoding='utf-8')
            calls=[]
            def run(command,**kwargs):
                calls.append(command)
                if '-c' in command: return Mock(returncode=0 if any('install' in cmd for cmd in calls) else 1)
                if '--version' in command: return Mock(returncode=1)
                return Mock(returncode=0)
            with patch.object(bootstrap,'ROOT',root),patch.object(bootstrap.subprocess,'run',side_effect=run):
                self.assertEqual(bootstrap.ensure_environment(),(python,0))
            repair=next(i for i,cmd in enumerate(calls) if 'ensurepip' in cmd)
            install=next(i for i,cmd in enumerate(calls) if 'install' in cmd)
            self.assertLess(repair,install)

    def test_failed_pip_repair_returns_error_and_does_not_mark_ready(self):
        with TemporaryDirectory() as directory:
            root=Path(directory); python=root/'.venv'/'Scripts'/'python.exe'
            python.parent.mkdir(parents=True); python.touch(); (root/'artifacts').mkdir()
            (root/'requirements-game.txt').write_text('ursina==8.3.0\n',encoding='utf-8')
            calls=[]
            def run(command,**kwargs):
                calls.append(command)
                return Mock(returncode=1 if 'ensurepip' in command or '--version' in command or '-c' in command else 0)
            with patch.object(bootstrap,'ROOT',root),patch.object(bootstrap.subprocess,'run',side_effect=run):
                self.assertEqual(bootstrap.ensure_environment(),(None,4))
            self.assertFalse((root/'.venv'/'requirements.sha256').exists())
            self.assertFalse(any('install' in cmd for cmd in calls))
