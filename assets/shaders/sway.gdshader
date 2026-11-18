shader_type canvas_item;
// Gentle wind sway for trees, bushes and banners. The bottom of the sprite
// stays planted and the top moves, so the quad is sheared rather than moved.
uniform float amp = 5.0;      // top offset in texture pixels
uniform float speed = 1.2;
uniform float phase = 0.0;

void vertex() {
	float w = 1.0 - UV.y;
	float s = sin(TIME * speed + phase) + 0.35 * sin(TIME * speed * 2.3 + phase * 1.7);
	VERTEX.x += s * amp * w;
}
