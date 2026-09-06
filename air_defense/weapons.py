"""逐武器彈匣與到期時刻，不依畫面幀率量化射速。"""
from dataclasses import dataclass

@dataclass(frozen=True)
class InputCommand:
    sequence:int
    kind:str
    value:int | None=None

@dataclass
class WeaponRuntime:
    weapon_id:str
    magazine_rounds:int | None
    quota_remaining:int | None
    next_shot_at:float=0
    reload_finish_at:float | None=None
    burst_remaining:int=0
    next_burst_start_at:float=0

    @classmethod
    def create(cls,stats):return cls(stats.weapon_id,stats.magazine_size,stats.quota)

    def error(self,now):
        if self.reload_finish_at is not None:return 'reload'
        if now+1e-9<self.next_shot_at:return 'cooldown'
        if self.magazine_rounds==0 or self.quota_remaining==0:return 'ammo'
        return None

    def reload(self,now,stats):
        if self.reload_finish_at is not None or self.magazine_rounds is None or self.magazine_rounds==stats.magazine_size or self.quota_remaining==0:return False
        self.reload_finish_at=now+stats.reload_seconds;self.burst_remaining=0;return True

    def tick(self,now,stats):
        if self.reload_finish_at is not None and now+1e-9>=self.reload_finish_at:
            self.magazine_rounds=stats.magazine_size if self.quota_remaining is None else min(stats.magazine_size,self.quota_remaining)
            self.reload_finish_at=None;self.next_shot_at=max(self.next_shot_at,now);return True
        return False

    def consume(self,at,stats):
        if self.magazine_rounds is not None:self.magazine_rounds-=1
        if self.quota_remaining is not None:self.quota_remaining-=1
        self.next_shot_at=at+stats.interval

    def cancel(self):
        self.reload_finish_at=None;self.burst_remaining=0
