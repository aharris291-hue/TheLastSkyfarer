extends Node2D
## Small bobbing diamond above things worth inspecting (shape + motion, not
## colour alone, so it reads for colour-blind players).

var t := 0.0


func _process(delta: float) -> void:
	t += delta
	position.y += sin(t * 3.0) * 0.35
	queue_redraw()


func _draw() -> void:
	var s := 12.0 + sin(t * 3.0) * 1.5
	var pts := PackedVector2Array([Vector2(0, -s), Vector2(s * 0.7, 0), Vector2(0, s), Vector2(-s * 0.7, 0)])
	draw_colored_polygon(pts, Color(1.0, 0.86, 0.45, 0.95))
	draw_polyline(pts + PackedVector2Array([pts[0]]), Color(0.25, 0.16, 0.05, 0.9), 2.5)
