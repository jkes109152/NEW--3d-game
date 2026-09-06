import unittest
from air_defense.entities import Enemy,V3
from air_defense.progression import level_for
from air_defense.state import BattleState
from tests.fixtures.expansion import profile


class ArmorMatrixTests(unittest.TestCase):
    def test_each_armor_actual_move_jump_damage_regeneration_and_city(self):
        cases=[('A01',120,6,0,5,4),('A02',120,5.4,3,5,2),('A03',130,6,1,5,3),
               ('A04',110,7.2,0,5,2),('A05',160,5.7,0,5,2),('A06',120,6,0,2.5,2)]
        for aid,hp,speed,reduction,delay,rate in cases:
            with self.subTest(armor=aid):
                p=profile();p['player_upgrades']['max_hp']=2;p['owned_armors']=[aid];p['confirmed_loadout']['armor_id']=aid
                b=BattleState(p,level_for(1,1,2));player=b.player;before=player.position
                self.assertEqual(player.max_hp,hp);player.move(1,0,False,1)
                self.assertAlmostEqual((player.position-before).length(),speed)
                self.assertEqual(player.hurt(60+reduction),60);wounded=player.hp
                player.tick(delay-.01);self.assertEqual(player.hp,wounded)
                player.tick(.02);self.assertAlmostEqual(player.hp,wounded+.01*rate)
                player.tick(40);self.assertAlmostEqual(player.healed,.2*hp)
                self.assertEqual(player.hurt(1),1)
                peak=0
                for i in range(240):player.move(0,0,i==0,1/120);peak=max(peak,player.position.y)
                self.assertAlmostEqual(peak,1.8,delta=.04)
                b.enemies['city']=Enemy('city','NORMAL',V3(0,0,-44),phase='ground')
                b.step(1/120);self.assertAlmostEqual(b.city.hp,100-10/120)
