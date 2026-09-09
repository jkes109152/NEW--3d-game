import type { PvpControls } from './pvp-controls.ts';

export function bindPvpMouse(
  canvas: HTMLCanvasElement,
  controls: PvpControls,
  isGround: () => boolean,
  doc: Document = document,
  win: Window = window,
) {
  let rightHeld = false;
  const off: (() => void)[] = [];
  const listen = (
    target: EventTarget,
    name: string,
    handler: EventListener,
  ) => {
    target.addEventListener(name, handler, { capture: true });
    off.push(() =>
      target.removeEventListener(name, handler, { capture: true }),
    );
  };
  const owns = (event: Event) =>
    controls.enabled &&
    (doc.pointerLockElement === canvas || event.target === canvas);
  const aim = (event: MouseEvent) => {
    // 在預設選單／失焦之前攔截；相容 mousedown 不可再切換一次。
    event.preventDefault();
    event.stopPropagation();
    if (!rightHeld && isGround()) controls.command('toggle_aim');
    rightHeld = true;
  };
  listen(doc, 'pointerdown', ((event: PointerEvent) => {
    if (owns(event) && event.button === 2) aim(event);
  }) as EventListener);
  listen(doc, 'mousedown', ((event: MouseEvent) => {
    if (!owns(event)) return;
    if (event.button === 2) aim(event);
    else if (event.button === 0 && isGround()) {
      event.preventDefault();
      controls.command('fire_down');
    }
  }) as EventListener);
  listen(win, 'mouseup', ((event: MouseEvent) => {
    if (event.button === 2) rightHeld = false;
    if (event.button === 0 && isGround()) controls.command('fire_up');
  }) as EventListener);
  listen(doc, 'pointerup', ((event: PointerEvent) => {
    if (event.button === 2) rightHeld = false;
  }) as EventListener);
  for (const name of ['contextmenu', 'auxclick'])
    listen(doc, name, (event) => {
      if (!owns(event)) return;
      event.preventDefault();
      event.stopPropagation();
    });
  const reset = () => {
    rightHeld = false;
  };
  listen(win, 'blur', reset);
  listen(doc, 'pointercancel', reset);
  listen(doc, 'pointerlockchange', reset);
  return () => off.forEach((remove) => remove());
}
