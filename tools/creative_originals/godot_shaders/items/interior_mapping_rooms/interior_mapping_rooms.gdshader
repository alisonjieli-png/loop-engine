shader_type spatial;

uniform float rooms_across : hint_range(1.0, 20.0) = 4.0;
uniform float rooms_down : hint_range(1.0, 20.0) = 4.0;
uniform float room_depth : hint_range(0.1, 3.0) = 1.0;
uniform vec4 wall_color : source_color = vec4(0.78, 0.72, 0.62, 1.0);
uniform vec4 floor_color : source_color = vec4(0.42, 0.3, 0.2, 1.0);
uniform vec4 ceiling_color : source_color = vec4(0.92, 0.92, 0.9, 1.0);
uniform vec4 frame_color : source_color = vec4(0.16, 0.17, 0.2, 1.0);
uniform float frame_width : hint_range(0.0, 0.3) = 0.08;
uniform float lights_on : hint_range(0.0, 1.0) = 0.6;
uniform float glass_reflection : hint_range(0.0, 1.0) = 0.2;

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

void fragment() {
	vec2 grid = UV * vec2(rooms_across, rooms_down);
	vec2 cell = floor(grid);
	vec2 local = fract(grid);
	vec3 direction = -normalize(vec3(dot(VIEW, TANGENT) * rooms_across, dot(VIEW, -BINORMAL) * rooms_down,
									 dot(VIEW, NORMAL) / room_depth));
	vec3 origin = vec3(local, 0.0);
	vec3 bounds = vec3(direction.x > 0.0 ? 1.0 : 0.0, direction.y > 0.0 ? 1.0 : 0.0, -1.0);
	vec3 distances = (bounds - origin) / direction;
	float t = min(min(distances.x, distances.y), distances.z);
	vec3 hit = origin + direction * t;
	float seed = hash21(cell + vec2(17.0, 3.0));
	vec3 tint = mix(vec3(1.0), vec3(0.6 + seed * 0.6, 0.8, 1.2 - seed * 0.5), 0.35);
	vec3 color;
	if (t == distances.z) {
		float stripes = 0.85 + 0.15 * step(0.5, fract(hit.x * 6.0));
		color = wall_color.rgb * tint * stripes;
	} else if (t == distances.x) {
		color = wall_color.rgb * tint * 0.75;
	} else if (direction.y > 0.0) {
		float planks = 0.8 + 0.2 * step(0.5, fract(hit.x * 5.0));
		color = floor_color.rgb * planks;
	} else {
		float lamp = 1.0 - smoothstep(0.08, 0.14, length(hit.xz - vec2(0.5, -0.5)));
		color = ceiling_color.rgb + vec3(lamp);
	}
	float depth_shade = mix(1.0, 0.55, clamp(-hit.z, 0.0, 1.0));
	float lit = step(seed, lights_on);
	color *= depth_shade * mix(0.25, 1.15, lit);
	float facing = clamp(dot(NORMAL, VIEW), 0.0, 1.0);
	color = mix(color, vec3(0.65, 0.75, 0.85), glass_reflection * (1.0 - facing));
	vec2 frame_distance = min(local, 1.0 - local);
	float frame = 1.0 - step(frame_width, min(frame_distance.x, frame_distance.y));
	ALBEDO = mix(color * 0.2, frame_color.rgb, frame);
	EMISSION = color * (1.0 - frame) * 0.8;
	ROUGHNESS = mix(0.1, 0.8, frame);
}
