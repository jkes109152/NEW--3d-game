export class MultiplayerClient {
  open = false;
  me: any = null;
  rooms: any[] = [];
  room: any = null;
  error = '';
  busy = false;
  private timer: ReturnType<typeof setTimeout> | null = null;
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
  constructor(
    private changed: () => void,
    private received: (room: any) => void,
    private transport: typeof fetch = fetch,
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
      });
      const value: any = await response.json();
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
  }
  private accept(room: any) {
    if (room.runId !== this.room?.runId) {
      this.outgoing = null;
      this.lookTotals = [0, 0];
      this.pendingCommands.clear();
      this.input = { suspended: true };
      this.stream = crypto.randomUUID();
    }
    this.room = room;
    this.received(room);
    this.changed();
  }
  setInput(frame: any) {
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
  private schedule() {
    if (this.timer || this.stopped) return;
    this.timer = setTimeout(
      async () => {
        this.timer = null;
        if (this.stopped) return;
        if (!this.busy && !this.polling) {
          this.polling = true;
          try {
            await this.poll();
          } catch (error: any) {
            this.error = `連線中斷：${error.message}，正在重試`;
            if (Date.now() - this.started > 10000 && this.room)
              this.received({ ...this.room, connectionLost: true });
            this.changed();
          } finally {
            this.polling = false;
          }
        }
        this.schedule();
      },
      this.room?.status === 'playing' ? 120 : this.room ? 800 : 2000,
    );
  }
  dispose() {
    this.stopped = true;
    if (this.timer) clearTimeout(this.timer);
  }
}
