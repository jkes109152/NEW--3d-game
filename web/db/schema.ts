import {
  sqliteTable,
  text,
  integer,
  primaryKey,
  index,
  uniqueIndex,
} from 'drizzle-orm/sqlite-core';

export const players = sqliteTable(
  'mp_players',
  {
    id: text('id').primaryKey(),
    name: text('name').notNull(),
    tokenHash: text('token_hash').notNull(),
    expiresAt: integer('expires_at').notNull(),
  },
  (t) => [uniqueIndex('idx_mp_players_token').on(t.tokenHash)],
);
export const rooms = sqliteTable(
  'mp_rooms',
  {
    id: text('id').primaryKey(),
    name: text('name').notNull(),
    hostId: text('host_id').notNull(),
    status: text('status').notNull().default('waiting'),
    mode: text('mode').notNull().default('coop'),
    rosterRevision: integer('roster_revision').notNull().default(0),
    startsAt: integer('starts_at'),
    timeLimitSeconds: integer('time_limit_seconds'),
    hostInstanceId: text('host_instance_id'),
    simulationSeenAt: integer('simulation_seen_at'),
    simulationTick: integer('simulation_tick').notNull().default(0),
    result: text('result'),
    departures: text('departures').notNull().default('{}'),
    runId: text('run_id'),
    levelA: integer('level_a').notNull().default(1),
    levelB: integer('level_b').notNull().default(1),
    campaign: integer('campaign').notNull().default(2),
    roster: text('roster').notNull().default('[]'),
    snapshot: text('snapshot'),
    sequence: integer('sequence').notNull().default(0),
    updatedAt: integer('updated_at').notNull(),
    createdAt: integer('created_at').notNull(),
  },
  (t) => [index('idx_mp_rooms_active').on(t.status, t.updatedAt)],
);
export const members = sqliteTable(
  'mp_members',
  {
    roomId: text('room_id').notNull(),
    playerId: text('player_id').notNull(),
    ready: integer('ready').notNull().default(0),
    profile: text('profile'),
    input: text('input').notNull().default('{}'),
    inputSeq: integer('input_seq').notNull().default(0),
    inputStream: text('input_stream'),
    inputInstance: text('input_instance'),
    inputReceivedAt: integer('input_received_at'),
    seenAt: integer('seen_at').notNull(),
  },
  (t) => [
    primaryKey({ columns: [t.roomId, t.playerId] }),
    uniqueIndex('idx_mp_members_player').on(t.playerId),
  ],
);
export const results = sqliteTable(
  'mp_results',
  {
    runId: text('run_id').notNull(),
    playerId: text('player_id').notNull(),
    profileId: text('profile_id').notNull(),
    rebirth: integer('rebirth').notNull(),
    reward: integer('reward').notNull(),
    partySize: integer('party_size').notNull(),
    levelA: integer('level_a').notNull(),
    levelB: integer('level_b').notNull(),
    campaign: integer('campaign').notNull(),
    createdAt: integer('created_at').notNull(),
    savedAt: integer('saved_at'),
  },
  (t) => [
    primaryKey({ columns: [t.runId, t.playerId] }),
    index('idx_mp_results_pending').on(t.playerId, t.savedAt, t.createdAt),
  ],
);
