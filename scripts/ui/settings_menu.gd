extends MenuBase
## Settings: audio, display, accessibility and control remapping.
## Fully navigable with keyboard or controller.

const InputConfig := preload("res://scripts/systems/input_config.gd")

var _capture_action := ""
var _capture_button: Button
var _controls_box: VBoxContainer


func _ready() -> void:
	make_backdrop(0.7)
	var margin := MarginContainer.new()
	margin.set_anchors_preset(Control.PRESET_FULL_RECT)
	for side in ["left", "right"]:
		margin.add_theme_constant_override("margin_" + side, 300)
	for side in ["top", "bottom"]:
		margin.add_theme_constant_override("margin_" + side, 60)
	add_child(margin)
	var outer := PanelContainer.new()
	margin.add_child(outer)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 12)
	outer.add_child(v)
	v.add_child(make_title("Settings", 48))
	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	scroll.follow_focus = true
	v.add_child(scroll)
	var list := VBoxContainer.new()
	list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	list.add_theme_constant_override("separation", 10)
	scroll.add_child(list)

	_section(list, "Audio")
	_slider(list, "Master volume", "master_volume", 0.0, 1.0)
	_slider(list, "Music volume", "music_volume", 0.0, 1.0)
	_slider(list, "Sound effects volume", "sfx_volume", 0.0, 1.0)
	_slider(list, "Ambience volume", "ambience_volume", 0.0, 1.0)
	_section(list, "Display")
	_toggle(list, "Fullscreen", "fullscreen")
	_toggle(list, "V-Sync", "vsync")
	_section(list, "Accessibility")
	_slider(list, "Text size", "text_scale", 1.0, 1.5, 0.05)
	_choice(list, "Text speed", "text_speed", [["Instant", 0.0], ["Normal", 1.0], ["Fast", 2.0]])
	_choice(list, "Glide control", "glide_hold", [["Hold button", true], ["Press to toggle", false]])
	_toggle(list, "Screen shake", "screen_shake")
	_section(list, "Controls  (select an action, then press the new key or button)")
	_controls_box = VBoxContainer.new()
	list.add_child(_controls_box)
	_build_controls()
	add_button(list, "Reset controls to default", func():
		Settings.reset_controls()
		_build_controls())
	add_button(v, "Back", close)
	focus_first(list)


func _section(parent: Control, text: String) -> void:
	var l := make_label(text, 30, Color(0.98, 0.82, 0.5))
	parent.add_child(l)


func _row(parent: Control, text: String) -> HBoxContainer:
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 20)
	var l := make_label(text, 28)
	l.custom_minimum_size = Vector2(440, 0)
	h.add_child(l)
	parent.add_child(h)
	return h


func _slider(parent: Control, text: String, key: String, lo: float, hi: float, step := 0.05) -> void:
	var h := _row(parent, text)
	var s := HSlider.new()
	s.min_value = lo
	s.max_value = hi
	s.step = step
	s.value = Settings.get(key)
	s.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	s.custom_minimum_size = Vector2(0, 40)
	var val := make_label("%d%%" % int(round(s.value * 100)), 26)
	val.custom_minimum_size = Vector2(90, 0)
	s.value_changed.connect(func(x):
		Settings.set(key, x)
		Settings.apply()
		Settings.save_settings()
		val.text = "%d%%" % int(round(x * 100))
		if key == "sfx_volume":
			AudioManager.play_sfx("ui_move"))
	h.add_child(s)
	h.add_child(val)


func _toggle(parent: Control, text: String, key: String) -> void:
	var h := _row(parent, text)
	var c := CheckButton.new()
	c.button_pressed = Settings.get(key)
	c.text = "On" if c.button_pressed else "Off"
	c.toggled.connect(func(on):
		Settings.set(key, on)
		c.text = "On" if on else "Off"
		Settings.apply()
		Settings.save_settings()
		AudioManager.play_sfx("ui_confirm"))
	h.add_child(c)


func _choice(parent: Control, text: String, key: String, options: Array) -> void:
	var h := _row(parent, text)
	var o := OptionButton.new()
	o.add_theme_font_size_override("font_size", 28)
	var current = Settings.get(key)
	for i in options.size():
		o.add_item(options[i][0], i)
		if options[i][1] == current:
			o.select(i)
	o.item_selected.connect(func(i):
		Settings.set(key, options[i][1])
		Settings.apply()
		Settings.save_settings())
	h.add_child(o)


func _build_controls() -> void:
	for c in _controls_box.get_children():
		c.queue_free()
	for pair in InputConfig.REMAPPABLE:
		var action: String = pair[0]
		var h := _row(_controls_box, pair[1])
		var kb := Button.new()
		kb.text = InputConfig.action_label(action, "keyboard")
		kb.custom_minimum_size = Vector2(220, 56)
		kb.pressed.connect(func(): _start_capture(action, kb, "keyboard"))
		h.add_child(kb)
		var pad := Button.new()
		pad.text = InputConfig.action_label(action, "gamepad")
		pad.custom_minimum_size = Vector2(220, 56)
		pad.pressed.connect(func(): _start_capture(action, pad, "gamepad"))
		h.add_child(pad)


var _capture_device := ""


func _start_capture(action: String, button: Button, device: String) -> void:
	_capture_action = action
	_capture_button = button
	_capture_device = device
	button.text = "Press a key..." if device == "keyboard" else "Press a button..."


func _input(event: InputEvent) -> void:
	if _capture_action == "":
		return
	var accept := false
	if _capture_device == "keyboard" and event is InputEventKey and event.pressed and not event.echo:
		accept = true
		if event.physical_keycode == KEY_ESCAPE:
			_cancel_capture()
			get_viewport().set_input_as_handled()
			return
	elif _capture_device == "gamepad" and event is InputEventJoypadButton and event.pressed:
		accept = true
	if not accept:
		return
	get_viewport().set_input_as_handled()
	var e: InputEvent
	if event is InputEventKey:
		var k := InputEventKey.new()
		k.physical_keycode = event.physical_keycode if event.physical_keycode else event.keycode
		e = k
	else:
		var j := InputEventJoypadButton.new()
		j.button_index = event.button_index
		e = j
	Settings.remap(_capture_action, e)
	_capture_action = ""
	AudioManager.play_sfx("ui_confirm")
	_build_controls()
	focus_first(_controls_box)


func _cancel_capture() -> void:
	_capture_action = ""
	_build_controls()


func on_back() -> void:
	if _capture_action != "":
		_cancel_capture()
		return
	close()


func handles_pause() -> bool:
	return _capture_action == ""
