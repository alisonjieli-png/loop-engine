// Game rules have no renderer, clock, model call or network dependency.
export const RULES = Object.freeze({radius: 16, speed: 5.2, sprintSpeed: 8.1,
  heroRadius: 0.45, enemyRadius: 0.48, attackDuration: 0.48,
  attackReach: 2.55, attackDamage: 34, enemyDamage: 12, maxHealth: 100});

export function createState() {
  return {version: 'fantasy_arena_state/v1', time: 0, phase: 'playing', wave: 1,
    defeated: 0, health: RULES.maxHealth, stamina: 100, nextWaveAt: null,
    hero: {x: 0, z: 6, yaw: Math.PI, moving: false, attack: 0, attackHit: false,
      dodge: 0, invulnerable: 0}, enemies: [], obstacles: [], events: [], seed: 19};
}

export function spawnWave(state) {
  const count = 2 + state.wave;
  state.enemies = Array.from({length: count}, (_, i) => {
    const angle = i / count * Math.PI * 2 + state.wave * .71;
    return {id: `wave-${state.wave}-${i}`, x: Math.cos(angle) * 11,
      z: Math.sin(angle) * 11 - 1, yaw: 0, health: 68, attack: 0,
      cooldown: .8 + i * .25, stagger: 0, moving: false, dead: false};
  });
  state.nextWaveAt = null;
}

function confine(actor, radius, obstacles) {
  const distance = Math.hypot(actor.x, actor.z);
  if (distance > RULES.radius - radius) {
    actor.x *= (RULES.radius - radius) / distance;
    actor.z *= (RULES.radius - radius) / distance;
  }
  for (const item of obstacles) {
    const dx = actor.x - item.x, dz = actor.z - item.z;
    const d = Math.hypot(dx, dz), min = radius + item.radius;
    if (d < min) {
      actor.x = item.x + (d > .0001 ? dx / d : 1) * min;
      actor.z = item.z + (d > .0001 ? dz / d : 0) * min;
    }
  }
}

export function advance(state, input, dt) {
  if (!Number.isFinite(dt) || dt < 0 || dt > .05) throw new Error('Expected a fixed step between 0 and 0.05 seconds.');
  state.events = [];
  if (state.phase !== 'playing') return;
  state.time += dt;
  const hero = state.hero;
  hero.invulnerable = Math.max(0, hero.invulnerable - dt);
  hero.dodge = Math.max(0, hero.dodge - dt);
  const dx = Math.max(-1, Math.min(1, Number(input.x) || 0));
  const dz = Math.max(-1, Math.min(1, Number(input.z) || 0));
  const length = Math.hypot(dx, dz);
  hero.moving = length > .05;
  const sprint = input.sprint && state.stamina > 1 && hero.moving;
  state.stamina = Math.max(0, Math.min(100, state.stamina + (sprint ? -24 : 17) * dt));
  if (input.dodge && state.stamina >= 25 && hero.dodge === 0) {
    hero.dodge = .35; hero.invulnerable = .4; state.stamina -= 25;
    state.events.push({type: 'dodge'});
  }
  if (hero.moving) {
    const speed = hero.dodge > 0 ? 13 : sprint ? RULES.sprintSpeed : RULES.speed;
    hero.x += dx / Math.max(1, length) * speed * dt;
    hero.z += dz / Math.max(1, length) * speed * dt;
    if (hero.attack === 0) hero.yaw = Math.atan2(dx, dz);
  }
  confine(hero, RULES.heroRadius, state.obstacles);
  if (input.attack && hero.attack === 0 && state.stamina >= 8) {
    hero.attack = RULES.attackDuration; hero.attackHit = false; state.stamina -= 8;
    state.events.push({type: 'swing'});
  }
  if (hero.attack > 0) {
    hero.attack = Math.max(0, hero.attack - dt);
    if (!hero.attackHit && hero.attack < RULES.attackDuration * .55) {
      hero.attackHit = true;
      for (const enemy of state.enemies) {
        const x = enemy.x - hero.x, z = enemy.z - hero.z, distance = Math.hypot(x, z);
        const facing = (x * Math.sin(hero.yaw) + z * Math.cos(hero.yaw)) / Math.max(.001, distance);
        if (!enemy.dead && distance < RULES.attackReach && facing > -.15) {
          enemy.health = Math.max(0, enemy.health - RULES.attackDamage);
          enemy.stagger = .42;
          if (distance > .001) { enemy.x += x / distance * .6; enemy.z += z / distance * .6; }
          confine(enemy, RULES.enemyRadius, state.obstacles);
          state.events.push({type: 'hit', id: enemy.id, x: enemy.x, z: enemy.z});
          if (enemy.health === 0) {
            enemy.dead = true; state.defeated++;
            state.events.push({type: 'defeat', id: enemy.id, x: enemy.x, z: enemy.z});
          }
        }
      }
    }
  }
  for (const enemy of state.enemies) {
    enemy.moving = false;
    if (enemy.dead) continue;
    enemy.stagger = Math.max(0, enemy.stagger - dt);
    enemy.cooldown = Math.max(0, enemy.cooldown - dt);
    const x = hero.x - enemy.x, z = hero.z - enemy.z, distance = Math.hypot(x, z);
    enemy.yaw = Math.atan2(x, z);
    if (enemy.stagger > 0) continue;
    if (enemy.attack > 0) {
      const before = enemy.attack;
      enemy.attack = Math.max(0, enemy.attack - dt);
      if (before > .15 && enemy.attack <= .15 && distance < 1.8 && hero.invulnerable === 0) {
        state.health = Math.max(0, state.health - RULES.enemyDamage);
        hero.invulnerable = .65;
        state.events.push({type: 'hurt'});
      }
    } else if (distance < 1.55 && enemy.cooldown === 0) {
      enemy.attack = .65; enemy.cooldown = 1.6;
    } else if (distance > 1.3) {
      const speed = 1.65 + Math.min(state.wave, 3) * .16;
      enemy.x += x / distance * speed * dt; enemy.z += z / distance * speed * dt;
      enemy.moving = true;
    }
    confine(enemy, RULES.enemyRadius, state.obstacles);
  }
  if (state.health === 0) state.phase = 'defeated';
  if (state.enemies.length && state.enemies.every(enemy => enemy.dead)) {
    if (state.wave === 3) {
      state.phase = 'victory';
    } else if (state.nextWaveAt === null) {
      state.nextWaveAt = state.time + 3;
      state.health = Math.min(RULES.maxHealth, state.health + 20);
    } else if (state.time >= state.nextWaveAt) {
      state.wave++; spawnWave(state); state.events.push({type: 'wave'});
    }
  }
}
