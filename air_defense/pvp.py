"""獨立 PvP 當局；不載入玩家成長或合作世界。"""
from copy import deepcopy
from math import isfinite, acos, radians, cos, sin, sqrt, tan
from .pvp_motion import STEP, spawn_actor, accept_input, move_actor
from .combat import LockState
from .entities import V3, direction, clamp
from .pvp_motion import visible, crash_fraction, outside

LIMITS = {2: 180, 3: 300, 4: 210, 5: 330, 6: 240, 7: 390, 8: 270}


class PvpBattle:
    def __init__(self, run_id, roster, time_limit_seconds):
        if not run_id or len(roster) not in LIMITS or time_limit_seconds != LIMITS[len(roster)]:
            raise ValueError('對戰局次或時限無效')
        if len({p['id'] for p in roster}) != len(roster):
            raise ValueError('玩家名單重複')
        counts = {t: sum(p['team'] == t for p in roster) for t in ('air', 'ground')}
        if counts != {'air': (len(roster) + 1) // 2, 'ground': len(roster) // 2}:
            raise ValueError('分隊比例無效')
        self.run_id, self.roster, self.limit = run_id, deepcopy(roster), time_limit_seconds
        self.elapsed, self.tick, self.remainder = 0., 0, 0.
        self.phase, self.result = 'active', None
        self.actors, self.locks, self.missiles, self.events = {}, {}, {}, []
        self.event_sequence, self.missile_sequence = 0, 0
        indices = {'air': 0, 'ground': 0}
        for p in roster:
            self.actors[p['id']] = spawn_actor(p['id'], p['team'], indices[p['team']], p['name'])
            self.locks[p['id']] = LockState()
            indices[p['team']] += 1

    def advance(self, dt, frames, departed_ids=()):
        if not isfinite(dt) or dt < 0 or dt > 1:
            raise ValueError('模擬時間無法可靠接續')
        if self.phase != 'active':
            return self.snapshot()
        self.remainder += dt
        while self.remainder >= STEP - 1e-10 and self.phase == 'active':
            self.remainder -= STEP
            step = min(STEP, self.limit - self.elapsed)
            self.step(step, frames, departed_ids)
        return self.snapshot()

    def event(self, kind, **data):
        self.event_sequence += 1
        self.events.append(dict(sequence=self.event_sequence, kind=kind, **data))
        self.events = self.events[-128:]

    def eliminate(self, key, reason, at=None, owner=None):
        actor = self.actors[key]
        if not actor['alive']:
            return
        actor.update(alive=False, hp=0, eliminationReason=reason, eliminatedAt=self.elapsed if at is None else at, firing=False, aiming=False)
        self.locks[key].clear()
        if owner is not None:
            self.actors[owner]['kills'] += 1
        self.event('eliminated', player_id=key, reason=reason)

    def finish(self, winner, reason):
        if self.result is not None:
            return
        self.phase = 'aborted' if winner is None else 'finished'
        self.result = dict(runId=self.run_id, winner=winner, reason=reason, elapsed=self.elapsed,
                           players=[{k: a[k] for k in ('id','name','team','alive','kills','eliminationReason')} for a in self.actors.values()])
        for lock in self.locks.values():
            lock.clear()
        self.missiles.clear()

    def candidates(self, actor, aspect):
        eye = V3(*actor['position']) + V3(0, 1.6, 0)
        forward = direction(actor['yaw'], actor['pitch'])
        right = direction(actor['yaw'] + 90)
        up = V3(forward.y*right.z, forward.z*right.x-forward.x*right.z, -forward.y*right.x)
        found = []
        for key, target in self.actors.items():
            if target['team'] != 'air' or not target['alive']:
                continue
            pos = V3(*target['position'])
            delta = pos - eye
            depth = delta.dot(forward)
            if depth <= 0 or delta.horizontal().length() > 240 or not visible(eye, pos):
                continue
            scale = 1 / (2 * tan(radians(65) / 2) * depth)
            if abs(delta.dot(right) * scale) <= min(.105, aspect / 2) + 1e-9 and abs(delta.dot(up) * scale) <= .105 + 1e-9:
                found.append(key)
        return found

    def step(self, dt, frames, departed_ids):
        self.tick += 1
        for actor in self.actors.values():
            actor['inputAck']['tick'] = self.tick
        before = {key: V3(*a['position']) for key, a in self.actors.items()}
        for key in departed_ids:
            if key in self.actors:
                self.actors[key]['departed'] = True
                self.eliminate(key, 'departed')
        if all(a['departed'] for a in self.actors.values()):
            self.finish(None, 'all_departed')
            return
        for key, actor in self.actors.items():
            frame = frames.get(key, {'suspended': True})
            commands = accept_input(actor, frame)
            move_actor(actor, frame, dt, commands)
            if actor['team'] == 'ground' and actor['alive']:
                for command in commands:
                    if command == 'toggle_aim': actor['aiming'] = not actor['aiming']
                    elif command == 'fire_down': actor['firing'] = True
                    elif command == 'fire_up': actor['firing'] = False
            actor['inputAck']['tick'] = self.tick
        next_time = min(self.limit, self.elapsed + dt)
        alive = [key for key, a in self.actors.items() if a['team'] == 'air' and a['alive']]
        for key, actor in self.actors.items():
            if actor['team'] != 'ground':
                continue
            lock = self.locks[key]
            candidates = self.candidates(actor, frames.get(key, {}).get('aspect', 16/9)) if actor['alive'] else []
            lock.update(dt, candidates, alive, actor['aiming'] and actor['alive'], False, 3)
            if actor['firing'] and lock.ready() and next_time >= actor['next_fire'] - 1e-9:
                self.missile_sequence += 1
                mid = str(self.missile_sequence)
                self.missiles[mid] = dict(id=mid, owner_id=key, target_id=lock.valid[0], position=list((V3(*actor['position'])+V3(0,1.6,0)).tuple()), forward=list(direction(actor['yaw'],actor['pitch']).tuple()), age=0.)
                actor['next_fire'] = next_time + 1.25
                self.event('weapon_fire', weapon_id='W01', player_id=key, projectile_ids=[mid])
                lock.clear()
        impacts = []
        for index, (key, actor) in enumerate(self.actors.items()):
            if actor['team'] != 'air' or not actor['alive']:
                continue
            fraction = crash_fraction(before[key], V3(*actor['position']))
            if fraction is not None:
                impacts.append((fraction, 0, index, key, 'crash', None, None))
            previous = actor['outside']
            actor['outside'] = previous + dt if outside(actor['position']) else 0.
            if actor['outside'] >= 5 - 1e-9:
                impacts.append((clamp((5-previous)/dt, 0, 1), 0, index, key, 'boundary', None, None))
        for mid, missile in list(self.missiles.items()):
            target = self.actors[missile['target_id']]
            if not target['alive']:
                del self.missiles[mid]
                continue
            start = V3(*missile['position'])
            current = V3(*missile['forward']).normalized()
            desired = (V3(*target['position']) - start).normalized()
            angle = acos(clamp(current.dot(desired), -1, 1))
            turn = min(angle, radians(240) * dt)
            if angle > 1e-8:
                perpendicular = (desired - current * cos(angle)).normalized()
                if perpendicular.length() < .1:
                    perpendicular = V3(current.z, 0, -current.x).normalized()
                if perpendicular.length() < .1:
                    perpendicular = V3(1, 0, 0)
                current = (current * cos(turn) + perpendicular * sin(turn)).normalized()
            life_dt = min(dt, max(0, 5 - missile['age']))
            end = start + current * (90 * life_dt)
            relative_start = start - before[missile['target_id']]
            relative_end = end - V3(*target['position'])
            delta = relative_end - relative_start
            aa, bb, cc = delta.dot(delta), 2*relative_start.dot(delta), relative_start.dot(relative_start)-1.5**2
            fraction = None
            if cc <= 0: fraction = 0
            elif aa > 1e-12 and bb*bb-4*aa*cc >= 0:
                hit = (-bb-sqrt(bb*bb-4*aa*cc))/(2*aa)
                if 0 <= hit <= 1: fraction = hit
            missile.update(position=list(end.tuple()), forward=list(current.tuple()), age=missile['age']+dt)
            if fraction is not None:
                impacts.append((fraction, 1, int(mid), missile['target_id'], 'missile', missile['owner_id'], mid))
            elif missile['age'] >= 5 - 1e-9:
                del self.missiles[mid]
        for fraction, _, _, target_id, reason, owner, mid in sorted(impacts):
            if mid: self.missiles.pop(mid, None)
            target = self.actors[target_id]
            if not target['alive']: continue
            target['hp'] = target['hp'] - 1 if reason == 'missile' else 0
            self.event('hit' if reason == 'missile' else reason, player_id=target_id, owner_id=owner)
            if target['hp'] <= 0: self.eliminate(target_id, reason, self.elapsed+dt*fraction, owner)
        self.elapsed = next_time
        for lock in self.locks.values():
            lock.valid = tuple(k for k in lock.valid if self.actors[k]['alive'])
        if not any(a['alive'] for a in self.actors.values() if a['team']=='air'):
            self.finish('ground', 'air_eliminated')
        elif all(a['departed'] for a in self.actors.values() if a['team']=='ground'):
            self.finish('air', 'ground_departed')
        elif self.elapsed >= self.limit - 1e-9:
            self.finish('air', 'timeout')

    def snapshot(self):
        actors = deepcopy(list(self.actors.values()))
        missiles = deepcopy(list(self.missiles.values()))
        views = {}
        for key, actor in self.actors.items():
            lock = self.locks[key]
            views[key] = dict(runId=self.run_id, selfId=key, team=actor['team'], phase=self.phase,
                              tick=self.tick, elapsed=self.elapsed, remainingSeconds=max(0, self.limit - self.elapsed),
                              actors=actors, missiles=missiles, inputAck=deepcopy(actor['inputAck']),
                              locks=dict(lock.progress), lock_current=lock.current, lock_valid=list(lock.valid),
                              cooldown=max(0, actor['next_fire'] - self.elapsed),
                              threats=dict(tracking=any(key in l.valid and l.progress.get(key, 0) < 1-1e-9 for l in self.locks.values()) if actor['alive'] else False,
                                           locked=any(key in l.valid and l.ready() for l in self.locks.values()) if actor['alive'] else False,
                                           missile=any(m['target_id']==key for m in missiles) if actor['alive'] else False),
                              result=deepcopy(self.result), events=deepcopy(self.events))
        return dict(mode='pvp', protocolVersion=1, runId=self.run_id, phase=self.phase,
                    tick=self.tick, elapsed=self.elapsed, result=deepcopy(self.result), views=views)


def predict(actor, frames):
    result = deepcopy(actor)
    for row in frames:
        frame = row['input']
        commands = accept_input(result, dict(frame, stream=row['stream'], inputSeq=row['inputSeqAtCapture']))
        move_actor(result, frame, STEP, [c for c in commands if c == 'jump'])
    return result
