// Demo of the critically damped spring, rendered by the family verifier and usable as an example: a value chart in
// 3D. A grey step signal jumps between targets; the orange tube is the spring following it, the blue tube the same
// spring with a speed limit. The baseline shows the chart with the signal alone.

const DURATION = 3;
const JUMPS = [[0, 0], [0.25, 1], [1.75, 0.25]];

function targetAt(time) {
  let value = JUMPS[0][1];
  for (const [start, level] of JUMPS) if (time >= start - 1e-9) value = level;
  return value;
}

function simulate(spring, rate, smoothTime, maxSpeed) {
  const samples = [[0, 0]];
  let state = {value: 0, velocity: 0};
  const steps = Math.round(DURATION * rate);
  for (let k = 0; k < steps; k += 1) {
    state = spring.smoothDamp(state.value, targetAt(k / rate), state.velocity, smoothTime, 1 / rate, maxSpeed);
    samples.push([(k + 1) / rate, state.value]);
  }
  return samples;
}

export function demo(THREE, spring, harness) {
  const toPoint = ([time, value]) => new THREE.Vector3(-2.2 + (4.4 * time) / DURATION, -1.25 + 2.4 * value, 0);
  const smoothTime = 0.3;
  const free = simulate(spring, 120, smoothTime, Infinity);
  const limited = simulate(spring, 120, smoothTime, 1.2);

  // The browser's run against the closed form x(t) = 1 - (1 + w t) e^(-w t) after the first jump from rest.
  const omega = 2 / smoothTime;
  let worst = 0;
  for (const [time, value] of free) {
    if (time <= 0.25 || time > 1.75) continue;
    const elapsed = time - 0.25;
    worst = Math.max(worst, Math.abs(value - (1 - (1 + omega * elapsed) * Math.exp(-omega * elapsed))));
  }
  harness.check('closed_form_after_the_jump', worst < 1e-9, {worst_difference: worst});
  const slow = simulate(spring, 40, smoothTime, Infinity);
  const ending = Math.abs(slow[slow.length - 1][1] - free[free.length - 1][1]);
  harness.check('same_end_at_40_and_120_hz', ending < 1e-9, {difference: ending});
  let fastest = 0;
  for (let k = 1; k < limited.length; k += 1) {
    fastest = Math.max(fastest, Math.abs(limited[k][1] - limited[k - 1][1]) * 120);
  }
  harness.check('speed_limit_respected', fastest <= 1.2 * (1 + 1e-9) && fastest > 1.1, {fastest_per_second: fastest});

  const background = new THREE.Color(0x141a26);
  const build = (withSprings) => {
    const scene = new THREE.Scene();
    scene.background = background;
    const grid = new THREE.GridHelper(4.8, 12, 0x3a4a66, 0x26324a);
    grid.rotation.x = Math.PI / 2;
    grid.position.y = 0.05;
    scene.add(grid);
    const signal = new THREE.CurvePath();
    const corners = [];
    JUMPS.forEach(([start, level], index) => {
      const end = index + 1 < JUMPS.length ? JUMPS[index + 1][0] : DURATION;
      corners.push(toPoint([start, level]), toPoint([end, level]));
    });
    for (let k = 0; k + 1 < corners.length; k += 1) signal.add(new THREE.LineCurve3(corners[k], corners[k + 1]));
    scene.add(new THREE.Mesh(new THREE.TubeGeometry(signal, 240, 0.025, 8, false),
      new THREE.MeshBasicMaterial({color: 0x8090a8})));
    if (withSprings) {
      for (const [samples, colour] of [[free, 0xff8a3d], [limited, 0x4cc3ff]]) {
        const curve = new THREE.CatmullRomCurve3(samples.filter((_, k) => k % 3 === 0).map(toPoint));
        scene.add(new THREE.Mesh(new THREE.TubeGeometry(curve, 360, 0.045, 10, false),
          new THREE.MeshBasicMaterial({color: colour})));
        const end = new THREE.Mesh(new THREE.SphereGeometry(0.09, 24, 12), new THREE.MeshBasicMaterial({color: colour}));
        end.position.copy(toPoint(samples[samples.length - 1]));
        scene.add(end);
      }
    }
    return scene;
  };
  const camera = new THREE.OrthographicCamera(-2.5, 2.5, 2.5, -2.5, 0.1, 20);
  camera.position.set(0, 0, 5);
  camera.lookAt(0, 0, 0);
  return {scene: build(true), camera, baseline: {scene: build(false), camera}};
}
