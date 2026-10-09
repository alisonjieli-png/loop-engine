shader_type spatial;
render_mode unshaded, cull_disabled, depth_draw_never, shadows_disabled;

uniform sampler2D screen_texture : hint_screen_texture, filter_linear_mipmap;
uniform float drop_density : hint_range(2.0, 40.0) = 12.0;
uniform float drop_size : hint_range(0.05, 0.5) = 0.28;
uniform float runner_columns : hint_range(1.0, 30.0) = 7.0;
uniform float runner_speed : hint_range(0.0, 2.0) = 0.35;
uniform float refraction : hint_range(0.0, 0.2) = 0.06;
uniform float mist_blur : hint_range(0.0, 6.0) = 3.0;
uniform vec4 mist_tint : source_color = vec4(0.82, 0.87, 0.92, 1.0);
uniform float mist_amount : hint_range(0.0, 1.0) = 0.25;

// MurmurHash3 32-bit finalizer used as an integer hash.
uint fmix32(uint h) {
	h ^= h >> 16u;
	h *= 0x85ebca6bu;
	h ^= h >> 13u;
	h *= 0xc2b2ae35u;
	h ^= h >> 16u;
	return h;
}

uint lattice2(vec2 p) {
	ivec2 c = ivec2(floor(p));
	return fmix32(uint(c.x) * 73856093u ^ uint(c.y) * 19349663u);
}

float hash21(vec2 p) {
	return float(lattice2(p)) / 4294967295.0;
}

vec2 hash22(vec2 p) {
	uint h = lattice2(p);
	return vec2(float(h & 0xffffu), float(h >> 16u)) / 65535.0;
}

vec3 static_drop(vec2 uv) {
	vec2 grid = uv * drop_density;
	vec2 cell = floor(grid);
	vec2 offset = hash22(cell);
	float size = drop_size * mix(0.3, 1.0, hash21(cell + 5.0)) * step(0.35, hash21(cell + 9.0));
	vec2 delta = (fract(grid) - offset * 0.6 - 0.2) / max(size, 1e-3);
	float r2 = dot(delta, delta);
	float inside = 1.0 - smoothstep(0.85, 1.0, r2);
	return vec3(delta * inside, inside);
}

vec3 running_drop(vec2 uv) {
	float column = floor(uv.x * runner_columns);
	float speed = runner_speed * mix(0.6, 1.4, hash21(vec2(column, 1.0)));
	float head = fract(hash21(vec2(column, 2.0)) + TIME * speed);
	float x = fract(uv.x * runner_columns) - 0.5 - (hash21(vec2(column, 3.0)) - 0.5) * 0.4;
	float y = uv.y - head;
	vec2 delta = vec2(x / 0.22, y / 0.03);
	float inside = 1.0 - smoothstep(0.7, 1.0, dot(delta, delta));
	float trail = (1.0 - smoothstep(0.03, 0.06, abs(x))) * step(y, 0.0) * smoothstep(-0.25, 0.0, y) * 0.5;
	return vec3(delta * 0.5 * inside, max(inside, trail));
}

void fragment() {
	vec2 uv = vec2(UV.x, UV.y);
	vec3 a = static_drop(uv);
	vec3 b = running_drop(uv);
	float wet = max(a.z, b.z);
	vec2 bend = (a.xy * a.z + b.xy * b.z) * refraction;
	vec3 sharp = textureLod(screen_texture, SCREEN_UV - bend, 0.0).rgb;
	vec3 misted = mix(textureLod(screen_texture, SCREEN_UV, mist_blur).rgb, mist_tint.rgb, mist_amount);
	float edge = smoothstep(0.55, 1.0, length(a.xy)) * a.z;
	vec3 bead = sharp * (1.15 - 0.45 * edge * step(0.0, a.y));
	vec3 color = mix(misted, bead, wet);
	float glint = (1.0 - smoothstep(0.0, 0.28, length(a.xy - vec2(-0.35, -0.4)))) * a.z;
	glint = max(glint, (1.0 - smoothstep(0.0, 0.35, length(b.xy - vec2(-0.2, -0.3)))) * step(0.5, b.z));
	ALBEDO = color + vec3(glint * 0.8);
}
