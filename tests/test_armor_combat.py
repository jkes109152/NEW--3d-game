import unittest
from air_defense.entities import Player, Enemy, V3
from air_defense.state import BattleState
from air_defense.progression import level_for
from tests.fixtures.expansion import profile

class ArmorCombatTests(unittest.TestCase):
    def test_damage_floor_budget_and_exact_delay(self):
        p=Player(hp=100,max_hp=100,armor=3,regen_delay=2.5,regen_rate=4)
        self.assertEqual(p.hurt(1),1);p.hurt(52);p.tick(2.5);self.assertEqual(p.hp,50)
        p.tick(.5);self.assertEqual(p.hp,52);p.tick(30);self.assertEqual(p.hp,70);self.assertEqual(p.healed,20)
        self.assertEqual(p.hurt(0),0)
    def test_equipped_armor_player_hp_speed_and_city_isolation(self):
        for aid in ('A02','A04','A05'):
            p=profile();p['owned_armors']=[aid];p['confirmed_loadout']['armor_id']=aid;p['player_upgrades']['max_hp']=1
            b=BattleState(p,level_for(1,1,2));before=b.player.position
            b.player.move(1,0,False,1);self.assertAlmostEqual((b.player.position-before).length(),b.loadout.player.move_speed)
            b.enemies['city']=Enemy('city','NORMAL',V3(0,0,-44),phase='ground');b.step(1/120)
            self.assertAlmostEqual(b.city.hp,100-10/120);self.assertEqual(b.player.max_hp,150 if aid=='A05' else 100 if aid=='A04' else 110)
