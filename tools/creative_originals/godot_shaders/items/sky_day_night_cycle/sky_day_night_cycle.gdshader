shader_type sky;

uniform vec4 day_zenith : source_color = vec4(0.16, 0.38, 0.82, 1.0);
uniform vec4 day_horizon : source_color = vec4(0.62, 0.78, 0.95, 1.0);
uniform vec4 sunset_glow : source_color = vec4(1.0, 0.48, 0.2, 1.0);
uniform vec4 night_zenith : source_color = vec4(0.01, 0.015, 0.05, 1.0);
uniform vec4 night_horizon : source_color = vec4(0.05, 0.07, 0.16, 1.0);
uniform vec4 ground_color : source_color = vec4(0.16, 0.15, 0.14, 1.0);
uniform float horizon_falloff : hint_range(0.5, 10.0) = 3.0;
uniform float sun_size : hint_range(0.001, 0.2) = 0.03;
uniform float halo_strength : hint_range(0.0, 4.0) = 0.8;
uniform float star_density : hint_range(0.0, 1.0) = 0.35;
uniform float star_brightness : hint_range(0.0, 4.0) = 1.4;

float hash31(vec3 p) {
	p = fract(p * vec3(0.1031, 0.1030, 0.0973));
	p += dot(p, p.yxz + 33.33);
	return fract((p.x + p.y) * p.z);
}

float stars(vec3 direction) {
	vec3 cell = floor(direction * 150.0);
	float chance = hash31(cell);
	if (chance > star_density * 0.06) {
		return 0.0;
	}
	vec3 center = (cell + 0.5 + (vec3(hash31(cell + 7.1), hash31(cell + 3.7), hash31(cell + 1.3)) - 0.5) * 0.6) / 150.0;
	float distance_to_star = length(direction - normalize(center)) * 150.0;
	float twinkle = 0.7 + 0.3 * sin(TIME * 3.0 + chance * 400.0);
	return smoothstep(0.35, 0.0, distance_to_star) * twinkle;
}

void sky() {
	vec3 direction = normalize(EYEDIR);
	vec3 sun_direction = LIGHT0_ENABLED ? normalize(LIGHT0_DIRECTION) : normalize(vec3(0.0, 0.2, -1.0));
	float elevation = sun_direction.y;
	float day = smoothstep(-0.18, 0.3, elevation);
	float dusk = 1.0 - smoothstep(0.0, 0.32, abs(elevation - 0.03));
	float facing = 0.5;
	if (length(direction.xz) > 1e-4 && length(sun_direction.xz) > 1e-4) {
		facing = dot(normalize(direction.xz), normalize(sun_direction.xz)) * 0.5 + 0.5;
	}
	float up = clamp(direction.y, 0.0, 1.0);
	float toward_horizon = pow(1.0 - up, horizon_falloff);
	vec3 zenith = mix(night_zenith.rgb, day_zenith.rgb, day);
	vec3 horizon = mix(night_horizon.rgb, day_horizon.rgb, day);
	horizon = mix(horizon, sunset_glow.rgb, dusk * facing * facing);
	vec3 color = mix(zenith, horizon, toward_horizon);
	if (direction.y < 0.0) {
		vec3 ground = ground_color.rgb * mix(0.15, 1.0, day);
		color = mix(horizon * 0.7, ground, smoothstep(0.0, 0.06, -direction.y));
	}
	float cosine = dot(direction, sun_direction);
	float angle = acos(clamp(cosine, -1.0, 1.0));
	vec3 light_color = LIGHT0_ENABLED ? LIGHT0_COLOR * LIGHT0_ENERGY : vec3(1.0);
	float disc = 1.0 - smoothstep(sun_size * 0.8, sun_size, angle);
	float halo = pow(max(cosine, 0.0), 48.0) * halo_strength;
	vec3 halo_color = mix(light_color, sunset_glow.rgb, dusk);
	color += (disc * light_color + halo * halo_color) * step(-0.02, direction.y);
	color += vec3(stars(direction)) * star_brightness * (1.0 - day) * smoothstep(-0.02, 0.1, direction.y);
	COLOR = color;
}
