import unittest
from dataclasses import replace
from math import nan,inf
from air_defense.deployment import WORLD,WorldDefinition,validate_placement,validate_deployment,range_preview
from air_defense.entities import V3
from air_defense.preparation import PreparationDraft
from tests.fixtures.expansion import profile,operation_id

class DeploymentTests(unittest.TestCase):
    def test_geometry_boundaries(self):
        empty=WorldDefinition(boxes=(),enemy_route=(),player_spawn=V3(0,0,0))
        self.assertIsNone(validate_placement(empty,(58.5,100)));self.assertEqual(validate_placement(empty,(58.501,100)),'outside_map')
        self.assertIsNone(validate_placement(empty,(13,10),[dict(x=10,z=10)]));self.assertEqual(validate_placement(empty,(12.99,10),[dict(x=10,z=10)]),'overlap')
        self.assertEqual(validate_placement(empty,(4.5,0)),'spawn_reserved');self.assertIsNone(validate_placement(empty,(4.501,0)))
        world=replace(empty,boxes=((V3(20,1,20),V3(2,2,2)),))
        self.assertEqual(validate_placement(world,(22.5,20)),'blocked_ground');self.assertIsNone(validate_placement(world,(22.501,20)))
        world=replace(empty,enemy_route=(V3(-10,0,20),V3(10,0,20)))
        self.assertEqual(validate_placement(world,(0,23.5)),'route_reserved');self.assertIsNone(validate_placement(world,(0,23.501)))
        for x in (nan,inf,True):self.assertEqual(validate_placement(empty,(x,10)),'invalid_position')
    def test_move_excludes_self_cancel_preserves_profile_and_invalid_history_removed(self):
        p=profile(rebirth_count=1);key='turret-'+operation_id();p['owned_turrets']=[dict(instance_id=key,turret_id='T01')]
        p['confirmed_loadout']['deployments']=[dict(instance_id=key,x=200,z=200)]
        d=PreparationDraft.from_profile(p);self.assertEqual(d.loadout['deployments'],[]);self.assertTrue(d.messages)
        self.assertIsNone(d.place(p,key,40,100));self.assertIsNone(d.place(p,key,41,100));self.assertEqual(len(d.loadout['deployments']),1)
        self.assertEqual(d.place(p,key,1000,100),'outside_map');self.assertEqual(d.loadout['deployments'][0]['x'],41)
        self.assertEqual(p['confirmed_loadout']['deployments'][0]['x'],200)
        self.assertEqual(len(range_preview((40,100),32)),1152)
