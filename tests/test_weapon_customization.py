import unittest
from copy import deepcopy
from air_defense.catalog import ATTACHMENTS
from air_defense.loadout import resolve_weapon_stats,resolve_loadout
from air_defense.progression import transact
from tests.fixtures.expansion import profile,request,operation_id,owned_weapon

class CustomizationTests(unittest.TestCase):
    def test_all_seven_attachments_effects_and_costs(self):
        for i,(aid,wid,field,value) in enumerate([('zoom_scope','W17','aim_factor',6.0),('guidance_scope','W01','lock_seconds',3.3),('heavy_barrel','W03','base_damage',1.15),('extended_magazine','W03','magazine_size',18),('quick_reload','W03','magazine_size',9),('cooling_guidance','W01','interval',1.0625),('light_loading_rack','W19','blast_radius',5.1)]):
            p=profile(coins=5000);p['owned_weapons'].setdefault(wid,owned_weapon());sel=dict(optic=None,barrel=None,feed=None)
            self.assertEqual(transact(p,operation_id(),request(p,'purchase_attachment',weapon_id=wid,attachment_id=aid))['result_code'],'applied')
            self.assertEqual(p['owned_weapons'][wid]['selected_attachments'],sel)
            sel[ATTACHMENTS[aid].slot]=aid
            self.assertEqual(transact(p,operation_id(2),request(p,'customize_weapon',weapon_id=wid,selected_attachments=sel,selected_color='original',selected_pattern='plain'))['coins_delta'],0)
            self.assertAlmostEqual(getattr(resolve_weapon_stats(p,wid),field),value)
    def test_order_preview_snapshot_and_weapon_isolation(self):
        p=profile(coins=9999);w=p['owned_weapons']['W17'];w['upgrade_levels'].update(damage=2,range=2,cooldown=2)
        w['owned_attachments']=['heavy_barrel','zoom_scope'];w['selected_attachments'].update(barrel='heavy_barrel',optic='zoom_scope')
        s=resolve_weapon_stats(p,'W17');self.assertAlmostEqual(s.base_damage,3.45);self.assertEqual(s.range,240);self.assertAlmostEqual(s.interval,.7425)
        snapshot=resolve_loadout(p);w['upgrade_levels']['damage']=4
        self.assertEqual(snapshot.weapons['W17'].base_damage,s.base_damage)
        with self.assertRaises(TypeError):snapshot.weapons['W17'].values['base_damage']=8
    def test_cosmetic_ownership_free_reselection_and_incompatible_attachment(self):
        p=profile(coins=1000)
        transact(p,operation_id(),request(p,'purchase_cosmetic',weapon_id='W17',cosmetic_kind='color',cosmetic_id='mint'))
        self.assertEqual(p['coins'],925);self.assertEqual(p['owned_weapons']['W17']['selected_color'],'original')
        req=request(p,'customize_weapon',weapon_id='W17',selected_attachments=dict(optic=None,barrel=None,feed=None),selected_color='mint',selected_pattern='plain')
        for i in (2,3):self.assertEqual(transact(p,operation_id(i),req)['coins_delta'],0)
        self.assertNotIn('mint',p['owned_weapons']['W03']['owned_colors'])
        self.assertEqual(transact(p,operation_id(4),request(p,'purchase_attachment',weapon_id='W03',attachment_id='cooling_guidance'))['reason'],'incompatible')
