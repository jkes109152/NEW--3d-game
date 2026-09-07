import {
  cleanName,
  MAX_PLAYERS,
  personalReward,
  publicLoadout,
} from './multiplayer-rules';

const COOKIE = 'defense_party';
const id = () => crypto.randomUUID().replaceAll('-', '');
async function digest(value: string) {
  return Array.from(
    new Uint8Array(
      await crypto.subtle.digest('SHA-256', new TextEncoder().encode(value)),
    ),
    (b) => b.toString(16).padStart(2, '0'),
  ).join('');
}
class RequestError extends Error {
  constructor(
    message: string,
    public status = 400,
  ) {
    super(message);
  }
}
function requireValue(
  value: unknown,
  message: string,
  status = 400,
): asserts value {
  if (!value) throw new RequestError(message, status);
}
export async function multiplayerRequest(request: Request, db: D1Database) {
  const now = Date.now(),
    url = new URL(request.url);
  const reply = (data: unknown, extra: Record<string, string> = {}) =>
    Response.json(data, { headers: { 'Cache-Control': 'no-store', ...extra } });
  try {
    requireValue(request.method === 'POST', '請使用房間操作按鈕', 405);
    const origin = request.headers.get('origin');
    requireValue(
      !!origin &&
        new Set([
          url.origin,
          'https://game.jkesbyebye.com',
          'https://candy-defense-jkes.jkes109152.chatgpt.site',
          'http://localhost:3000',
          'http://127.0.0.1:3000',
        ]).has(origin),
      '來源不符',
      403,
    );
    requireValue(
      request.headers.get('content-type')?.startsWith('application/json'),
      '請使用遊戲介面操作',
      415,
    );
    const raw = await request.text();
    requireValue(raw.length < 750000, '房間資料過大', 413);
    const data = JSON.parse(raw),
      action = data.action;
    const token = request.headers
      .get('cookie')
      ?.split(';')
      .map((s) => s.trim())
      .find((s) => s.startsWith(COOKIE + '='))
      ?.slice(COOKIE.length + 1);
    let me: any = token
      ? await db
          .prepare(
            'SELECT id,name FROM mp_players WHERE token_hash=? AND expires_at>?',
          )
          .bind(await digest(token), now)
          .first()
      : null;
    if (action === 'identity') {
      const name = cleanName(data.name);
      if (me) {
        await db
          .prepare('UPDATE mp_players SET name=?,expires_at=? WHERE id=?')
          .bind(name, now + 30 * 86400000, me.id)
          .run();
        return reply({ me: { ...me, name } });
      }
      const secret = id() + id(),
        playerId = id();
      await db
        .prepare(
          'INSERT INTO mp_players(id,name,token_hash,expires_at) VALUES(?,?,?,?)',
        )
        .bind(playerId, name, await digest(secret), now + 30 * 86400000)
        .run();
      return reply(
        { me: { id: playerId, name } },
        {
          'Set-Cookie': `${COOKIE}=${secret}; HttpOnly; Path=/; SameSite=Strict; Max-Age=2592000${origin?.startsWith('https:') ? '; Secure' : ''}`,
        },
      );
    }
    if (action === 'lobby') {
      const rooms = await db
        .prepare(
          "SELECT r.id,r.name,r.status,r.level_a,r.level_b,p.name AS host_name,(SELECT count(*) FROM mp_members m WHERE m.room_id=r.id AND m.seen_at>?) AS count FROM mp_rooms r JOIN mp_players p ON p.id=r.host_id WHERE r.status IN ('waiting','playing') AND r.updated_at>? ORDER BY r.created_at DESC LIMIT 40",
        )
        .bind(now - 20000, now - 20000)
        .all();
      const membership = me
        ? await db
            .prepare('SELECT room_id FROM mp_members WHERE player_id=?')
            .bind(me.id)
            .first()
        : null;
      const pending = me
        ? await db
            .prepare(
              'SELECT * FROM mp_results WHERE player_id=? AND saved_at IS NULL ORDER BY created_at LIMIT 50',
            )
            .bind(me.id)
            .all()
        : { results: [] };
      return reply({
        me,
        rooms: rooms.results,
        roomId: (membership as any)?.room_id ?? null,
        receipts: pending.results,
      });
    }
    requireValue(me, '請先設定玩家名稱', 401);
    if (action === 'ack') {
      requireValue(typeof data.runId === 'string', '局次無效');
      await db
        .prepare(
          'UPDATE mp_results SET saved_at=? WHERE run_id=? AND player_id=?',
        )
        .bind(now, data.runId, me.id)
        .run();
      return reply({ saved: true });
    }
    if (action === 'create') {
      const name = cleanName(data.name || `${me.name}的房間`),
        roomId = id();
      const old: any = await db
        .prepare(
          'SELECT r.status,r.updated_at FROM mp_members m JOIN mp_rooms r ON r.id=m.room_id WHERE m.player_id=?',
        )
        .bind(me.id)
        .first();
      requireValue(
        !old || old.status === 'closed' || old.updated_at < now - 20000,
        '請先離開目前房間',
      );
      await db.batch([
        db.prepare('DELETE FROM mp_members WHERE player_id=?').bind(me.id),
        db
          .prepare(
            'INSERT INTO mp_rooms(id,name,host_id,updated_at,created_at) VALUES(?,?,?,?,?)',
          )
          .bind(roomId, name, me.id, now, now),
        db
          .prepare(
            'INSERT INTO mp_members(room_id,player_id,seen_at) VALUES(?,?,?)',
          )
          .bind(roomId, me.id, now),
      ]);
      return reply({ roomId });
    }
    const roomId = data.roomId;
    requireValue(
      typeof roomId === 'string' && /^[a-f0-9]{32}$/.test(roomId),
      '房間編號無效',
    );
    let room: any = await db
      .prepare('SELECT * FROM mp_rooms WHERE id=?')
      .bind(roomId)
      .first();
    requireValue(room, '找不到房間', 404);
    if (action === 'join') {
      requireValue(
        room.status === 'waiting' && room.updated_at > now - 20000,
        '房間已開始或已關閉',
      );
      const existing: any = await db
        .prepare('SELECT room_id FROM mp_members WHERE player_id=?')
        .bind(me.id)
        .first();
      requireValue(
        !existing || existing.room_id === roomId,
        '請先離開目前房間',
      );
      const inserted = await db
        .prepare(
          "INSERT OR IGNORE INTO mp_members(room_id,player_id,seen_at) SELECT ?,?,? WHERE (SELECT status FROM mp_rooms WHERE id=?)='waiting' AND (SELECT count(*) FROM mp_members WHERE room_id=?)<?",
        )
        .bind(roomId, me.id, now, roomId, roomId, MAX_PLAYERS)
        .run();
      requireValue(
        inserted.meta.changes || existing?.room_id === roomId,
        '房間已滿或已開始',
      );
      return reply({ roomId });
    }
    const membership: any = await db
      .prepare('SELECT * FROM mp_members WHERE room_id=? AND player_id=?')
      .bind(roomId, me.id)
      .first();
    requireValue(membership, '你已離開此房間', 403);
    const host = room.host_id === me.id;
    if (action === 'leave') {
      const statements = [
        db
          .prepare('DELETE FROM mp_members WHERE room_id=? AND player_id=?')
          .bind(roomId, me.id),
      ];
      if (host)
        statements.push(
          db
            .prepare(
              "UPDATE mp_rooms SET status='closed',snapshot=NULL,updated_at=? WHERE id=?",
            )
            .bind(now, roomId),
        );
      await db.batch(statements);
      return reply({ left: true });
    }
    if (room.updated_at < now - 20000 && room.status !== 'finished') {
      await db
        .prepare(
          "UPDATE mp_rooms SET status='closed',snapshot=NULL WHERE id=? AND updated_at<?",
        )
        .bind(roomId, now - 20000)
        .run();
      room.status = 'closed';
    }
    if (action === 'ready') {
      requireValue(room.status === 'waiting', '本局已開始');
      const profile = data.ready ? publicLoadout(data.profile) : null;
      await db
        .prepare(
          "UPDATE mp_members SET ready=?,profile=?,seen_at=? WHERE room_id=? AND player_id=? AND (SELECT status FROM mp_rooms WHERE id=?)='waiting'",
        )
        .bind(
          profile ? 1 : 0,
          profile ? JSON.stringify(profile) : null,
          now,
          roomId,
          me.id,
          roomId,
        )
        .run();
    } else if (action === 'start') {
      requireValue(host, '只有房主可以開始', 403);
      const all: any = await db
        .prepare(
          'SELECT m.player_id AS id,p.name,m.profile FROM mp_members m JOIN mp_players p ON p.id=m.player_id WHERE m.room_id=? ORDER BY CASE WHEN m.player_id=? THEN 0 ELSE 1 END,m.player_id',
        )
        .bind(roomId, me.id)
        .all();
      const roster = all.results.map((m: any) => ({
        ...m,
        profile: JSON.parse(m.profile || 'null'),
      }));
      requireValue(
        roster.length >= 2 && roster.every((m: any) => m.profile),
        '至少兩人，且所有玩家皆需準備完成',
      );
      const campaign = Math.min(
        ...roster.map((m: any) => m.profile.rebirth_count + 2),
      );
      const a = room.level_a <= campaign ? room.level_a : 1;
      const b =
        room.level_b <= (a === campaign ? 2 * a + 1 : a + 1) ? room.level_b : 1;
      const result = await db
        .prepare(
          "UPDATE mp_rooms SET status='playing',run_id=?,roster=?,campaign=?,level_a=?,level_b=?,snapshot=NULL,sequence=0,updated_at=? WHERE id=? AND status='waiting' AND (SELECT count(*) FROM mp_members WHERE room_id=?)=? AND NOT EXISTS(SELECT 1 FROM mp_members WHERE room_id=? AND (ready=0 OR seen_at<?))",
        )
        .bind(
          id(),
          JSON.stringify(roster),
          campaign,
          a,
          b,
          now,
          roomId,
          roomId,
          roster.length,
          roomId,
          now - 10000,
        )
        .run();
      requireValue(result.meta.changes, '玩家或準備狀態已變更，請重試');
    } else if (action === 'exchange') {
      await db
        .prepare(
          'UPDATE mp_members SET seen_at=? WHERE room_id=? AND player_id=?',
        )
        .bind(now, roomId, me.id)
        .run();
      if (host) {
        await db
          .prepare(
            "UPDATE mp_rooms SET updated_at=? WHERE id=? AND status NOT IN ('closed')",
          )
          .bind(now, roomId)
          .run();
        if (room.status === 'waiting')
          await db
            .prepare(
              'DELETE FROM mp_members WHERE room_id=? AND player_id<>? AND seen_at<?',
            )
            .bind(roomId, me.id, now - 20000)
            .run();
      }
      if (room.status === 'playing' && data.input) {
        requireValue(
          Number.isSafeInteger(data.inputSeq) &&
            data.inputSeq >= 0 &&
            JSON.stringify(data.input).length < 20000,
          '操作資料無效',
        );
        await db
          .prepare(
            'UPDATE mp_members SET input=?,input_seq=? WHERE room_id=? AND player_id=? AND input_seq<?',
          )
          .bind(
            JSON.stringify(data.input),
            data.inputSeq,
            roomId,
            me.id,
            data.inputSeq,
          )
          .run();
      }
      if (data.snapshot) {
        requireValue(host, '只有房主可同步戰場', 403);
        requireValue(
          room.status === 'playing' && data.runId === room.run_id,
          '局次已變更',
        );
        const snapshot = data.snapshot;
        requireValue(
          snapshot &&
            snapshot.views &&
            Object.keys(snapshot.views).length <= MAX_PLAYERS &&
            Number.isSafeInteger(data.sequence),
          '戰場資料無效',
        );
        await db
          .prepare(
            "UPDATE mp_rooms SET snapshot=?,sequence=? WHERE id=? AND run_id=? AND status='playing' AND sequence<?",
          )
          .bind(
            JSON.stringify(snapshot),
            data.sequence,
            roomId,
            room.run_id,
            data.sequence,
          )
          .run();
      }
    } else if (action === 'finish') {
      requireValue(host, '只有房主可結算戰場', 403);
      requireValue(data.runId === room.run_id, '局次已變更');
      if (room.status !== 'finished') {
        requireValue(room.status === 'playing', '本局已結束');
        const snap = JSON.parse(room.snapshot || 'null');
        requireValue(
          snap && ['success', 'failure'].includes(snap.phase),
          '戰鬥尚未完成',
        );
        const roster = JSON.parse(room.roster),
          success = snap.phase === 'success';
        const statements = roster.map((m: any) =>
          db
            .prepare(
              'INSERT OR IGNORE INTO mp_results(run_id,player_id,profile_id,rebirth,reward,party_size,level_a,level_b,campaign,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)',
            )
            .bind(
              room.run_id,
              m.id,
              m.profile.profile_id,
              m.profile.rebirth_count,
              success
                ? personalReward(
                    room.level_a,
                    room.level_b,
                    room.campaign,
                    m.profile.rebirth_count,
                    roster.length,
                  )
                : 0,
              roster.length,
              room.level_a,
              room.level_b,
              room.campaign,
              now,
            ),
        );
        statements.push(
          db
            .prepare(
              "UPDATE mp_rooms SET status='finished',updated_at=? WHERE id=? AND run_id=? AND status='playing'",
            )
            .bind(now, roomId, room.run_id),
        );
        await db.batch(statements);
      }
    } else if (action === 'again') {
      requireValue(
        host && room.status === 'finished',
        '只有房主可開始下一局',
        403,
      );
      const snap = JSON.parse(room.snapshot || 'null'),
        limit =
          room.level_a === room.campaign
            ? 2 * room.level_a + 1
            : room.level_a + 1;
      const next =
        snap?.phase === 'success'
          ? room.level_b < limit
            ? [room.level_a, room.level_b + 1]
            : room.level_a < room.campaign
              ? [room.level_a + 1, 1]
              : [1, 1]
          : [1, 1];
      await db.batch([
        db
          .prepare(
            "UPDATE mp_rooms SET status='waiting',snapshot=NULL,run_id=NULL,roster='[]',level_a=?,level_b=?,updated_at=? WHERE id=? AND status='finished'",
          )
          .bind(...next, now, roomId),
        db
          .prepare(
            "UPDATE mp_members SET ready=0,input_seq=0,input='{}' WHERE room_id=?",
          )
          .bind(roomId),
      ]);
    } else if (!['ready', 'start'].includes(action))
      throw new RequestError('未知房間操作');
    room = await db
      .prepare('SELECT * FROM mp_rooms WHERE id=?')
      .bind(roomId)
      .first();
    const rows = await db
      .prepare(
        'SELECT m.player_id AS id,p.name,m.ready,m.seen_at,m.input,m.input_seq FROM mp_members m JOIN mp_players p ON p.id=m.player_id WHERE m.room_id=? ORDER BY m.player_id',
      )
      .bind(roomId)
      .all();
    const roster = JSON.parse(room.roster),
      snapshot = room.snapshot ? JSON.parse(room.snapshot) : null;
    const pending = await db
      .prepare(
        'SELECT * FROM mp_results WHERE player_id=? AND saved_at IS NULL ORDER BY created_at LIMIT 50',
      )
      .bind(me.id)
      .all();
    const receipt = room.run_id
      ? await db
          .prepare('SELECT * FROM mp_results WHERE run_id=? AND player_id=?')
          .bind(room.run_id, me.id)
          .first()
      : null;
    return reply({
      me,
      room: {
        id: room.id,
        name: room.name,
        hostId: room.host_id,
        status: room.status,
        runId: room.run_id,
        level: [room.level_a, room.level_b, room.campaign],
        sequence: room.sequence,
        roster: host
          ? roster
          : roster.map((m: any) => ({ id: m.id, name: m.name })),
        members: rows.results.map((m: any) => ({
          id: m.id,
          name: m.name,
          ready: !!m.ready,
          online: m.seen_at > now - 5000,
          ...(host
            ? { input: JSON.parse(m.input), inputSeq: m.input_seq }
            : {}),
        })),
        receipts: pending.results,
        snapshot: host
          ? null
          : snapshot
            ? { phase: snapshot.phase, view: snapshot.views[me.id] }
            : null,
        receipt,
      },
    });
  } catch (error) {
    if (error instanceof RequestError)
      return Response.json(
        { error: error.message },
        { status: error.status, headers: { 'Cache-Control': 'no-store' } },
      );
    if (error instanceof SyntaxError)
      return Response.json({ error: '房間資料格式無效' }, { status: 400 });
    console.error(
      'multiplayer request failed',
      error instanceof Error ? error.message : 'unknown',
    );
    return Response.json(
      { error: '房間操作未完成，請稍後重試。' },
      { status: 400, headers: { 'Cache-Control': 'no-store' } },
    );
  }
}
