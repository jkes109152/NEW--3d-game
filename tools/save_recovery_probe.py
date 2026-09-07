"""保存例外的離屏引擎回歸；只使用臨時存檔與真實 UI 回呼。"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import argparse
from copy import deepcopy
import json
from tempfile import TemporaryDirectory
from unittest.mock import patch

from air_defense.main import create_game
from air_defense.save_data import SlotRepository
from tests.fixtures.expansion import profile
from tools.engine_probe import screenshot


def run(size, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    report = dict(category='離屏引擎 UI 回呼，非人工鍵鼠或效能量測',
                  resolution=size, cases=[], screenshots=[])
    with TemporaryDirectory(prefix='保存審查-') as folder:
        repo = SlotRepository(folder)
        p = profile(coins=5000)
        p['owned_weapons']['W03']['owned_colors'].append('mint')
        p['owned_weapons']['W03']['owned_attachments'].append('heavy_barrel')
        repo.save(1, p)
        engine, c = create_game(size, repository=repo, silent=True, offscreen=True)
        c.focus_checks = False
        c.bridge.update = lambda: None
        try:
            def shot(name):
                screenshot(engine, output / f'{name}.png')
                report['screenshots'].append(name)

            def texts():
                return [str(node.text) for node in c.ui.layer.children if getattr(node, 'text', '')]

            c.select_slot(1)
            c.customize('W04')
            assert '尚未擁有' in '\n'.join(texts())
            shot('purchase-preview')
            purchase_click = c.ui.buttons[2].on_click
            before = repo.path(1).read_bytes()
            with patch('air_defense.save_data.os.replace', side_effect=PermissionError('故障注入')):
                purchase_click()
            assert c.state.screen == 'save_error' and repo.path(1).read_bytes() == before
            candidate = deepcopy(c.state.pending_save.candidate_profile)
            shot('purchase-save-error')
            c.input('enter')
            purchase_click()
            assert c.state.screen == 'weapon_customize'
            assert c.custom_draft == candidate['owned_weapons']['W04']
            assert repo.load(1) == candidate
            assert '套用自訂' in texts()
            shot('purchase-retried')
            report['cases'].append('新購武器重試、工坊建立、舊回呼不重扣')

            c.customize('W03')
            c.custom_select('selected_color', 'mint')
            c.custom_select('selected_attachments', 'heavy_barrel', 'barrel')
            with patch('air_defense.save_data.os.replace', side_effect=PermissionError('故障注入')):
                c.ui.buttons[5].on_click()
            assert c.state.screen == 'save_error'
            candidate = deepcopy(c.state.pending_save.candidate_profile)
            c.input('enter')
            assert c.custom_draft['upgrade_levels']['damage'] == 1
            assert c.custom_draft['selected_color'] == 'mint'
            assert '基礎傷害 1.00 → 1.44' in '\n'.join(texts())
            assert repo.load(1) == candidate
            shot('upgrade-retried')
            c.ui.buttons[-2].on_click()
            assert repo.load(1)['owned_weapons']['W03']['selected_color'] == 'mint'
            assert repo.load(1)['coins'] == candidate['coins']
            report['cases'].append('升級重試同步能力、保留草稿並可免費套用')

            c.back()
            c.back()
            c.return_slots()
            damaged = profile(rebirth_count=1)
            instance = 'turret-' + '1' * 32
            damaged['owned_turrets'] = [dict(instance_id=instance, turret_id='T01')]
            damaged['confirmed_loadout']['deployments'] = [dict(instance_id=instance, x=10**400, z=0)]
            raw = json.dumps(damaged).encode()
            repo.path(3).write_bytes(raw)
            c.route('slot_select')
            shot('corrupt-slot-list')
            c.select_slot(3)
            assert c.state.screen == 'recover_confirm'
            assert repo.path(3).read_bytes() == raw
            c.ui.buttons[1].on_click()
            assert c.state.screen == 'profile_menu' and repo.load(3)['coins'] == 0
            assert any(path.read_bytes() == raw for path in repo.root.glob('slot-3.corrupt.*.json'))
            report['cases'].append('巨大座標安全選檔、原始備份及確認重建')

            c.return_slots()
            repo.path(4).write_bytes(b'original corrupt')
            c.select_slot(4)
            repo.save(4, profile(coins=321))
            expected = repo.path(4).read_bytes()
            for _ in range(2):
                c.ui.buttons[1].on_click()
                assert c.state.screen == 'recover_confirm'
                assert repo.path(4).read_bytes() == expected
            assert '已變更' in c.ui.last_toast
            shot('stale-recovery-preserved')
            report['cases'].append('舊復原確認連按不覆寫已變更存檔')
            c.back()
            c.select_slot(4)
            assert c.state.profile['coins'] == 321
            c.return_slots()

            c.request_delete(4)
            delete_click = c.ui.buttons[1].on_click
            repo.save(4, profile(coins=654))
            expected = repo.path(4).read_bytes()
            delete_click()
            delete_click()
            assert c.state.screen == 'slot_select'
            assert repo.path(4).read_bytes() == expected
            assert '失效' in c.ui.last_toast
            shot('stale-delete-preserved')
            report['cases'].append('舊刪除確認及延遲回呼不刪除新內容')
            c.request_delete(4)
            c.ui.buttons[1].on_click()
            assert not any(repo.root.glob('slot-4*.json'))
            assert repo.load(1) is not None and repo.load(3) is not None
            report['cases'].append('重新確認可刪除，其他欄位保留')
            report['status'] = 'PASS'
        finally:
            (output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            c.window_listener.ignoreAll()
            engine.destroy()
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--width', type=int, default=1280)
    parser.add_argument('--height', type=int, default=720)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run((args.width, args.height), args.output)
