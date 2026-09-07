"""002 本地審查：保存恢復畫面與過期確認的公開行為回歸。"""
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import Mock, patch

from air_defense.deployment import validate_placement
from air_defense.main import GameController
from air_defense.preparation import PreparationDraft
from air_defense.save_data import SaveError, SlotRepository, validate_profile
from air_defense.state import AppState
from air_defense.ui import GameUI
from tests.fixtures.expansion import profile


class ReviewV2Tests(TestCase):
    def setUp(self):
        folder = TemporaryDirectory(prefix='審查回歸-')
        self.addCleanup(folder.cleanup)
        self.repo = SlotRepository(folder.name)

    def controller(self, data=None):
        self.repo.save(1, data or profile(coins=5000))
        c = object.__new__(GameController)
        c.state = AppState(self.repo)
        c.state.select_slot(1)
        c.ui = Mock()
        c.audio = Mock()
        return c

    def fail_purchase(self, c, kind, **fields):
        before = self.repo.path(1).read_bytes()
        with patch('air_defense.save_data.os.replace', side_effect=PermissionError('故障注入')):
            c.shop_action(kind, **fields)
        self.assertEqual(c.state.screen, 'save_error')
        self.assertEqual(self.repo.path(1).read_bytes(), before)
        candidate = deepcopy(c.state.pending_save.candidate_profile)
        with patch.object(c.state, 'transaction', side_effect=AssertionError('重試不可重算交易')):
            c.retry_save()
        self.assertEqual(c.state.screen, 'weapon_customize')
        self.assertEqual(self.repo.load(1), candidate)
        return candidate

    def render_customization(self, c):
        ui = object.__new__(GameUI)
        ui.controller = c
        for name in ('heading', 'text', 'preview_weapon', 'button'):
            setattr(ui, name, Mock())
        ui.show_weapon_customize()
        return ui.preview_weapon.call_args.args[1]

    def test_purchase_from_preview_retries_into_usable_customization(self):
        c = self.controller()
        c.customize('W04')
        candidate = self.fail_purchase(c, 'purchase_weapon', weapon_id='W04')
        self.assertEqual(self.render_customization(c).weapon_id, 'W04')
        self.assertEqual(c.custom_draft, candidate['owned_weapons']['W04'])
        c.apply_custom()
        self.assertEqual(c.state.screen, 'weapon_customize')
        self.assertEqual(self.repo.load(1)['coins'], candidate['coins'])

    def test_upgrade_retry_updates_preview_and_preserves_unsaved_selection(self):
        data = profile(coins=5000)
        w = data['owned_weapons']['W03']
        w['owned_colors'].append('mint')
        w['owned_attachments'].append('heavy_barrel')
        c = self.controller(data)
        c.customize('W03')
        c.custom_select('selected_color', 'mint')
        c.custom_select('selected_attachments', 'heavy_barrel', 'barrel')
        candidate = self.fail_purchase(c, 'upgrade_weapon', weapon_id='W03', upgrade_id='damage')
        stats = self.render_customization(c)
        self.assertAlmostEqual(stats.base_damage, 1.4375)
        self.assertEqual(stats.color_id, 'mint')
        self.assertEqual(candidate['owned_weapons']['W03']['selected_color'], 'original')
        c.apply_custom()
        saved = self.repo.load(1)
        self.assertEqual(saved['coins'], candidate['coins'])
        self.assertEqual(saved['owned_weapons']['W03']['selected_color'], 'mint')
        self.assertEqual(saved['owned_weapons']['W03']['upgrade_levels']['damage'], 1)

    def test_failed_retry_keeps_error_route_until_write_succeeds(self):
        c = self.controller()
        c.customize('W04')
        with patch('air_defense.save_data.os.replace', side_effect=PermissionError('故障注入')):
            c.shop_action('purchase_weapon', weapon_id='W04')
            c.retry_save()
        self.assertEqual(c.state.screen, 'save_error')
        self.assertNotIn('W04', self.repo.load(1)['owned_weapons'])
        c.retry_save()
        self.assertEqual(self.render_customization(c).weapon_id, 'W04')
        self.assertEqual(len(self.repo.load(1)['operation_history']), 1)

    def test_unrepresentable_coordinates_and_deep_json_offer_recovery(self):
        data = profile(rebirth_count=1)
        instance = 'turret-' + '1' * 32
        data['owned_turrets'] = [dict(instance_id=instance, turret_id='T01')]
        payloads = []
        for value in (10**400, -(10**400), float('inf'), float('nan')):
            data['confirmed_loadout']['deployments'] = [dict(instance_id=instance, x=value, z=0)]
            payloads.append(json.dumps(data).encode())
        deep_json = ('[' * 10000 + '0' + ']' * 10000).encode()
        with self.assertRaises(RecursionError): json.loads(deep_json)
        payloads.append(deep_json)
        self.repo.save(2, profile(coins=123))
        for raw in payloads:
            with self.subTest(payload=raw[:40]):
                self.repo.path(1).write_bytes(raw)
                with self.assertRaises(SaveError) as error:
                    self.repo.load(1)
                self.assertEqual(error.exception.code, 'corrupt')
                rows = self.repo.list_slots()
                self.assertIsNotNone(rows[0][2])
                self.assertEqual(rows[1][1]['coins'], 123)
                backup = self.repo.prepare_recovery(1)
                self.assertEqual(backup.read_bytes(), raw)
                self.assertEqual(self.repo.path(1).read_bytes(), raw)
                self.repo.recover(1, True)
                self.assertEqual(self.repo.load(1)['coins'], 0)

    def test_unrepresentable_coordinate_rejected_without_changing_draft(self):
        data = profile(rebirth_count=1)
        instance = 'turret-' + '1' * 32
        data['owned_turrets'] = [dict(instance_id=instance, turret_id='T01')]
        draft = PreparationDraft.from_profile(data)
        before = deepcopy(draft.loadout)
        for value in (10**400, -(10**400), float('inf'), float('nan'), True):
            with self.subTest(value=str(value)[:30]):
                self.assertEqual(validate_placement(None, (value, 0)), 'invalid_position')
                self.assertEqual(draft.place(data, instance, value, 0), 'invalid_position')
                self.assertEqual(draft.loadout, before)
                invalid = deepcopy(data)
                invalid['confirmed_loadout']['deployments'] = [dict(instance_id=instance, x=value, z=0)]
                with self.assertRaises(ValueError): validate_profile(invalid)

    def test_recovery_confirmation_rejects_changed_or_missing_source(self):
        for change in ('replace', 'remove'):
            with self.subTest(change=change):
                self.repo.path(1).write_bytes(b'original corrupt')
                backup = self.repo.prepare_recovery(1)
                if change == 'replace':
                    self.repo.save(1, profile(coins=987))
                    expected = self.repo.path(1).read_bytes()
                else:
                    self.repo.path(1).unlink()
                    expected = None
                for _ in range(2):
                    with self.assertRaises(SaveError) as error:
                        self.repo.recover(1, True)
                    self.assertEqual(error.exception.code, 'recovery_changed')
                self.assertEqual(self.repo.path(1).read_bytes() if self.repo.path(1).exists() else None, expected)
                self.assertEqual(backup.read_bytes(), b'original corrupt')

    def test_delete_confirmation_rejects_changed_formal_file_or_backups(self):
        for change in ('formal', 'backup', 'added_backup', 'removed_formal'):
            with self.subTest(change=change):
                self.repo.save(1, profile(coins=123))
                backup = self.repo.root / 'slot-1.corrupt.test.json'
                backup.write_bytes(b'original backup')
                token = self.repo.request_delete(1)
                if change == 'formal': self.repo.save(1, profile(coins=987))
                elif change == 'backup': backup.write_bytes(b'restored backup')
                elif change == 'added_backup': (self.repo.root / 'slot-1.corrupt.extra.json').write_bytes(b'new backup')
                else: self.repo.path(1).unlink()
                expected = {p.name: p.read_bytes() for p in self.repo.root.glob('*.json')}
                self.assertFalse(self.repo.confirm_delete(1, token))
                self.assertFalse(self.repo.confirm_delete(1, token))
                self.assertEqual({p.name: p.read_bytes() for p in self.repo.root.glob('*.json')}, expected)
                fresh = self.repo.request_delete(1)
                self.assertTrue(self.repo.confirm_delete(1, fresh))
                self.assertFalse(any(self.repo.root.glob('slot-1*.json')))

    def test_delete_preview_read_failure_is_visible_and_preserves_file(self):
        c = self.controller()
        before = self.repo.path(1).read_bytes()
        with patch.object(Path, 'read_bytes', side_effect=PermissionError('故障注入')):
            c.request_delete(1)
        self.assertEqual(c.state.screen, 'profile_menu')
        self.assertEqual(self.repo.path(1).read_bytes(), before)
        c.ui.toast.assert_called_once()
