extends Control
class_name MenuBase
## Shared helpers for code-built menus: dimmed backdrop, centred panel,
## focusable buttons (controller friendly) and "back" handling.

signal closed

var panel: PanelContainer
var box: VBoxContainer
var title_font: Font = preload("res://assets/ui/fonts/LiberationSerif-Bold.ttf")
var dim := true


func _init() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_STOP


func make_backdrop(alpha := 0.6) -> void:
	var bg := ColorRect.new()
	bg.color = Color(0.03, 0.03, 0.06, alpha)
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(bg)


func make_panel(width := 760.0, title := "") -> VBoxContainer:
	var center := CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(center)
	panel = PanelContainer.new()
	panel.custom_minimum_size = Vector2(width, 0)
	center.add_child(panel)
	box = VBoxContainer.new()
	box.add_theme_constant_override("separation", 16)
	panel.add_child(box)
	if title != "":
		box.add_child(make_title(title))
	return box


func make_title(text: String, size := 52) -> Label:
	var l := Label.new()
	l.text = text
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	l.add_theme_font_override("font", title_font)
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", Color(0.98, 0.86, 0.58))
	return l


func make_label(text: String, size := 28, color := Color(0.95, 0.9, 0.82), wrap := false) -> Label:
	var l := Label.new()
	l.text = text
	if wrap:
		l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		l.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	return l


func add_button(parent: Control, text: String, callback: Callable, disabled := false) -> Button:
	var b := Button.new()
	b.text = text
	b.disabled = disabled
	b.custom_minimum_size = Vector2(0, 64)
	b.pressed.connect(func():
		AudioManager.play_sfx("ui_confirm")
		callback.call())
	b.focus_entered.connect(func(): AudioManager.play_sfx("ui_move", 0.0, -6.0))
	parent.add_child(b)
	return b


func focus_first(parent: Node = null) -> void:
	await get_tree().process_frame
	var root := parent if parent else self
	for c in _all_children(root):
		if c is Control and c.focus_mode != Control.FOCUS_NONE and c.is_visible_in_tree() and not (c is Button and c.disabled):
			c.grab_focus()
			return


func _all_children(n: Node) -> Array:
	var out := []
	for c in n.get_children():
		out.append(c)
		out.append_array(_all_children(c))
	return out


func close() -> void:
	AudioManager.play_sfx("ui_back")
	closed.emit()
	queue_free()


func _unhandled_input(event: InputEvent) -> void:
	if not is_visible_in_tree():
		return
	if event.is_action_pressed("ui_cancel") or (event.is_action_pressed("pause") and handles_pause()):
		get_viewport().set_input_as_handled()
		on_back()


func handles_pause() -> bool:
	return true


func on_back() -> void:
	close()
