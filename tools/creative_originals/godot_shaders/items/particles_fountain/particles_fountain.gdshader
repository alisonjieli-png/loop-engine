shader_type particles;

uniform float launch_speed : hint_range(0.0, 20.0) = 5.5;
uniform float spread_degrees : hint_range(0.0, 45.0) = 9.0;
uniform float nozzle_radius : hint_range(0.0, 1.0) = 0.06;
uniform float swirl_speed : hint_range(-4.0, 4.0) = 0.8;
uniform float gravity : hint_range(0.0, 30.0) = 9.8;
uniform float floor_height : hint_range(-5.0, 5.0) = 0.0;
uniform float bounce : hint_range(0.0, 1.0) = 0.3;
uniform float droplet_scale : hint_range(0.1, 4.0) = 1.0;
uniform vec4 water_color : source_color = vec4(0.45, 0.75, 1.0, 1.0);
uniform vec4 spray_color : source_color = vec4(0.92, 0.97, 1.0, 1.0);

float hash01(uint value) {
	value ^= value >> 16u;
	value *= 0x7feb352du;
	value ^= value >> 15u;
	value *= 0x846ca68bu;
	value ^= value >> 16u;
	return float(value) / 4294967295.0;
}

void start() {
	uint seed = NUMBER * 747796405u + RANDOM_SEED;
	float angle = hash01(seed) * TAU;
	float radius = sqrt(hash01(seed + 1u)) * nozzle_radius;
	float tilt = radians(spread_degrees) * sqrt(hash01(seed + 2u));
	float heading = hash01(seed + 3u) * TAU;
	vec3 direction = vec3(sin(tilt) * cos(heading), cos(tilt), sin(tilt) * sin(heading));
	float speed = launch_speed * mix(0.82, 1.0, hash01(seed + 4u));
	vec3 offset = vec3(cos(angle) * radius, 0.0, sin(angle) * radius);
	vec3 tangent = normalize(vec3(-sin(angle), 0.0, cos(angle)));
	float size = droplet_scale * mix(0.6, 1.3, hash01(seed + 5u));
	TRANSFORM = EMISSION_TRANSFORM * mat4(vec4(size, 0.0, 0.0, 0.0), vec4(0.0, size, 0.0, 0.0),
										  vec4(0.0, 0.0, size, 0.0), vec4(offset, 1.0));
	VELOCITY = (EMISSION_TRANSFORM * vec4(direction * speed + tangent * swirl_speed, 0.0)).xyz;
	COLOR = water_color;
	CUSTOM = vec4(0.0);
}

void process() {
	CUSTOM.y += DELTA;
	VELOCITY.y -= gravity * DELTA;
	if (TRANSFORM[3].y < floor_height && VELOCITY.y < 0.0) {
		TRANSFORM[3].y = floor_height;
		VELOCITY.y = -VELOCITY.y * bounce;
		VELOCITY.xz *= 0.6;
		CUSTOM.x += 1.0;
	}
	float age = clamp(CUSTOM.y / LIFETIME, 0.0, 1.0);
	float splashed = clamp(CUSTOM.x, 0.0, 1.0);
	vec3 tint = mix(water_color.rgb, spray_color.rgb, max(age, splashed));
	COLOR = vec4(tint, (1.0 - smoothstep(0.75, 1.0, age)) * mix(water_color.a, spray_color.a, splashed));
}
