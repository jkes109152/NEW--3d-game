"""戰前草稿不改資產，只有最終確認才保存。"""
from copy import deepcopy
from dataclasses import dataclass, field
from .deployment import validate_deployment
from .loadout import validate_loadout

STEPS=('prepare_armor','prepare_weapons','prepare_deployment','prepare_confirm')

@dataclass
class PreparationDraft:
    profile_id:str
    revision:int
    rebirth_count:int
    loadout:dict
    step:int=0
    selected_turret:str | None=None
    messages:list=field(default_factory=list)

    @classmethod
    def from_profile(cls,profile):
        load=deepcopy(profile['confirmed_loadout']);valid=[];messages=[]
        for p in load['deployments']:
            error=validate_deployment(profile,valid+[p])
            if error:messages.append(error)
            else:valid.append(p)
        load['deployments']=valid
        return cls(profile['profile_id'],profile['profile_revision'],profile['rebirth_count'],load,messages=messages)

    def validate(self,profile):
        if self.profile_id!=profile['profile_id'] or self.rebirth_count!=profile['rebirth_count'] or self.revision!=profile['profile_revision']:return 'stale_draft'
        return validate_loadout(profile,self.loadout)

    def place(self,profile,instance_id,x,z):
        items=[p for p in self.loadout['deployments'] if p['instance_id']!=instance_id]
        items.append(dict(instance_id=instance_id,x=x,z=z));reason=validate_deployment(profile,items)
        if reason:return reason
        self.loadout['deployments']=items;return None

    def remove(self,instance_id):
        self.loadout['deployments']=[p for p in self.loadout['deployments'] if p['instance_id']!=instance_id]
