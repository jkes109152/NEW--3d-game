"""結算導覽的離屏引擎驗證；隔離局面不作真人輸入或通關證據。"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import argparse
import json
from tempfile import TemporaryDirectory

from air_defense.main import create_game
from air_defense.save_data import SlotRepository
from tools.engine_probe import screenshot, start


def run(size, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    report = {'category': '離屏引擎按鈕／鍵盤入口；非原生輸入或通關',
              'resolution': size, 'screenshots': [], 'cases': []}
    with TemporaryDirectory(prefix='結算導覽-') as folder:
        repo = SlotRepository(folder)
        engine, c = create_game(size, repository=repo, silent=True, offscreen=True)
        c.focus_checks = False
        c.bridge.update = lambda: None
        try:
            def shot(name):
                screenshot(engine, output / f'{name}.png')
                report['screenshots'].append(name)

            def texts():
                return [str(node.text) for node in c.ui.layer.children
                        if getattr(node, 'text', '')]

            def fixture(slot, rebirth, cursor):
                c.select_slot(slot)
                c.state.profile['rebirth_count'] = rebirth
                c.state.profile['coins'] = 70
                repo.save(slot, c.state.profile)
                c.state.cursor = cursor

            def finish(battle, success):
                if success:
                    for aircraft in battle.aircraft.values():
                        aircraft.status = 'destroyed'
                        aircraft.hp = 0
                    battle.check_outcome()
                else:
                    battle.fail('player')
                c.state.settle()
                c.release_mouse()
                c.ui.show()

            fixture(1, 1, (3, 1))
            for _ in range(4):
                engine.step()
            baseline = c.metrics()
            battle = start(c)
            finish(battle, False)
            assert c.state.cursor == (1, 1)
            assert '返回主選單' in texts()
            assert any('下一次出擊 1-1' in text for text in texts())
            shot('failure-3-1')
            old_click = c.ui.buttons[0].on_click
            c.input('enter')
            assert c.state.screen == 'profile_menu'
            assert any('開始防守    1-1' == text for text in texts())
            old_click()
            assert c.state.screen == 'profile_menu'
            shot('failure-menu-1-1')
            fresh = start(c)
            assert fresh.level.level_id == '1-1'
            assert fresh.attempt_id != battle.attempt_id
            assert c.state.profile['coins'] == 70
            shot('failure-restarted-1-1')
            report['cases'].append({'result': 'failure', 'level': '3-1', 'next': '1-1',
                                    'menu_label': '開始防守    1-1', 'coins': 70})
            c.leave_battle()

            cases = ((2, 0, (1, 1), (1, 2)), (3, 0, (1, 2), (2, 1)),
                     (4, 1, (2, 3), (3, 1)), (5, 1, (3, 7), (1, 1)))
            for slot, rebirth, cursor, following in cases:
                fixture(slot, rebirth, cursor)
                battle = start(c)
                finish(battle, True)
                level = battle.level.level_id
                next_stage = f'{following[0]}-{following[1]}'
                label = f'前往下一關（{next_stage}）'
                assert label in texts(), texts()
                assert '返回主選單' not in texts()
                result_texts = texts()
                shot(f'success-{level}-next-{next_stage}')
                old_click = c.ui.buttons[0].on_click
                coins = c.state.profile['coins']
                if slot % 2:
                    c.input('enter')
                else:
                    old_click()
                assert c.state.screen == 'prepare_armor'
                assert c.state.battle is None
                assert c.state.cursor == following
                draft = c.state.draft
                old_click()
                assert c.state.draft is draft and draft.step == 0
                assert c.state.profile['coins'] == coins
                clean = c.metrics()
                for key in ('visuals', 'effects', 'active_missiles', 'active_rockets',
                            'pending_commands', 'core_tracers', 'lock_markers'):
                    assert clean[key] == 0, (key, clean)
                shot(f'prepare-next-{level}-to-{next_stage}')
                for _ in range(3):
                    c.prep_next()
                assert any(next_stage in text for text in texts())
                c.confirm_start()
                c.release_mouse()
                assert c.state.battle.level.level_id == next_stage
                assert c.state.battle.attempt_id != battle.attempt_id
                assert c.state.profile['coins'] == coins
                shot(f'started-next-{level}-to-{next_stage}')
                report['cases'].append({'result': 'success', 'level': level,
                                        'next': next_stage, 'button': label,
                                        'input': 'enter' if slot % 2 else 'button.on_click',
                                        'result_texts': result_texts, 'stale_click_ignored': True,
                                        'preparation_cleanup': clean})
                c.leave_battle()

            # Esc 仍可在勝利結果返回商店／重生所在的主選單。
            battle = start(c)
            finish(battle, True)
            c.input('escape')
            assert c.state.screen == 'profile_menu' and c.state.cursor == (1, 2)
            assert any('開始防守    1-2' == text for text in texts())
            shot('success-escape-menu-1-2')
            metrics = c.metrics()
            differences = {key: metrics[key] - baseline[key] for key in baseline}
            assert not any(differences.values()), differences
            report.update(escape_to_menu=True, baseline=baseline, final_metrics=metrics,
                          active_differences=differences, status='PASS')
            (output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            print(json.dumps(report, ensure_ascii=False))
            return report
        finally:
            c.window_listener.ignoreAll()
            engine.destroy()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--size', choices=('1280x720', '1920x1080'), required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(tuple(map(int, args.size.split('x'))), args.output)
