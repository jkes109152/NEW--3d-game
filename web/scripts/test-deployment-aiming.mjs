import { test } from 'node:test';
import assert from 'node:assert/strict';
import { PerspectiveCamera, Vector3 } from 'three';
import { mapViewport, mapPoint, turretStock } from '../lib/deployment-ui.ts';
import {
  projectAircraft,
  movingReticle,
  labelPosition,
} from '../lib/aiming-hud.ts';
import { lastPlayedLabel } from '../lib/slot-display.ts';
import { AntiAirHud } from '../lib/aiming-hud.ts';

test('live HUD renders independent targets, fire feedback, offscreen removal and weapon cleanup',()=>{
  const oldDocument=globalThis.document;
  const root={hidden:true,innerHTML:'',className:'',setAttribute(){},remove(){this.removed=true;}};
  globalThis.document={createElement:()=>root};
  try {
    const camera=new PerspectiveCamera(60,16/9,.05,600);camera.updateMatrixWorld();
    const hud=new AntiAirHud({appendChild:()=>{}});
    const b={attempt_id:'demo',weapon_category:'anti_air',active_weapon_id:'W02',aiming:true,phase:'active',elapsed:0,lock_box_scale:2,fire_mode:'lock_multi',lock_seconds:3,lock_current:null,locks:{a:.2,b:.9,c:1},lock_valid:['a','b','c'],fire_blocked:'lock',events:[],aircraft:[{id:'a',position:[-2,0,50],hp:1,status:'approaching'},{id:'b',position:[2,0,50],hp:1,status:'approaching'},{id:'c',position:[0,2,50],hp:1,status:'approaching'}]};
    hud.update(b,camera,1280,720);
    assert.equal((root.innerHTML.match(/class="aa-mark /g)||[]).length,3);
    assert.match(root.innerHTML,/目標 1 20%/);assert.match(root.innerHTML,/目標 2 90%/);assert.match(root.innerHTML,/已鎖定 1／3/);assert.doesNotMatch(root.innerHTML,/aa-ready /);
    b.locks={a:1,b:1,c:1};b.fire_blocked='cooldown';hud.update(b,camera,1280,720);assert.match(root.innerHTML,/等待武器就緒/);assert.doesNotMatch(root.innerHTML,/class="aa-ready /);
    b.fire_blocked=null;hud.update(b,camera,1280,720);assert.match(root.innerHTML,/可齊射/);
    b.events=[{kind:'weapon_fire',weapon_id:'W02',sequence:1,endpoints:[[],[],[]]}];b.locks={};b.lock_valid=[];b.fire_blocked='cooldown';hud.update(b,camera,1280,720);assert.match(root.innerHTML,/已齊射 3 枚導彈/);assert.doesNotMatch(root.innerHTML,/class="aa-ready /);
    b.events=[];b.locks={a:.5};b.aircraft[0].position=[1000,0,50];hud.update(b,camera,1280,720);assert.equal((root.innerHTML.match(/class="aa-mark /g)||[]).length,0);
    b.aiming=false;hud.update(b,camera,1280,720);assert.match(root.innerHTML,/aa-acquire/);assert.doesNotMatch(root.innerHTML,/class="aa-mark /);
    b.weapon_category='pistol';hud.update(b,camera,1280,720);assert.equal(root.hidden,true);hud.dispose();assert.equal(root.removed,true);
  } finally {globalThis.document=oldDocument;}
});

test('deployment coordinates and circular range retain world proportions across aspect and zoom', () => {
  for (const [width, height] of [
    [600, 540],
    [320, 440],
    [1200, 600],
  ])
    for (const zoom of [1, 2, 4]) {
      const view = mapViewport({ x: 12, y: 80, zoom }, width / height);
      assert.ok(Math.abs(width / view.width - height / view.height) < 1e-9);
      assert.deepEqual(
        mapPoint(
          [width / 2, height / 2],
          { left: 0, top: 0, width, height },
          view,
        ),
        [12, 80],
      );
      const target = [-35, 150],
        pixel = [
          ((target[0] - view.left) / view.width) * width,
          ((view.top - target[1]) / view.height) * height,
        ];
      const restored = mapPoint(
        pixel,
        { left: 0, top: 0, width, height },
        view,
      );
      assert.ok(restored.every((v, i) => Math.abs(v - target[i]) < 1e-9));
    }
});
test('inventory tracks individual instances and removal returns only the affected unit', () => {
  const profile = {
    owned_turrets: [
      { instance_id: 'a', turret_id: 'T01' },
      { instance_id: 'b', turret_id: 'T01' },
      { instance_id: 'c', turret_id: 'T03' },
    ],
  };
  assert.deepEqual(
    turretStock(profile, [{ instance_id: 'a' }], 'T01').available.map(
      (v) => v.instance_id,
    ),
    ['b'],
  );
  assert.equal(turretStock(profile, [], 'T02').total, 0);
  assert.equal(turretStock(profile, [], 'T01').available.length, 2);
  assert.equal(
    turretStock(profile, [{ instance_id: 'a' }, { instance_id: 'b' }], 'T01')
      .available.length,
    0,
  );
});
test('AA reticle projects the existing model using its real camera, including moving views', () => {
  for (const [width, height] of [
    [1280, 720],
    [390, 844],
  ]) {
    const camera = new PerspectiveCamera(65, width / height, 0.05, 600);
    camera.position.set(4, 1.6, 9);
    camera.rotation.order = 'YXZ';
    camera.rotation.set(-0.1, 0.2, 0);
    camera.updateMatrixWorld();
    const world = new Vector3(0.1, 0.08, -1)
      .applyQuaternion(camera.quaternion)
      .multiplyScalar(60)
      .add(camera.position);
    const point = projectAircraft(
      [world.x, world.y, -world.z],
      camera,
      width,
      height,
    );
    const projected = world.clone().project(camera);
    assert.ok(Math.abs(point.x - ((projected.x + 1) * width) / 2) < 1e-8);
    assert.ok(Math.abs(point.y - ((1 - projected.y) * height) / 2) < 1e-8);
    const center = { x: width / 2, y: height / 2 },
      size = height * 0.21;
    const atZero = movingReticle(center, point, 0, size),
      atFull = movingReticle(center, point, 1, size);
    assert.deepEqual(atZero, center);
    assert.deepEqual(atFull, point);
    const halfway = movingReticle(center, point, 0.65, size);
    assert.ok(
      Math.abs(halfway.x - center.x - (point.x - center.x) * 0.65) < 1e-8,
    );
    const far = movingReticle(center, { x: width * 4, y: height * 4 }, 1, size);
    assert.equal(far.x, center.x + size / 2);
    assert.equal(far.y, center.y + size / 2);
    const behind = camera.position
      .clone()
      .add(new Vector3(0, 0, 10).applyQuaternion(camera.quaternion));
    assert.equal(
      projectAircraft([behind.x, behind.y, -behind.z], camera, width, height),
      null,
    );
  }
});
test('crossing targets keep separate, non-overlapping labels in phone and desktop layouts', () => {
  for (const [width, height] of [
    [390, 844],
    [1280, 720],
  ]) {
    const targets = Array.from({ length: 8 }, (_, i) => ({
      x: width / 2 + ((i % 3) - 1) * 24,
      y: height / 2 + Math.floor(i / 3) * 26,
    }));
    const boxes = [];
    for (const point of targets) {
      const box = labelPosition(point, width, height, boxes, targets, []);
      assert.ok(
        box.x >= 0 &&
          box.x + box.w <= width &&
          box.y >= 0 &&
          box.y + box.h <= height,
      );
      for (const other of boxes)
        assert.ok(
          box.x >= other.x + other.w ||
            box.x + box.w <= other.x ||
            box.y >= other.y + other.h ||
            box.y + box.h <= other.y,
        );
      boxes.push(box);
    }
  }
});
test('legacy or invalid play dates do not invent a timestamp', () => {
  for (const v of [null, undefined, 'broken', {}])
    assert.equal(lastPlayedLabel(v), '尚無日期紀錄');
  assert.match(lastPlayedLabel('2026-09-07T12:34:56Z'), /2026/);
});
