shader_type canvas_item;
// Painted sky with drifting clouds and a sea of clouds below the horizon.
// Colours are driven by the time-of-day controller (scripts/world/sky.gd).

uniform vec4 sky_top : source_color = vec4(0.35, 0.55, 0.85, 1.0);
uniform vec4 sky_mid : source_color = vec4(0.62, 0.78, 0.95, 1.0);
uniform vec4 horizon_col : source_color = vec4(0.98, 0.88, 0.75, 1.0);
uniform vec4 sun_col : source_color = vec4(1.0, 0.9, 0.7, 1.0);
uniform vec4 cloud_light : source_color = vec4(1.0, 0.98, 0.95, 1.0);
uniform vec4 cloud_shade : source_color = vec4(0.72, 0.76, 0.88, 1.0);
uniform vec2 sun_pos = vec2(0.75, 0.32);
uniform float horizon = 0.62;
uniform vec2 cam = vec2(0.0);
uniform float aspect = 1.7778;
uniform float stars = 0.0;
uniform float fog = 0.0;

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float noise(vec2 p) {
	vec2 i = floor(p); vec2 f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash(i), hash(i + vec2(1, 0)), u.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), u.x), u.y);
}
float fbm(vec2 p) {
	float v = 0.0; float a = 0.5;
	for (int i = 0; i < 5; i++) { v += a * noise(p); p *= 2.03; a *= 0.5; }
	return v;
}

void fragment() {
	vec2 uv = UV;
	float t = TIME;
	// Base gradient
	vec3 col = mix(sky_top.rgb, sky_mid.rgb, smoothstep(0.0, horizon * 0.8, uv.y));
	col = mix(col, horizon_col.rgb, smoothstep(horizon * 0.55, horizon, uv.y));
	// Stars (night only)
	if (stars > 0.0) {
		vec2 sp = uv * vec2(aspect, 1.0) * 140.0 + cam * 0.0004;
		float s = step(0.996, hash(floor(sp))) * smoothstep(horizon, 0.0, uv.y);
		col += vec3(s) * stars * (0.6 + 0.4 * sin(t * 2.0 + hash(floor(sp)) * 20.0));
	}
	// Sun glow
	vec2 d = (uv - sun_pos) * vec2(aspect, 1.0);
	float sd = length(d);
	col += sun_col.rgb * (0.55 * exp(-sd * 9.0) + 0.25 * exp(-sd * 2.5));
	col = mix(col, sun_col.rgb * 1.05 + 0.1, smoothstep(0.045, 0.035, sd));
	// High drifting clouds (parallax with camera)
	vec2 cp = vec2(uv.x * aspect, uv.y) * 2.2 + vec2(cam.x * 0.00008 + t * 0.006, cam.y * 0.00004);
	float c = fbm(cp * vec2(1.0, 2.6));
	float cmask = smoothstep(0.52, 0.75, c) * smoothstep(horizon, horizon * 0.25, uv.y);
	vec3 ccol = mix(cloud_shade.rgb, cloud_light.rgb, smoothstep(0.5, 0.85, fbm(cp * 1.7 + 3.0)));
	col = mix(col, ccol, cmask * 0.85);
	// Sea of clouds below the horizon: puffy rows that get bigger toward the viewer
	if (uv.y > horizon - 0.06) {
		float depth = clamp((uv.y - horizon + 0.06) / (1.0 - horizon + 0.06), 0.0, 1.0);
		float rows = 3.0 + (1.0 - depth) * 18.0;
		vec2 sp2 = vec2(uv.x * aspect * (1.6 - depth) * 3.0 + cam.x * 0.00025 * (0.4 + depth) + t * 0.01, depth * rows);
		float puff = fbm(sp2 + vec2(0.0, t * 0.02));
		float top_edge = horizon - 0.035 + (puff - 0.5) * 0.07;
		float sea = smoothstep(top_edge, top_edge + 0.02, uv.y);
		vec3 seacol = mix(cloud_light.rgb, cloud_shade.rgb, smoothstep(0.35, 0.8, puff) * 0.7 + depth * 0.2);
		seacol = mix(seacol, horizon_col.rgb, (1.0 - depth) * 0.35);
		seacol += sun_col.rgb * 0.18 * exp(-abs(uv.x - sun_pos.x) * 4.0) * (1.0 - depth);
		col = mix(col, seacol, sea);
	}
	col = mix(col, cloud_light.rgb * 0.95, fog);
	COLOR = vec4(col, 1.0);
}
