"""PvP 共用幾何與移動；不依賴場景、存檔或時鐘。"""
from math import sqrt
from .entities import V3, clamp, direction, ray_box

STEP = 1 / 120
BOXES = [(V3(*c), V3(*s)) for c, s in [
    ((-45, 6, -25), (10, 12, 18)), ((45, 6, 25), (10, 12, 18)),
    ((-25, 4, 45), (16, 8, 10)), ((25, 4, -45), (16, 8, 10))]]


def spawn_actor(player_id, team, index, name=''):
    if team not in ('ground', 'air') or type(index) is not int or not 0 <= index < 4:
        raise ValueError('陣營或出生位置無效')
    air = team == 'air'
    return dict(id=player_id, name=name, team=team,
                position=[(-30 + index * 20) if air else (-12 + index * 8), 40 if air else 0, 70 if air else 0],
                yaw=180 if air else 0, pitch=0., roll=0., speed=40 if air else 6,
                vertical_speed=0., hp=2 if air else 1, alive=True, departed=False,
                eliminationReason=None, eliminatedAt=None, outside=0., kills=0,
                aiming=False, firing=False, next_fire=0., look_received=[0., 0.], look_pending=[0., 0.],
                inputAck=dict(stream='', input_seq=0, command_seq=0, look_total=[0., 0.], tick=0))


def visible(start, end):
    delta = end - start
    length = delta.length()
    return length < 1e-8 or not any(ray_box(start, delta / length, c, s, max(0, length - .01)) is not None for c, s in BOXES)


def crash_fraction(start, end):
    delta = end - start
    length = delta.length()
    hits = []
    if start.y <= 1.5:
        return 0.
    if end.y <= 1.5:
        hits.append((start.y - 1.5) / max(start.y - end.y, 1e-12))
    for center, size in BOXES:
        distance = ray_box(start, delta / max(length, 1e-12), center, size + V3(3, 3, 3), length)
        if distance is not None:
            hits.append(distance / max(length, 1e-12))
    return min(hits) if hits else None


def outside(position):
    return abs(position[0]) > 100 or abs(position[2]) > 100 or position[1] > 70


def accept_input(actor, frame):
    """確認控制包與一次性命令；取消也是已處理，重送不能重做。"""
    ack = actor['inputAck']
    stream = frame.get('stream', ack['stream'])
    if stream != ack['stream']:
        ack.update(stream=stream, input_seq=0, command_seq=0, look_total=[0., 0.])
        actor.update(look_received=[0., 0.], look_pending=[0., 0.], firing=False, aiming=False)
    seq = frame.get('inputSeq', ack['input_seq'])
    if seq < ack['input_seq']:
        return []
    ack['input_seq'] = seq
    total = frame.get('look_total', actor['look_received'])
    for i in range(2):
        actor['look_pending'][i] += total[i] - actor['look_received'][i]
    actor['look_received'] = list(total)
    if frame.get('suspended', True) or not actor['alive']:
        actor.update(look_pending=[0., 0.], firing=False, aiming=False)
        ack['look_total'] = list(total)
        ack['command_seq'] = max(ack['command_seq'], frame.get('cancelThrough', 0),
                                 max((c['sequence'] for c in frame.get('commands', [])), default=0))
        return []
    commands = []
    for command in sorted(frame.get('commands', []), key=lambda c: c['sequence']):
        if command['sequence'] > ack['command_seq']:
            commands.append(command['kind'])
            ack['command_seq'] = command['sequence']
    return commands


def move_actor(actor, frame, dt, commands=()):
    """只推進角色姿態；命中與淘汰由當局處理。"""
    if not actor['alive']:
        return actor
    if actor['team'] == 'air':
        if not frame.get('suspended', True):
            actor['speed'] = clamp(actor['speed'] + frame.get('throttle', 0) * 12 * dt, 24, 55)
            for i, (key, axis, rate) in enumerate((('yaw','turn_x',120), ('pitch','turn_y',90))):
                amount = clamp(actor['look_pending'][i], -rate*dt, rate*dt)
                actor['look_pending'][i] -= amount
                actor['inputAck']['look_total'][i] += amount
                actor[key] += clamp(amount + frame.get(axis, 0) * rate * dt, -rate*dt, rate*dt)
            actor['pitch'] = clamp(actor['pitch'], -70, 70)
            actor['roll'] = (actor['roll'] + frame.get('roll', 0) * 180 * dt) % 360
        pos = V3(*actor['position']) + direction(actor['yaw'], actor['pitch']) * (actor['speed'] * dt)
        actor['position'] = list(pos.tuple())
        return actor
    active = not frame.get('suspended', True)
    if active:
        for i, key in enumerate(('yaw', 'pitch')):
            amount = actor['look_pending'][i]
            actor[key] += amount
            actor['look_pending'][i] = 0
            actor['inputAck']['look_total'][i] += amount
        actor['pitch'] = clamp(actor['pitch'], -85, 85)
    movement = direction(actor['yaw']) * (frame.get('move_z', 0) if active else 0) + direction(actor['yaw'] + 90) * (frame.get('move_x', 0) if active else 0)
    if movement.length() > 1:
        movement = movement.normalized()
    pos = V3(*actor['position'])
    if 'jump' in commands and active and pos.y <= 1e-6:
        actor['vertical_speed'] = sqrt(2 * 18 * 1.8)
    actor['vertical_speed'] -= 18 * dt
    y = max(0, pos.y + actor['vertical_speed'] * dt)
    if y == 0:
        actor['vertical_speed'] = 0
    pos = V3(pos.x, y, pos.z)
    for offset in (V3(movement.x * 6 * dt, 0, 0), V3(0, 0, movement.z * 6 * dt)):
        candidate = pos + offset
        if not any(abs(candidate.x-c.x) < size.x/2+.45 and abs(candidate.z-c.z) < size.z/2+.45 and candidate.y < c.y+size.y/2 and candidate.y+1.8 > c.y-size.y/2 for c, size in BOXES):
            pos = candidate
    actor['position'] = [clamp(pos.x, -99.55, 99.55), pos.y, clamp(pos.z, -99.55, 99.55)]
    return actor
