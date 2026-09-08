export type PvpTeam = 'ground' | 'air';
export type PvpPhase = 'active' | 'finished' | 'aborted';
export type Vec3 = [number, number, number];
export type Pair = [number, number];
export type PvpRoster = { id: string; name: string; team: PvpTeam }[];
export type PvpCommand = {
  sequence: number;
  kind: 'fire_down' | 'fire_up' | 'toggle_aim' | 'jump';
};
export interface PvpInput {
  suspended: boolean;
  cancelThrough: number;
  move_x: number;
  move_z: number;
  turn_x: number;
  turn_y: number;
  throttle: number;
  roll: number;
  look_total: Pair;
  aspect: number;
  commands: PvpCommand[];
}
export interface InputAck {
  stream: string;
  input_seq: number;
  command_seq: number;
  look_total: Pair;
  tick: number;
}
export interface PvpActor {
  id: string;
  name: string;
  team: PvpTeam;
  position: Vec3;
  yaw: number;
  pitch: number;
  roll: number;
  speed: number;
  vertical_speed: number;
  hp: number;
  alive: boolean;
  departed: boolean;
  eliminationReason: string | null;
  eliminatedAt: number | null;
  outside: number;
  kills: number;
  aiming: boolean;
  firing: boolean;
  next_fire: number;
  look_received: Pair;
  look_pending: Pair;
  inputAck: InputAck;
}
export interface PvpMissile {
  id: string;
  owner_id: string;
  target_id: string;
  position: Vec3;
  forward: Vec3;
  age: number;
}
export interface PvpResult {
  runId: string;
  winner: PvpTeam | null;
  reason: string;
  elapsed: number;
  players: {
    id: string;
    name: string;
    team: PvpTeam;
    alive: boolean;
    kills: number;
    eliminationReason: string | null;
  }[];
}
export interface PvpView {
  runId: string;
  selfId: string;
  team: PvpTeam;
  phase: PvpPhase;
  tick: number;
  elapsed: number;
  remainingSeconds: number;
  actors: PvpActor[];
  missiles: PvpMissile[];
  inputAck: InputAck;
  locks: Record<string, number>;
  lock_current: string | null;
  lock_valid: string[];
  cooldown: number;
  threats: { tracking: boolean; locked: boolean; missile: boolean };
  result: PvpResult | null;
  events: { sequence: number; kind: string; [key: string]: unknown }[];
}
export interface PvpSnapshot {
  mode: 'pvp';
  protocolVersion: 1;
  runId: string;
  phase: PvpPhase;
  tick: number;
  elapsed: number;
  result: PvpResult | null;
  views: Record<string, PvpView>;
}
export interface HostInput {
  playerId: string;
  inputStream: string;
  inputInstance: string | null;
  inputSeq: number;
  input: PvpInput;
  inputReceivedAt: number | null;
  lastSeenAt: number;
}
export type Departures = Record<
  string,
  { at: number; reason: 'left' | 'timeout' }
>;
export interface PredictionFrame {
  runId: string;
  stream: string;
  tick: number;
  dt: number;
  inputSeqAtCapture: number;
  input: PvpInput;
}
export const PVP_STEP = 1 / 120;
export const neutralInput = (): PvpInput => ({
  suspended: true,
  cancelThrough: 0,
  move_x: 0,
  move_z: 0,
  turn_x: 0,
  turn_y: 0,
  throttle: 0,
  roll: 0,
  look_total: [0, 0],
  aspect: 16 / 9,
  commands: [],
});
