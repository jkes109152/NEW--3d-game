import { neutralInput } from './pvp-types.ts';
export class MultiplayerClient {
  open = false;
  me: any = null;
  rooms: any[] = [];
  room: any = null;
  error = '';
  busy = false;
  private timer: ReturnType<typeof setTimeout> | null = null;
  private timerDelay = 0;
  private stopped = false;
  private polling = false;
  private queue: Promise<any> = Promise.resolve();
  private input: any = { suspended: true };
  private inputSeq = Date.now();
  private stream = crypto.randomUUID();
  private outgoing: any = null;
  private lookTotals = [0, 0];
  private pendingCommands = new Map<number, any>();
  private sequence = 0;
  private started = 0;
  readonly instanceId = crypto.randomUUID();
  private pvpBound = '';
  private pvpEvicted = false;
  private pvpCancel = 0;
  private pvpCancelPending = false;
  private pvpCancelSeq = 0;
  private pvpInput = neutralInput();
  constructor(
    private changed: () => void,
    private received: (room: any) => void,
    private transport: typeof fetch = (input, init) =>
      globalThis.fetch(input, init),
    private clock: () => number = () => performance.now(),
  ) {}
  state() {
    return {
      open: this.open,
      me: this.me,
      rooms: this.rooms,
      room: this.room,
      error: this.error,
      busy: this.busy,
    };
  }
  private request(data: any): Promise<any> {
    const run = async () => {
      const response = await this.transport('/api/multiplayer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
        cache: 'no-store',
        signal: AbortSignal.timeout(8000),
      }).catch(() => {
        throw Error('目前無法連線，請確認網路後重試');
      });
      const value: any = await response.json().catch(() => {
        throw Error('連線服務暫時無法回應，請稍後重試');
      });
      if (!response.ok) throw Error(value.error || '連線失敗');
      return value;
    };
    const next = this.queue.then(run, run);
    this.queue = next.catch(() => {});
    return next;
  }
  async action(action: string, payload: any = {}) {
    this.busy = true;
    this.error = '';
    this.changed();
    try {
      if (action === 'open') {
        this.open = true;
        await this.lobby();
        this.schedule();
        return;
      }
      if (action === 'close') {
        this.open = false;
        this.changed();
        return;
      }
      const data = await this.request({
        action,
        roomId: this.room?.id,
        runId: this.room?.runId,
        instanceId: this.instanceId,
        protocolVersion: 1,
        ...payload,
      });
      if (data.me) this.me = data.me;
      if (data.roomId) {
        this.room = { id: data.roomId, status: 'connecting', members: [] };
        await this.poll();
      }
      if (data.room) this.accept(data.room);
      if (action === 'identity') await this.lobby();
      if (action === 'leave') {
        this.room = null;
        this.outgoing = null;
        this.pvpBound = '';
        this.pvpEvicted = false;
        await this.lobby();
      }
      this.schedule();
    } catch (error: any) {
      this.error = error.message;
    } finally {
      this.busy = false;
      this.changed();
    }
  }
  private async lobby() {
    const data = await this.request({ action: 'lobby' });
    this.me = data.me;
    this.rooms = data.rooms;
    if (data.receipts?.length)
      this.received({ status: 'rewards', receipts: data.receipts });
    if (data.roomId && !this.room) {
      this.room = { id: data.roomId, status: 'connecting', members: [] };
      await this.poll();
    }
    this.changed();
  }
  private accept(room: any) {
    if (room.runId !== this.room?.runId) {
      this.outgoing = null;
      this.lookTotals = [0, 0];
      this.pendingCommands.clear();
      this.input = { suspended: true };
      this.stream = crypto.randomUUID();
      this.pvpBound = '';
      this.pvpEvicted = false;
      this.pvpCancel = 0;
      this.pvpCancelPending = false;
      this.pvpCancelSeq = 0;
      this.pvpInput = neutralInput();
    }
    if (
      room.mode === 'pvp' &&
      room.inputInstance === this.instanceId &&
      room.currentStream
    ) {
      this.pvpBound = room.currentStream;
      this.stream = room.currentStream;
    }
    if (room.mode === 'pvp' && room.view?.inputAck?.stream === this.pvpBound) {
      const ack = room.view.inputAck;
      for (const sequence of this.pendingCommands.keys())
        if (sequence <= ack.command_seq) this.pendingCommands.delete(sequence);
      if (
        this.pvpCancelPending &&
        ack.command_seq >= this.pvpCancel &&
        ack.input_seq >= this.pvpCancelSeq &&
        this.pvpCancelSeq > 0
      )
        this.pvpCancelPending = false;
    }
    this.room = room;
    this.received(room);
    this.changed();
    if (this.open && !this.polling) this.schedule();
  }
  setInput(frame: any) {
    if (this.room?.mode === 'pvp') {
      this.setPvpInput(frame);
      return;
    }
    if (frame.suspended) {
      this.pendingCommands.clear();
      this.input = { suspended: true, commands: [], look_delta: [0, 0] };
      return;
    }
    this.lookTotals[0] += frame.look_delta?.[0] || 0;
    this.lookTotals[1] += frame.look_delta?.[1] || 0;
    for (const command of frame.commands || [])
      this.pendingCommands.set(command.sequence, command);
    const previous = this.input;
    this.input = {
      ...frame,
      commands: [...(previous.commands || []), ...(frame.commands || [])].slice(
        -96,
      ),
      look_delta: [
        (previous.look_delta?.[0] || 0) + (frame.look_delta?.[0] || 0),
        (previous.look_delta?.[1] || 0) + (frame.look_delta?.[1] || 0),
      ],
    };
  }
  setSnapshot(snapshot: any) {
    if (snapshot.mode === 'pvp') {
      this.outgoing = snapshot;
      return;
    }
    if (
      this.outgoing &&
      (Object.values(this.outgoing.views)[0] as any)?.attempt_id ===
        (Object.values(snapshot.views)[0] as any)?.attempt_id &&
      this.outgoing.views &&
      snapshot.views
    ) {
      const previous = Object.values(this.outgoing.views)[0] as any;
      const incoming = Object.values(snapshot.views)[0] as any;
      const events = [
        ...new Map(
          [...(previous?.events || []), ...(incoming?.events || [])].map(
            (e: any) => [e.sequence, e],
          ),
        ).values(),
      ].slice(-128);
      snapshot = {
        ...snapshot,
        views: Object.fromEntries(
          Object.entries(snapshot.views).map(([k, v]: any) => [
            k,
            { ...v, events },
          ]),
        ),
      };
    }
    this.outgoing = snapshot;
  }
  async acknowledge(runId: string) {
    try {
      await this.request({ action: 'ack', runId });
    } catch {}
  }

  predictView(view: any) {
    if (view.input_stream === this.stream)
      for (const seq of this.pendingCommands.keys())
        if (seq <= (view.command_ack ?? -1)) this.pendingCommands.delete(seq);
    const ack =
      view.input_stream === this.stream
        ? view.look_total_ack || [0, 0]
        : [0, 0];
    return {
      ...view,
      yaw: view.yaw + this.lookTotals[0] - ack[0],
      pitch: Math.max(
        -85,
        Math.min(85, view.pitch + this.lookTotals[1] - ack[1]),
      ),
    };
  }
  private async poll() {
    if (!this.room) {
      if (this.open) await this.lobby();
      return;
    }
    if (this.room.status === 'connecting') {
      const data = await this.request({
        action: 'sync',
        roomId: this.room.id,
        protocolVersion: 1,
        instanceId: this.instanceId,
      });
      this.accept(data.room);
      return;
    }
    if (this.room.mode === 'pvp') {
      await this.pollPvp();
      return;
    }
    const input = this.input;
    this.input = { ...input, commands: [], look_delta: [0, 0] };
    const room = this.room,
      host = this.me?.id === room.hostId;
    const snapshot = host && room.status === 'playing' ? this.outgoing : null;
    const seq = ++this.inputSeq;
    const data = await this.request({
      action: 'exchange',
      roomId: room.id,
      input: {
        ...input,
        commands: input.suspended
          ? []
          : [...this.pendingCommands.values()].slice(-96),
        look_total: this.lookTotals,
        stream: this.stream,
      },
      inputSeq: seq,
      ...(snapshot
        ? { snapshot, sequence: ++this.sequence, runId: room.runId }
        : {}),
    });
    this.error = '';
    this.started = Date.now();
    this.accept(data.room);
    if (
      host &&
      snapshot &&
      ['success', 'failure'].includes(snapshot.phase) &&
      data.room.status === 'playing'
    ) {
      const result = await this.request({
        action: 'finish',
        roomId: room.id,
        runId: room.runId,
      });
      this.accept(result.room);
    }
  }
  private schedule(elapsed = 0, failed = false) {
    if (this.stopped) return;
    const delay = ['playing', 'countdown'].includes(this.room?.status)
      ? 50
      : this.room
        ? 800
        : 2000;
    if (this.timer && this.timerDelay === delay) return;
    if (this.timer) clearTimeout(this.timer);
    this.timerDelay = delay;
    this.timer = setTimeout(
      async () => {
        this.timer = null;
        if (this.stopped) return;
        const began = this.clock();
        let failed = false;
        if (!this.busy && !this.polling) {
          this.polling = true;
          try {
            await this.poll();
          } catch (error: any) {
            failed = true;
            this.error = `連線中斷：${error.message}，正在重試`;
            if (Date.now() - this.started > 10000 && this.room)
              this.received({ ...this.room, connectionLost: true });
            this.changed();
          } finally {
            this.polling = false;
          }
        }
        this.schedule(this.clock() - began, failed);
      },
      failed ? Math.max(800, delay) : Math.max(0, delay - elapsed),
    );
  }
  dispose() {
    this.stopped = true;
    if (this.timer) clearTimeout(this.timer);
  }
  pvpControlState() {
    return {
      stream: this.pvpBound,
      inputSeq: this.inputSeq,
      input: {
        ...this.pvpInput,
        commands: [...this.pendingCommands.values()],
        look_total: [...this.lookTotals],
      },
      waiting: this.pvpCancelPending,
      evicted: this.pvpEvicted,
    };
  }
  private setPvpInput(frame: any) {
    if (frame.suspended || this.pendingCommands.size >= 96) {
      if (!this.pvpInput.suspended) {
        this.pvpCancel = Math.max(
          this.pvpCancel,
          ...this.pendingCommands.keys(),
          0,
        );
        this.pvpCancelPending = true;
        this.pvpCancelSeq = 0;
      }
      this.pendingCommands.clear();
      this.pvpInput = {
        ...neutralInput(),
        look_total: [this.lookTotals[0], this.lookTotals[1]],
        cancelThrough: this.pvpCancel,
      };
      return;
    }
    if (this.pvpCancelPending || this.pvpEvicted || !this.pvpBound) return;
    this.lookTotals[0] += frame.look_delta?.[0] || 0;
    this.lookTotals[1] += frame.look_delta?.[1] || 0;
    for (const c of frame.commands || [])
      this.pendingCommands.set(c.sequence, c);
    this.pvpInput = {
      ...neutralInput(),
      ...frame,
      suspended: false,
      cancelThrough: this.pvpCancel,
      look_total: [this.lookTotals[0], this.lookTotals[1]],
      commands: [...this.pendingCommands.values()],
    };
  }
  private async pollPvp() {
    let room = this.room;
    const base = () => ({
      roomId: room.id,
      runId: room.runId,
      protocolVersion: 1,
      instanceId: this.instanceId,
    });
    if (this.pvpEvicted) return;
    if (!room.runId || ['finished', 'closed'].includes(room.status)) {
      this.accept((await this.request({ action: 'sync', ...base() })).room);
      return;
    }
    try {
      if (!this.pvpBound) {
        const sync = await this.request({ action: 'sync', ...base() });
        this.accept(sync.room);
        room = this.room;
        if (!room.runId || !['countdown', 'playing'].includes(room.status))
          return;
        this.accept(
          (
            await this.request({
              action: 'resume',
              ...base(),
              expectedStream: room.currentStream,
            })
          ).room,
        );
        room = this.room;
      }
      const sequence = ++this.inputSeq;
      if (this.pvpCancelPending && !this.pvpCancelSeq)
        this.pvpCancelSeq = sequence;
      const snapshot =
        room.hostId === this.me?.id &&
        room.status === 'playing' &&
        this.outgoing?.runId === room.runId
          ? this.outgoing
          : null;
      const result = await this.request({
        action: 'exchange',
        ...base(),
        inputStream: this.pvpBound,
        inputSeq: sequence,
        input: {
          ...this.pvpInput,
          commands: [...this.pendingCommands.values()],
          look_total: this.lookTotals,
        },
        ...(snapshot ? { snapshot, sequence: ++this.sequence } : {}),
      });
      this.error = '';
      this.started = Date.now();
      this.accept(result.room);
      if (snapshot?.phase === 'finished' && result.room.status === 'playing')
        this.accept((await this.request({ action: 'finish', ...base() })).room);
    } catch (error: any) {
      if (error.message.includes('另一分頁')) {
        this.pvpEvicted = true;
        this.setPvpInput({ suspended: true });
      }
      throw error;
    }
  }
}
