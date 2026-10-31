extends CanvasLayer
## Scene transitions with a fade (autoload "Router").

signal scene_changed(path: String)

var _fade: ColorRect
var busy := false
## Spawn marker requested by the last transition (consumed by the level).
var pending_spawn := ""
var use_saved_position := false


func _ready() -> void:
	layer = 100
	process_mode = Node.PROCESS_MODE_ALWAYS
	_fade = ColorRect.new()
	_fade.color = Color(0.03, 0.03, 0.06, 1)
	_fade.set_anchors_preset(Control.PRESET_FULL_RECT)
	_fade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_fade.modulate.a = 0.0
	add_child(_fade)


func go(path: String, spawn := "", from_save := false, fade_time := 0.6) -> void:
	if busy:
		return
	busy = true
	pending_spawn = spawn
	use_saved_position = from_save
	var tw := create_tween()
	tw.tween_property(_fade, "modulate:a", 1.0, fade_time)
	await tw.finished
	get_tree().paused = false
	get_tree().change_scene_to_file(path)
	await get_tree().process_frame
	await get_tree().process_frame
	scene_changed.emit(path)
	var tw2 := create_tween()
	tw2.tween_property(_fade, "modulate:a", 0.0, fade_time)
	await tw2.finished
	busy = false


## Fade to black, run a callback (e.g. a time skip), then fade back in.
func fade_through(callback: Callable, hold := 0.8, caption := "") -> void:
	var tw := create_tween()
	tw.tween_property(_fade, "modulate:a", 1.0, 0.8)
	await tw.finished
	var label: Label
	if caption != "":
		label = Label.new()
		label.text = caption
		label.add_theme_font_size_override("font_size", 44)
		label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		label.set_anchors_preset(Control.PRESET_FULL_RECT)
		add_child(label)
	if callback.is_valid():
		callback.call()
	await get_tree().create_timer(hold, true).timeout
	if label:
		label.queue_free()
	var tw2 := create_tween()
	tw2.tween_property(_fade, "modulate:a", 0.0, 0.8)
	await tw2.finished
