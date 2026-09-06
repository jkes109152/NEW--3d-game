import unittest
from air_defense.progression import transact
from air_defense.deployment import validate_deployment
from tests.fixtures.expansion import profile,request,operation_id

class TurretInventoryTests(unittest.TestCase):
    def test_per_instance_replay_and_capacity_not_inventory_cap(self):
        p=profile(coins=100000);self.assertEqual(transact(p,operation_id(),request(p,'purchase_turret',turret_id='T01'))['reason'],'locked')
        for r,capacity in ((1,2),(2,4),(4,8),(6,12)):
            p=profile(coins=100000,rebirth_count=r)
            for i in range(capacity+1):
                req=request(p,'purchase_turret',turret_id='T01');op=operation_id(i)
                result=transact(p,op,req);self.assertEqual(result['summary']['instance_id'],'turret-'+op)
                self.assertTrue(transact(p,op,req)['replayed'])
            self.assertEqual(len(p['owned_turrets']),capacity+1)
            placements=[dict(instance_id=t['instance_id'],x=40,z=100+i*4) for i,t in enumerate(p['owned_turrets'])]
            self.assertEqual(validate_deployment(p,placements),'capacity');self.assertIsNone(validate_deployment(p,placements[:-1]))
            self.assertEqual(validate_deployment(p,[placements[0],placements[0]]),'duplicate_instance')
