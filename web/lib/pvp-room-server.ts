import { cleanName, pvpTimeLimit, splitPvpTeams } from './multiplayer-rules.ts';
import { neutralInput } from './pvp-types.ts';

// 房間在線、開局與倒數共用心跳寬限；戰鬥操作仍以一秒判定過期。
const ROOM_PRESENCE_TIMEOUT_MS = 5000;

export class PvpRequestError extends Error {
  constructor(
    message: string,
    public status = 400,
  ) {
    super(message);
  }
}
const requirePvp = (value: unknown, message: string, status = 400) => {
  if (!value) throw new PvpRequestError(message, status);
};
const uuid = () => crypto.randomUUID().replaceAll('-', '');
const parse = (value: string | null, fallback: any = null) =>
  value ? JSON.parse(value) : fallback;

export async function pvpRoomRequest(
  db: D1Database,
  me: any,
  data: any,
  now: number,
  initial?: any,
): Promise<any> {
  const action = data.action;
  if (action === 'create') {
    const old = await db
      .prepare('SELECT room_id FROM mp_members WHERE player_id=?')
      .bind(me.id)
      .first();
    requirePvp(!old, '請先離開目前房間');
    const id = uuid();
    await db.batch([
      db
        .prepare(
          "INSERT INTO mp_rooms(id,name,host_id,mode,updated_at,created_at) VALUES(?,?,?,'pvp',?,?)",
        )
        .bind(id, cleanName(data.name || `${me.name}的房間`), me.id, now, now),
      db
        .prepare(
          'INSERT INTO mp_members(room_id,player_id,seen_at) VALUES(?,?,?)',
        )
        .bind(id, me.id, now),
    ]);
    return { roomId: id };
  }
  let room = initial;
  const roomId = room.id;
  let cachedMembers: any[] | null = null;
  const roomStatement = () =>
    db.prepare('SELECT * FROM mp_rooms WHERE id=?').bind(roomId);
  const membersStatement = () =>
    db
      .prepare(
        'SELECT m.*,p.name FROM mp_members m JOIN mp_players p ON p.id=m.player_id WHERE m.room_id=? ORDER BY m.player_id',
      )
      .bind(roomId);
  const reload = async () => {
    cachedMembers = null;
    room = await roomStatement().first();
  };
  const memberRows = async () => {
    if (!cachedMembers)
      cachedMembers = (await membersStatement().all()).results;
    return cachedMembers!;
  };
  const updates: D1PreparedStatement[] = [];
  const ended = () => ['finished', 'closed'].includes(room.status);
  const host = room.host_id === me.id;
  async function abort(reason: string) {
    if (ended()) return;
    const snap = parse(room.snapshot),
      roster = parse(room.roster, []);
    const actors = snap?.views?.[roster[0]?.id]?.actors || [];
    const result = {
      runId: room.run_id,
      winner: null,
      reason,
      elapsed: snap?.elapsed || 0,
      players: roster.map((p: any) => {
        const a = actors.find((v: any) => v.id === p.id);
        return {
          ...p,
          alive: a?.alive ?? true,
          kills: a?.kills || 0,
          eliminationReason: a?.eliminationReason ?? null,
        };
      }),
    };
    await db
      .prepare(
        "UPDATE mp_rooms SET status='finished',result=?,updated_at=? WHERE id=? AND run_id=? AND status IN ('countdown','playing') AND result IS NULL",
      )
      .bind(JSON.stringify(result), now, roomId, room.run_id)
      .run();
    await reload();
  }
  async function cancelCountdown() {
    const run = room.run_id;
    await db.batch([
      db
        .prepare(
          "UPDATE mp_rooms SET status='waiting',run_id=NULL,roster='[]',snapshot=NULL,starts_at=NULL,result=NULL,departures='{}',roster_revision=roster_revision+1 WHERE id=? AND run_id=? AND status='countdown'",
        )
        .bind(roomId, run),
      db
        .prepare(
          "UPDATE mp_members SET ready=0,input='{}',input_seq=0,input_stream=NULL,input_instance=NULL,input_received_at=NULL WHERE room_id=? AND EXISTS(SELECT 1 FROM mp_rooms WHERE id=? AND status='waiting' AND run_id IS NULL)",
        )
        .bind(roomId, roomId),
    ]);
    await reload();
  }
  async function depart(playerId: string, reason: 'left' | 'timeout') {
    // 同一交易記帳並釋放資格；JSON 路徑只來自資料庫的十六進位身分。
    const path = '$.' + playerId;
    await db.batch([
      db
        .prepare(
          "UPDATE mp_rooms SET departures=json_set(departures,?,json(?)),roster_revision=roster_revision+1 WHERE id=? AND run_id=? AND status='playing' AND json_type(departures,?) IS NULL",
        )
        .bind(
          path,
          JSON.stringify({ at: now, reason }),
          roomId,
          room.run_id,
          path,
        ),
      db
        .prepare(
          'DELETE FROM mp_members WHERE room_id=? AND player_id=? AND EXISTS(SELECT 1 FROM mp_rooms WHERE id=? AND run_id=? AND json_type(departures,?) IS NOT NULL)',
        )
        .bind(roomId, playerId, roomId, room.run_id, path),
    ]);
    await reload();
  }
  if (action === 'join') {
    requirePvp(
      room.status === 'waiting' && room.updated_at > now - 20000,
      '房間已開始或已關閉',
    );
    const existing: any = await db
      .prepare('SELECT room_id FROM mp_members WHERE player_id=?')
      .bind(me.id)
      .first();
    requirePvp(!existing || existing.room_id === roomId, '請先離開目前房間');
    const changes = await db.batch([
      db
        .prepare(
          "INSERT OR IGNORE INTO mp_members(room_id,player_id,seen_at) SELECT ?,?,? WHERE EXISTS(SELECT 1 FROM mp_rooms WHERE id=? AND status='waiting') AND (SELECT count(*) FROM mp_members WHERE room_id=?)<8",
        )
        .bind(roomId, me.id, now, roomId, roomId),
      db
        .prepare(
          "UPDATE mp_rooms SET roster_revision=roster_revision+1 WHERE id=? AND status='waiting' AND EXISTS(SELECT 1 FROM mp_members WHERE room_id=? AND player_id=?)",
        )
        .bind(roomId, roomId, me.id),
    ]);
    requirePvp(
      changes[0].meta.changes || existing?.room_id === roomId,
      '房間已滿或已開始',
    );
    return { roomId };
  }
  let membership: any = (await memberRows()).find((m) => m.player_id === me.id);
  if (
    action === 'leave' &&
    !membership &&
    data.runId === room.run_id &&
    parse(room.departures, {})[me.id]
  )
    return { left: true };
  requirePvp(membership, '你已離開此房間', 403);
  requirePvp(data.protocolVersion === 1, '對戰版本已更新，請重新載入', 409);
  if (data.snapshot)
    requirePvp(host && action === 'exchange', '只有房主可同步戰場', 403);
  if (room.run_id && action !== 'sync')
    requirePvp(data.runId === room.run_id, '局次已變更', 409);
  if (
    host &&
    ['countdown', 'playing'].includes(room.status) &&
    data.instanceId !== room.host_instance_id
  )
    await abort('host_reload');
  if (
    room.status === 'playing' &&
    now - (room.simulation_seen_at ?? room.starts_at) >= 10000
  )
    await abort('host_timeout');
  if (room.status === 'countdown') {
    if (
      (await memberRows()).some(
        (m) => now - m.seen_at >= ROOM_PRESENCE_TIMEOUT_MS,
      )
    )
      await cancelCountdown();
    else if (now >= room.starts_at) {
      await db
        .prepare(
          "UPDATE mp_rooms SET status='playing',simulation_seen_at=starts_at WHERE id=? AND run_id=? AND status='countdown'",
        )
        .bind(roomId, room.run_id)
        .run();
      await reload();
    }
  }
  if (room.status === 'playing') {
    for (const m of await memberRows())
      if (m.player_id !== room.host_id && now - m.seen_at >= 10000)
        await depart(m.player_id, 'timeout');
    membership = (await memberRows()).find((m) => m.player_id === me.id);
    requirePvp(membership, '已超過十秒重連期限，請返回大廳', 403);
  }
  if (room.status === 'waiting' && host) {
    await db.batch([
      db
        .prepare(
          "UPDATE mp_rooms SET roster_revision=roster_revision+1 WHERE id=? AND status='waiting' AND EXISTS(SELECT 1 FROM mp_members WHERE room_id=? AND player_id<>? AND seen_at<=?)",
        )
        .bind(roomId, roomId, me.id, now - 20000),
      db
        .prepare(
          "DELETE FROM mp_members WHERE room_id=? AND player_id<>? AND seen_at<=? AND EXISTS(SELECT 1 FROM mp_rooms WHERE id=? AND status='waiting')",
        )
        .bind(roomId, me.id, now - 20000, roomId),
    ]);
    await reload();
  }
  if (action === 'leave') {
    if (room.status === 'countdown') await cancelCountdown();
    if (room.status === 'playing') await depart(me.id, 'left');
    if (host) {
      if (room.status === 'playing') await abort('host_left');
      else if (room.status === 'waiting')
        await db
          .prepare(
            "UPDATE mp_rooms SET status='closed',updated_at=? WHERE id=? AND status='waiting'",
          )
          .bind(now, roomId)
          .run();
    }
    await db.batch([
      db
        .prepare('DELETE FROM mp_members WHERE room_id=? AND player_id=?')
        .bind(roomId, me.id),
      db
        .prepare(
          'UPDATE mp_rooms SET roster_revision=roster_revision+1 WHERE id=?',
        )
        .bind(roomId),
    ]);
    return { left: true };
  }
  if (action === 'ready') {
    requirePvp(
      room.status === 'waiting' && typeof data.ready === 'boolean',
      '請在等待室設定準備',
    );
    await db.batch([
      db
        .prepare(
          "UPDATE mp_members SET ready=?,profile=NULL,seen_at=? WHERE room_id=? AND player_id=? AND EXISTS(SELECT 1 FROM mp_rooms WHERE id=? AND status='waiting')",
        )
        .bind(+data.ready, now, roomId, me.id, roomId),
      db
        .prepare(
          "UPDATE mp_rooms SET roster_revision=roster_revision+1 WHERE id=? AND status='waiting'",
        )
        .bind(roomId),
    ]);
  } else if (action === 'start') {
    requirePvp(host, '只有房主可以開始', 403);
    requirePvp(room.status === 'waiting', '本局已開始');
    requirePvp(
      typeof data.instanceId === 'string' && data.instanceId.length <= 64,
      '頁面身分無效',
    );
    const rows = await memberRows();
    requirePvp(
      rows.length >= 2 &&
        rows.length <= 8 &&
        rows.every(
          (m) => m.ready && now - m.seen_at < ROOM_PRESENCE_TIMEOUT_MS,
        ),
      '至少兩人，且所有玩家需在線並準備完成',
    );
    const roster = splitPvpTeams(
      rows.map((m) => ({ id: m.player_id, name: m.name })),
    );
    const runId = uuid();
    const changes = await db.batch([
      db
        .prepare(
          "UPDATE mp_rooms SET status='countdown',run_id=?,roster=?,starts_at=?,time_limit_seconds=?,host_instance_id=?,snapshot=NULL,result=NULL,departures='{}',sequence=0,simulation_tick=0,simulation_seen_at=NULL,updated_at=? WHERE id=? AND status='waiting' AND roster_revision=? AND (SELECT count(*) FROM mp_members WHERE room_id=?)=? AND NOT EXISTS(SELECT 1 FROM mp_members WHERE room_id=? AND (ready=0 OR seen_at<=?))",
        )
        .bind(
          runId,
          JSON.stringify(roster),
          now + 3000,
          pvpTimeLimit(rows.length),
          data.instanceId,
          now,
          roomId,
          room.roster_revision,
          roomId,
          rows.length,
          roomId,
          now - ROOM_PRESENCE_TIMEOUT_MS,
        ),
      ...rows.map((m) =>
        db
          .prepare(
            "UPDATE mp_members SET input_stream=?,input_instance=NULL,input_seq=0,input='{}',input_received_at=NULL WHERE room_id=? AND player_id=? AND EXISTS(SELECT 1 FROM mp_rooms WHERE id=? AND run_id=? AND status='countdown')",
          )
          .bind(uuid(), roomId, m.player_id, roomId, runId),
      ),
    ]);
    requirePvp(changes[0].meta.changes, '玩家或準備狀態已變更，請重試');
  } else if (action === 'resume' && !ended()) {
    requirePvp(
      ['countdown', 'playing'].includes(room.status),
      '尚未開始對戰',
      409,
    );
    requirePvp(
      typeof data.instanceId === 'string' && data.instanceId.length <= 64,
      '頁面身分無效',
    );
    if (membership.input_instance !== data.instanceId) {
      const changed = await db
        .prepare(
          "UPDATE mp_members SET input_stream=?,input_instance=?,input_seq=0,input='{}',input_received_at=NULL WHERE room_id=? AND player_id=? AND input_stream=? AND EXISTS(SELECT 1 FROM mp_rooms WHERE id=? AND run_id=? AND status IN ('countdown','playing'))",
        )
        .bind(
          uuid(),
          data.instanceId,
          roomId,
          me.id,
          data.expectedStream,
          roomId,
          room.run_id,
        )
        .run();
      requirePvp(
        changed.meta.changes,
        '另一分頁已取得控制，請重新開啟房間',
        409,
      );
    }
  } else if (action === 'exchange' && !ended() && room.run_id) {
    requirePvp(
      membership.input_stream === data.inputStream &&
        membership.input_instance === data.instanceId,
      '另一分頁已取得控制，請重新開啟房間',
      409,
    );
    requirePvp(
      Number.isSafeInteger(data.inputSeq) && data.inputSeq >= 0,
      '操作序號無效',
    );
    const input = validatePvpInput(data.input);
    updates.push(
      db
        .prepare(
          'UPDATE mp_members SET input=?,input_seq=?,input_received_at=? WHERE room_id=? AND player_id=? AND input_stream=? AND input_instance=? AND input_seq<?',
        )
        .bind(
          JSON.stringify(input),
          data.inputSeq,
          now,
          roomId,
          me.id,
          data.inputStream,
          data.instanceId,
          data.inputSeq,
        ),
    );
    if (data.snapshot) {
      requirePvp(host, '只有房主可同步戰場', 403);
      requirePvp(room.status === 'playing', '倒數中不能推進戰鬥');
      validatePvpSnapshot(data.snapshot, room);
      requirePvp(
        Number.isSafeInteger(data.sequence) && data.sequence > 0,
        '戰場序號無效',
      );
      updates.push(
        db
          .prepare(
            "UPDATE mp_rooms SET snapshot=?,sequence=?,simulation_seen_at=CASE WHEN simulation_tick<? THEN ? ELSE simulation_seen_at END,simulation_tick=? WHERE id=? AND run_id=? AND status='playing' AND sequence<? AND simulation_tick<=?",
          )
          .bind(
            JSON.stringify(data.snapshot),
            data.sequence,
            data.snapshot.tick,
            now,
            data.snapshot.tick,
            roomId,
            room.run_id,
            data.sequence,
            data.snapshot.tick,
          ),
      );
    }
  } else if (action === 'finish') {
    requirePvp(host, '只有房主可結算戰場', 403);
    if (!ended()) {
      const snapshot = parse(room.snapshot);
      validatePvpSnapshot(snapshot, room);
      requirePvp(snapshot.phase === 'finished', '戰鬥尚未完成');
      await db
        .prepare(
          "UPDATE mp_rooms SET status='finished',result=?,updated_at=? WHERE id=? AND run_id=? AND status='playing' AND result IS NULL AND sequence=? AND roster_revision=?",
        )
        .bind(
          JSON.stringify(snapshot.result),
          now,
          roomId,
          room.run_id,
          room.sequence,
          room.roster_revision,
        )
        .run();
    }
  } else if (action === 'abort') {
    requirePvp(host, '只有房主可中止戰場', 403);
    requirePvp(
      [
        'host_reload',
        'simulation_gap',
        'simulation_error',
        'host_left',
      ].includes(data.reason),
      '中止原因無效',
    );
    await abort(data.reason);
  } else if (action === 'again') {
    requirePvp(host && room.status === 'finished', '只有房主可開始下一局', 403);
    await db.batch([
      db
        .prepare(
          'DELETE FROM mp_members WHERE room_id=? AND seen_at<=? AND player_id<>?',
        )
        .bind(roomId, now - 10000, me.id),
      db
        .prepare(
          "UPDATE mp_rooms SET status='waiting',run_id=NULL,roster='[]',snapshot=NULL,result=NULL,departures='{}',starts_at=NULL,sequence=0,simulation_tick=0,roster_revision=roster_revision+1,updated_at=? WHERE id=? AND run_id=? AND status='finished'",
        )
        .bind(now, roomId, room.run_id),
      db
        .prepare(
          "UPDATE mp_members SET ready=0,input='{}',input_seq=0,input_stream=NULL,input_instance=NULL,input_received_at=NULL WHERE room_id=? AND EXISTS(SELECT 1 FROM mp_rooms WHERE id=? AND status='waiting')",
        )
        .bind(roomId, roomId),
    ]);
  } else
    requirePvp(['sync', 'exchange', 'resume'].includes(action), '未知房間操作');
  if (!ended() && host)
    updates.push(
      db
        .prepare('UPDATE mp_rooms SET updated_at=? WHERE id=?')
        .bind(now, roomId),
    );
  if (
    action !== 'sync' ||
    !membership.input_instance ||
    membership.input_instance === data.instanceId
  )
    updates.push(
      db
        .prepare(
          'UPDATE mp_members SET seen_at=? WHERE room_id=? AND player_id=?',
        )
        .bind(now, roomId, me.id),
    );
  // 同一交易提交新操作／戰場並讀回回覆，省去逐句遠端往返。
  const result = await db.batch([
    ...updates,
    roomStatement(),
    membersStatement(),
  ]);
  room = result[result.length - 2].results[0];
  const rows = result[result.length - 1].results as any[],
    mine = rows.find((m) => m.player_id === me.id),
    snapshot = parse(room.snapshot);
  return {
    room: {
      id: room.id,
      name: room.name,
      mode: 'pvp',
      capacity: 8,
      protocolVersion: 1,
      hostId: room.host_id,
      status: room.status,
      runId: room.run_id,
      roster: parse(room.roster, []),
      startsAt: room.starts_at,
      serverNow: now,
      hostInstanceId: room.host_instance_id,
      timeLimitSeconds: room.time_limit_seconds,
      sequence: room.sequence,
      currentStream: mine?.input_stream,
      inputInstance: mine?.input_instance,
      members: rows.map((m) => ({
        id: m.player_id,
        name: m.name,
        ready: !!m.ready,
        online: now - m.seen_at < ROOM_PRESENCE_TIMEOUT_MS,
      })),
      view: snapshot?.views?.[me.id] ?? null,
      result: parse(room.result),
      departures: parse(room.departures, {}),
      ...(host
        ? {
            hostInputs: rows.map((m) => ({
              playerId: m.player_id,
              inputStream: m.input_stream,
              inputInstance: m.input_instance,
              inputSeq: m.input_seq,
              input: parse(m.input, neutralInput()),
              inputReceivedAt: m.input_received_at,
              lastSeenAt: m.seen_at,
            })),
          }
        : {}),
    },
  };
}

export function validatePvpInput(input: any) {
  requirePvp(
    input &&
      typeof input === 'object' &&
      !Array.isArray(input) &&
      JSON.stringify(input).length < 20000,
    '操作資料無效',
  );
  const v = { ...neutralInput(), ...input };
  requirePvp(
    typeof v.suspended === 'boolean' &&
      Number.isSafeInteger(v.cancelThrough) &&
      v.cancelThrough >= 0,
    '取消操作無效',
  );
  for (const key of [
    'move_x',
    'move_z',
    'turn_x',
    'turn_y',
    'throttle',
    'roll',
  ])
    requirePvp(Number.isFinite(v[key]) && Math.abs(v[key]) <= 1, '操作軸無效');
  requirePvp(
    Number.isFinite(v.aspect) && v.aspect >= 0.2 && v.aspect <= 6,
    '畫面比例無效',
  );
  requirePvp(
    Array.isArray(v.look_total) &&
      v.look_total.length === 2 &&
      v.look_total.every((x: any) => Number.isFinite(x) && Math.abs(x) < 1e9),
    '轉向資料無效',
  );
  requirePvp(
    Array.isArray(v.commands) &&
      v.commands.length <= 96 &&
      v.commands.every(
        (c: any) =>
          Number.isSafeInteger(c.sequence) &&
          c.sequence > 0 &&
          ['fire_down', 'fire_up', 'toggle_aim', 'jump'].includes(c.kind),
      ),
    '命令資料無效',
  );
  return Object.fromEntries(Object.keys(neutralInput()).map((k) => [k, v[k]]));
}

export function validatePvpSnapshot(snapshot: any, room: any) {
  const vector = (v: any, n = 3) =>
    Array.isArray(v) && v.length === n && v.every(Number.isFinite);
  const nonnegative = (v: any) => Number.isFinite(v) && v >= 0;
  requirePvp(
    snapshot &&
      snapshot.mode === 'pvp' &&
      snapshot.protocolVersion === 1 &&
      snapshot.runId === room.run_id,
    '戰場局次無效',
  );
  requirePvp(
    ['active', 'finished', 'aborted'].includes(snapshot.phase) &&
      Number.isSafeInteger(snapshot.tick) &&
      snapshot.tick >= 0 &&
      Number.isFinite(snapshot.elapsed) &&
      snapshot.elapsed >= 0 &&
      snapshot.elapsed <= room.time_limit_seconds,
    '戰場時間無效',
  );
  const roster = parse(room.roster, []);
  requirePvp(
    snapshot.views && Object.keys(snapshot.views).length === roster.length,
    '玩家快照數量不符',
  );
  let canonical = '';
  for (const p of roster) {
    const view = snapshot.views[p.id];
    requirePvp(
      view &&
        view.runId === snapshot.runId &&
        view.phase === snapshot.phase &&
        view.selfId === p.id &&
        view.team === p.team &&
        view.tick === snapshot.tick &&
        view.elapsed === snapshot.elapsed &&
        JSON.stringify(view.result) === JSON.stringify(snapshot.result),
      '玩家快照身分不符',
    );
    requirePvp(
      view.inputAck &&
        view.inputAck.tick === view.tick &&
        Number.isSafeInteger(view.inputAck.input_seq) &&
        Number.isSafeInteger(view.inputAck.command_seq) &&
        Array.isArray(view.inputAck.look_total) &&
        view.inputAck.look_total.length === 2 &&
        view.inputAck.look_total.every(Number.isFinite),
      '操作確認無效',
    );
    requirePvp(
      Array.isArray(view.actors) &&
        view.actors.length === roster.length &&
        new Set(view.actors.map((a: any) => a.id)).size === roster.length,
      '角色名單不符',
    );
    for (const member of roster) {
      const a = view.actors.find((x: any) => x.id === member.id);
      requirePvp(
        a &&
          a.team === member.team &&
          Array.isArray(a.position) &&
          a.position.length === 3 &&
          a.position.every(Number.isFinite) &&
          ['yaw', 'pitch', 'roll', 'speed', 'hp'].every((k) =>
            Number.isFinite(a[k]),
          ) &&
          a.hp >= 0 &&
          a.hp <= (a.team === 'air' ? 2 : 1) &&
          typeof a.alive === 'boolean' &&
          typeof a.departed === 'boolean',
        '角色狀態無效',
      );
      requirePvp(
        a.name === member.name &&
          Number.isInteger(a.hp) &&
          a.alive === a.hp > 0 &&
          (!a.departed || !a.alive) &&
          Number.isSafeInteger(a.kills) &&
          a.kills >= 0 &&
          Number.isFinite(a.vertical_speed) &&
          nonnegative(a.outside) &&
          nonnegative(a.next_fire) &&
          typeof a.aiming === 'boolean' &&
          typeof a.firing === 'boolean' &&
          vector(a.look_received, 2) &&
          vector(a.look_pending, 2),
        '角色詳細資料無效',
      );
      requirePvp(
        a.alive
          ? a.eliminationReason === null && a.eliminatedAt === null
          : ['missile', 'crash', 'boundary', 'departed'].includes(
              a.eliminationReason,
            ) &&
              nonnegative(a.eliminatedAt) &&
              a.eliminatedAt <= snapshot.elapsed + 1e-8,
        '淘汰狀態無效',
      );
      requirePvp(
        a.inputAck &&
          a.inputAck.tick === snapshot.tick &&
          typeof a.inputAck.stream === 'string' &&
          Number.isSafeInteger(a.inputAck.input_seq) &&
          a.inputAck.input_seq >= 0 &&
          Number.isSafeInteger(a.inputAck.command_seq) &&
          a.inputAck.command_seq >= 0 &&
          vector(a.inputAck.look_total, 2),
        '角色操作確認無效',
      );
    }
    requirePvp(
      Array.isArray(view.missiles) && view.missiles.length <= 64,
      '導彈資料無效',
    );
    requirePvp(
      new Set(view.missiles.map((m: any) => m.id)).size ===
        view.missiles.length &&
        view.missiles.every(
          (m: any) =>
            typeof m.id === 'string' &&
            vector(m.position) &&
            vector(m.forward) &&
            nonnegative(m.age) &&
            m.age <= 5 &&
            roster.some(
              (p: any) => p.id === m.owner_id && p.team === 'ground',
            ) &&
            roster.some((p: any) => p.id === m.target_id && p.team === 'air'),
        ),
      '導彈姿態或對應目標無效',
    );
    requirePvp(
      Math.abs(
        view.remainingSeconds - (room.time_limit_seconds - snapshot.elapsed),
      ) < 1e-7 &&
        nonnegative(view.cooldown) &&
        view.cooldown <= 1.25 + 1e-7 &&
        view.threats &&
        ['tracking', 'locked', 'missile'].every(
          (k) => typeof view.threats[k] === 'boolean',
        ),
      '玩家儀表無效',
    );
    requirePvp(
      view.locks &&
        Object.entries(view.locks).every(
          ([id, v]: any) =>
            roster.some((p: any) => p.id === id && p.team === 'air') &&
            nonnegative(v) &&
            v <= 1,
        ) &&
        Array.isArray(view.lock_valid) &&
        view.lock_valid.length <= 1 &&
        view.lock_valid.every((id: any) => id in view.locks) &&
        (view.lock_current === null || view.lock_current in view.locks),
      '鎖定資料無效',
    );
    requirePvp(
      Array.isArray(view.events) &&
        view.events.length <= 128 &&
        view.events.every(
          (e: any) =>
            Number.isSafeInteger(e.sequence) &&
            e.sequence > 0 &&
            ['weapon_fire', 'eliminated', 'hit', 'crash', 'boundary'].includes(
              e.kind,
            ),
        ),
      '戰鬥事件無效',
    );
    const world = JSON.stringify([view.actors, view.missiles, view.result]);
    requirePvp(!canonical || canonical === world, '玩家戰場彼此不一致');
    canonical = world;
  }
  if (snapshot.phase === 'active')
    requirePvp(!snapshot.result, '尚未結束不可指定勝方');
  else if (snapshot.phase === 'finished') {
    const r = snapshot.result,
      actors = snapshot.views[roster[0].id].actors;
    const expected = actors.map((a: any) => ({
      id: a.id,
      name: a.name,
      team: a.team,
      alive: a.alive,
      kills: a.kills,
      eliminationReason: a.eliminationReason,
    }));
    requirePvp(
      r && JSON.stringify(r.players) === JSON.stringify(expected),
      '結果玩家資料不符',
    );
    const air = actors.filter((a: any) => a.team === 'air'),
      ground = actors.filter((a: any) => a.team === 'ground');
    const alive = air.some((a: any) => a.alive),
      departed = parse(room.departures, {});
    requirePvp(
      r && r.runId === room.run_id && r.elapsed === snapshot.elapsed,
      '結果局次或時間不符',
    );
    requirePvp(
      (r.winner === 'ground' && r.reason === 'air_eliminated' && !alive) ||
        (r.winner === 'air' &&
          alive &&
          ((r.reason === 'timeout' &&
            snapshot.elapsed >= room.time_limit_seconds) ||
            (r.reason === 'ground_departed' &&
              ground.every((a: any) => departed[a.id])))),
      '勝方與戰場條件不符',
    );
  } else
    requirePvp(
      snapshot.result?.winner === null &&
        snapshot.result?.reason === 'all_departed' &&
        roster.every((p: any) => parse(room.departures, {})[p.id]),
      '中止必須對應全員退出',
    );
}
