"""結算後公開出戰入口、保存重試與玩家持有成果的回歸。"""
from copy import deepcopy
import unittest
from unittest.mock import patch

from air_defense.save_data import SaveError, SlotRepository
from air_defense.state import AppState
from tests.fixtures.expansion import isolated_roots, start_prepared


class ResultNavigationTests(unittest.TestCase):
    def make_app(self, root, cursor, rebirth_count=1):
        app = AppState(SlotRepository(root))
        app.select_slot(1)
        app.profile['rebirth_count'] = rebirth_count
        app.profile['coins'] = 5000
        app.repository.save(1, app.profile)
        app.cursor = cursor
        return app

    @staticmethod
    def win(battle):
        for aircraft in battle.aircraft.values():
            aircraft.status = 'destroyed'
            aircraft.hp = 0
        battle.check_outcome()

    def test_defeat_restarts_1_1_and_keeps_owned_progress(self):
        for cursor, reason in (((1, 2), 'player'), ((2, 3), 'city'), ((3, 1), 'impact')):
            with self.subTest(cursor=cursor, reason=reason), isolated_roots() as (root, _):
                app = self.make_app(root, cursor)
                for kind, fields in (
                    ('purchase_weapon', {'weapon_id': 'W06'}),
                    ('purchase_armor', {'armor_id': 'A02'}),
                    ('purchase_turret', {'turret_id': 'T01'}),
                ):
                    self.assertEqual(app.transaction(kind, **fields)['result_code'], 'applied')
                battle = start_prepared(app)
                kept = {k: deepcopy(v) for k, v in app.profile.items()
                        if k not in ('profile_revision', 'operation_history', 'rebirth_available')}
                battle.fail(reason)
                app.settle()
                self.assertEqual(app.screen, 'result_failure')
                self.assertEqual(app.cursor, (1, 1))
                self.assertEqual(app.last_result['level'], f'{cursor[0]}-{cursor[1]}')
                self.assertEqual(app.last_result['reward'], 0)
                self.assertTrue(app.profile['rebirth_available'])
                for key, value in kept.items():
                    self.assertEqual(app.profile[key], value, key)
                self.assertEqual(app.repository.load(1), app.profile)
                self.assertIsNone(app.begin_preparation())
                app.show_menu()
                fresh = start_prepared(app)
                self.assertEqual(fresh.level.level_id, '1-1')
                self.assertEqual(fresh.level.A, 3)
                self.assertNotEqual(fresh.attempt_id, battle.attempt_id)

    def test_defeat_save_retry_resets_only_after_persistence(self):
        with isolated_roots() as (root, _):
            app = self.make_app(root, (3, 1))
            battle = start_prepared(app)
            saved = app.repository.load(1)
            battle.fail('city')
            with patch.object(app.repository, 'save', side_effect=SaveError('write_failed', '故障注入')):
                app.settle()
            self.assertEqual((app.screen, app.cursor), ('save_error', (3, 1)))
            candidate = deepcopy(app.profile)
            self.assertEqual(app.repository.load(1), saved)
            self.assertIsNone(app.begin_preparation())
            app.show_menu()
            app.settle()
            self.assertEqual(app.screen, 'save_error')
            self.assertTrue(app.retry_save())
            self.assertEqual((app.screen, app.cursor), ('result_failure', (1, 1)))
            app.settle()
            self.assertTrue(app.retry_save())
            self.assertEqual(app.profile, candidate)
            self.assertEqual(app.repository.load(1), candidate)
            app.show_menu()
            self.assertEqual(start_prepared(app).level.level_id, '1-1')

    def test_victory_enters_actual_next_stage_preparation(self):
        cases = ((0, (1, 1), (1, 2)), (0, (1, 2), (2, 1)),
                 (1, (2, 3), (3, 1)), (1, (3, 7), (1, 1)))
        for rebirth, cursor, following in cases:
            with self.subTest(cursor=cursor), isolated_roots() as (root, _):
                app = self.make_app(root, cursor, rebirth)
                battle = start_prepared(app)
                coins = app.profile['coins']
                self.win(battle)
                app.settle()
                self.assertEqual((app.screen, app.cursor), ('result_success', following))
                self.assertEqual(app.profile['coins'], coins + battle.level.reward)
                settled = deepcopy(app.profile)
                self.assertIsNotNone(app.begin_preparation())
                self.assertEqual(app.screen, 'prepare_armor')
                self.assertIsNone(app.battle)
                self.assertIsNone(app.begin_preparation())
                app.cancel_preparation()
                self.assertEqual((app.screen, app.cursor), ('profile_menu', following))
                self.assertEqual(app.profile, settled)
                fresh = start_prepared(app)
                self.assertEqual(fresh.level.level_id, f'{following[0]}-{following[1]}')
                self.assertNotEqual(fresh.attempt_id, battle.attempt_id)
                self.assertEqual(app.profile['coins'], settled['coins'])

    def test_victory_retry_does_not_bypass_save_or_repeat_reward(self):
        with isolated_roots() as (root, _):
            app = self.make_app(root, (2, 3))
            battle = start_prepared(app)
            self.win(battle)
            with patch.object(app.repository, 'save', side_effect=SaveError('write_failed', '故障注入')):
                app.settle()
            self.assertEqual((app.screen, app.cursor), ('save_error', (2, 3)))
            self.assertIsNone(app.begin_preparation())
            candidate = deepcopy(app.profile)
            app.settle()
            self.assertTrue(app.retry_save())
            self.assertEqual((app.screen, app.cursor), ('result_success', (3, 1)))
            self.assertIsNotNone(app.begin_preparation())
            app.settle()
            self.assertEqual(app.profile, candidate)
            self.assertEqual(app.repository.load(1), candidate)
