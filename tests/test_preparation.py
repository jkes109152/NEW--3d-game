import unittest
from air_defense.preparation import PreparationDraft
from tests.fixtures.expansion import profile
class PreparationTests(unittest.TestCase):
    def test_cancel_copy_and_slots(self):
        p=profile();d=PreparationDraft.from_profile(p)
        d.loadout['weapon_slots']=[None,'W17',None,'W01',None]
        self.assertIsNone(d.validate(p));self.assertEqual(p['confirmed_loadout']['weapon_slots'][0],'W01')
        d.loadout['weapon_slots'][0]='W17';self.assertEqual(d.validate(p),'duplicate_weapon')
        d.loadout['weapon_slots']=['W03',None,None,None,None];self.assertEqual(d.validate(p),'missing_target_kind')
