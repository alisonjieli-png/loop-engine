shader_type spatial;

uniform vec4 brick_color : source_color = vec4(0.62, 0.26, 0.18, 1.0);
uniform vec4 mortar_color : source_color = vec4(0.72, 0.7, 0.66, 1.0);
uniform float bricks_across : hint_range(1.0, 20.0) = 4.0;
uniform float bricks_down : hint_range(1.0, 40.0) = 8.0;
uniform float mortar_width : hint_range(0.0, 0.2) = 0.06;
uniform float bevel : hint_range(0.0, 0.3) = 0.08;
uniform float depth_scale : hint_range(0.0, 0.2) = 0.05;
uniform int steps : hint_range(4, 64) = 24;
uniform float color_variation : hint_range(0.0, 1.0) = 0.35;

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

vec3 brick_cell(vec2 uv) {
	vec2 grid = uv * vec2(bricks_across, bricks_down);
	float row = floor(grid.y);
	grid.x += mod(row, 2.0) * 0.5;
	return vec3(fract(grid), hash21(floor(grid) + vec2(3.0, 7.0)));
}

float brick_height(vec2 uv) {
	vec2 local = brick_cell(uv).xy;
	vec2 edge = min(local, 1.0 - local) * vec2(1.0, bricks_across / bricks_down * 2.0);
	float distance_to_edge = min(edge.x, edge.y);
	return smoothstep(mortar_width * 0.5, mortar_width * 0.5 + bevel, distance_to_edge);
}

void fragment() {
	vec3 view_tangent = normalize(vec3(dot(VIEW, TANGENT), dot(VIEW, -BINORMAL), dot(VIEW, NORMAL)));
	vec2 shift = view_tangent.xy / max(view_tangent.z, 0.15) * depth_scale;
	float layer = 1.0 / float(steps);
	vec2 uv = UV;
	float ray_depth = 0.0;
	float surface_depth = 1.0 - brick_height(uv);
	vec2 previous_uv = uv;
	float previous_gap = surface_depth;
	for (int i = 0; i < steps; i++) {
		if (ray_depth >= surface_depth) {
			break;
		}
		previous_uv = uv;
		previous_gap = surface_depth - ray_depth;
		uv -= shift * layer;
		ray_depth += layer;
		surface_depth = 1.0 - brick_height(uv);
	}
	float after = ray_depth - surface_depth;
	float weight = previous_gap / max(previous_gap + after, 1e-4);
	uv = mix(previous_uv, uv, weight);
	float h = brick_height(uv);
	vec2 texel = vec2(0.002);
	float hx = brick_height(uv + vec2(texel.x, 0.0)) - h;
	float hy = brick_height(uv + vec2(0.0, texel.y)) - h;
	NORMAL_MAP = normalize(vec3(-hx * 20.0, hy * 20.0, 1.0)) * 0.5 + 0.5;
	vec3 cell = brick_cell(uv);
	vec3 brick = brick_color.rgb * mix(1.0 - color_variation * 0.5, 1.0 + color_variation * 0.3, cell.z);
	ALBEDO = mix(mortar_color.rgb, brick, smoothstep(0.05, 0.4, h));
	ROUGHNESS = 0.85;
}
