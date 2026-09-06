from tests.fixtures.expansion import operation_id, request
"""本地程式碼審查發現的邊界與故障回歸。"""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import Mock, patch

from air_defense.audio import AudioBus
from air_defense.combat import ray_target
from air_defense.entities import Enemy, V3, angles
from air_defense.progression import new_profile, transact
from air_defense.save_data import SaveError, SlotRepository, validate_profile
from air_defense.state import AppState, InputFrame
from tests.fixtures import battle


class ReviewRegressions(TestCase):
    def test_visible_head_above_cover_accepts_actual_ray_hit(self):
        b=battle(); b.player.position=V3(-29,0,72); b.player.weapon_slot=3
        enemy=Enemy('exposed','NORMAL',V3(-29,1,79))
        b.enemies[enemy.id]=enemy
        b.player.yaw,b.player.pitch=angles(V3(-29,2.7,78.7)-b.player.eye)
        self.assertEqual(ray_target(b.player,b.enemies)[0],enemy.id)
        self.assertEqual(b.fire(),'applied')
        self.assertEqual(enemy.hp,2)

    def test_city_failure_stops_same_enemy_before_player_damage(self):
        b=battle(); b.player.position=V3(0,0,-40); b.city.hp=.01
        b.enemies['e']=Enemy('e','NORMAL',V3(0,0,-44),phase='ground')
        b.advance(1/120,InputFrame())
        self.assertEqual(b.failure_reason,'city')
        self.assertEqual(b.player.hp,100)
        self.assertFalse(any(e['kind']=='player_hurt' for e in b.events))

    def test_aim_change_survives_frame_without_fixed_step(self):
        b=battle()
        b.advance(1/1000,InputFrame(aim_held=True))
        b.advance(1/120,InputFrame())
        self.assertTrue(b.player.aiming)
        b.advance(1/1000,InputFrame(aim_held=False))
        b.advance(1/120,InputFrame())
        self.assertFalse(b.player.aiming)

    def test_newer_aim_input_wins_over_pending_frame(self):
        b=battle()
        b.advance(1/1000,InputFrame(aim_held=True))
        b.advance(1/120,InputFrame(aim_held=False))
        self.assertFalse(b.player.aiming)

    def test_invalid_transaction_never_poison_profile(self):
        for request in ({'kind':'unknown'},{'kind':'purchase','upgrade_id':[]},
                        {'kind':'reward','a':1,'b':1},{'kind':'save','extra':True}):
            with self.subTest(request=request):
                p=new_profile(); before=deepcopy(p)
                self.assertEqual(transact(p,operation_id(),request)['reason'],'invalid_request')
                self.assertEqual(p,before)
                validate_profile(p)

    def test_stale_campaign_reward_conflict_does_not_mutate(self):
        p=new_profile(); before=deepcopy(p)
        req=request(p,'reward',a=1,b=1,A=3);req['rebirth_count']=1
        self.assertEqual(transact(p,operation_id(),req)['reason'],'invalid_round')
        self.assertEqual(p,before)

    def test_transaction_validates_destination_before_mutation(self):
        with TemporaryDirectory() as root:
            repo=SlotRepository(root); p=repo.create(1); p['coins']=500; before=deepcopy(p)
            with self.assertRaises(ValueError): repo.transaction(6,p,'buy',{'kind':'purchase','upgrade_id':'max_hp'})
            self.assertEqual(p,before)

    def test_pending_save_cannot_be_discarded_by_slot_selection(self):
        with TemporaryDirectory() as root:
            app=AppState(SlotRepository(root)); app.select_slot(1); app.profile['coins']=1000
            with patch('air_defense.save_data.os.replace',side_effect=PermissionError('故障注入')):
                self.assertEqual(app.purchase('max_hp',operation_id()),'save_failed')
            before=deepcopy(app.profile)
            with self.assertRaises(SaveError): app.select_slot(2)
            self.assertEqual(app.slot,1); self.assertEqual(app.profile,before)
            self.assertFalse(app.repository.path(2).exists())

    def test_changed_backup_is_recreated_before_recovery(self):
        with TemporaryDirectory() as root:
            repo=SlotRepository(root); original=b'original damaged json'
            repo.path(1).write_bytes(original)
            backup=repo.prepare_recovery(1); backup.write_bytes(b'truncated')
            repo.recover(1,True)
            self.assertTrue(any(path.read_bytes()==original for path in Path(root).glob('slot-1.corrupt.*.json')))

    def test_delete_invalidates_other_tokens_for_same_slot(self):
        with TemporaryDirectory() as root:
            repo=SlotRepository(root); repo.create(1)
            first=repo.request_delete(1); stale=repo.request_delete(1)
            self.assertTrue(repo.confirm_delete(1,first)); repo.create(1)
            self.assertFalse(repo.confirm_delete(1,stale))
            self.assertIsNotNone(repo.load(1))

    def test_audio_device_loss_during_status_or_stop_is_nonfatal(self):
        for method in ('status','stop'):
            with self.subTest(method=method):
                voice=Mock(); getattr(voice,method).side_effect=RuntimeError('音訊裝置已移除')
                bus=AudioBus(); bus.silent=False; bus.voices=[voice]
                (bus.tick if method=='status' else bus.stop)()
                self.assertEqual(bus.voices,[])
                self.assertTrue(bus.silent)

    def test_delete_ui_reports_expired_confirmation_and_returns_after_error(self):
        from air_defense.main import GameController
        for outcome in (False, SaveError('delete_failed','刪除失敗')):
            with self.subTest(outcome=outcome):
                controller=object.__new__(GameController)
                controller.state=Mock(); controller.ui=Mock(); controller.route=Mock()
                controller.dialog_slot=1; controller.delete_token='old-token'
                delete=controller.state.repository.confirm_delete
                if isinstance(outcome, Exception): delete.side_effect=outcome
                else: delete.return_value=outcome
                controller.confirm_delete()
                self.assertIsNone(controller.delete_token)
                controller.route.assert_called_once_with('slot_select')
                self.assertNotEqual(controller.ui.toast.call_args.args[0],'已刪除此欄位')
                self.assertIn('失',controller.ui.toast.call_args.args[0])
