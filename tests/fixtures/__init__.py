"""可重現測試資料。"""
from random import Random
from tempfile import TemporaryDirectory

SEED = 1701

class FakeClock:
    """由測試明確推進，避免依賴系統時間。"""
    def __init__(self): self.now = 0.
    def advance(self, seconds):
        self.now += seconds
        return self.now

class EventCollector:
    def __init__(self): self.events = []
    def collect(self, snapshot): self.events.extend(snapshot['events'])
    def of_kind(self, kind): return [e for e in self.events if e['kind'] == kind]

def seeded():
    return Random(SEED)

def battle(**kwargs):
    from air_defense.state import BattleState
    from air_defense.progression import new_profile, level_for
    return BattleState(new_profile(), level_for(1, 1, 2), seed=SEED, **kwargs)
