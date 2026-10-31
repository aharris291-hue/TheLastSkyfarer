extends RefCounted
## Default input bindings. All gameplay code reads actions through InputMap,
## never raw keys, so everything here can be remapped from the Settings menu.

const REMAPPABLE := [
	["move_left", "Move left"], ["move_right", "Move right"],
	["move_up", "Look up / climb"], ["move_down", "Look down / drop"],
	["jump", "Jump"], ["glide", "Glide (hold in air)"], ["run", "Run (hold)"],
	["interact", "Interact / talk"], ["journal", "Journal"], ["map", "Map"],
	["pause", "Pause"],
]

const PAD_NAMES := {
	JOY_BUTTON_A: "A", JOY_BUTTON_B: "B", JOY_BUTTON_X: "X", JOY_BUTTON_Y: "Y",
	JOY_BUTTON_BACK: "View", JOY_BUTTON_START: "Menu",
	JOY_BUTTON_LEFT_SHOULDER: "LB", JOY_BUTTON_RIGHT_SHOULDER: "RB",
	JOY_BUTTON_LEFT_STICK: "L3", JOY_BUTTON_RIGHT_STICK: "R3",
	JOY_BUTTON_DPAD_UP: "D-pad Up", JOY_BUTTON_DPAD_DOWN: "D-pad Down",
	JOY_BUTTON_DPAD_LEFT: "D-pad Left", JOY_BUTTON_DPAD_RIGHT: "D-pad Right",
}


static func _key(code: Key) -> InputEventKey:
	var e := InputEventKey.new()
	e.physical_keycode = code
	return e


static func _pad(button: JoyButton) -> InputEventJoypadButton:
	var e := InputEventJoypadButton.new()
	e.button_index = button
	return e


static func _axis(axis: JoyAxis, dir: float) -> InputEventJoypadMotion:
	var e := InputEventJoypadMotion.new()
	e.axis = axis
	e.axis_value = dir
	return e


static func defaults() -> Dictionary:
	return {
		"move_left": [_key(KEY_A), _key(KEY_LEFT), _pad(JOY_BUTTON_DPAD_LEFT), _axis(JOY_AXIS_LEFT_X, -1.0)],
		"move_right": [_key(KEY_D), _key(KEY_RIGHT), _pad(JOY_BUTTON_DPAD_RIGHT), _axis(JOY_AXIS_LEFT_X, 1.0)],
		"move_up": [_key(KEY_W), _key(KEY_UP), _pad(JOY_BUTTON_DPAD_UP), _axis(JOY_AXIS_LEFT_Y, -1.0)],
		"move_down": [_key(KEY_S), _key(KEY_DOWN), _pad(JOY_BUTTON_DPAD_DOWN), _axis(JOY_AXIS_LEFT_Y, 1.0)],
		"jump": [_key(KEY_SPACE), _pad(JOY_BUTTON_A)],
		"glide": [_key(KEY_SPACE), _pad(JOY_BUTTON_A)],
		"run": [_key(KEY_SHIFT), _pad(JOY_BUTTON_B)],
		"interact": [_key(KEY_E), _key(KEY_ENTER), _pad(JOY_BUTTON_X)],
		"journal": [_key(KEY_J), _key(KEY_TAB), _pad(JOY_BUTTON_Y)],
		"map": [_key(KEY_M), _pad(JOY_BUTTON_BACK)],
		"pause": [_key(KEY_ESCAPE), _key(KEY_P), _pad(JOY_BUTTON_START)],
		"tab_prev": [_key(KEY_Q), _pad(JOY_BUTTON_LEFT_SHOULDER)],
		"tab_next": [_key(KEY_R), _pad(JOY_BUTTON_RIGHT_SHOULDER)],
		"advance": [_key(KEY_SPACE), _key(KEY_E), _key(KEY_ENTER), _pad(JOY_BUTTON_A), _pad(JOY_BUTTON_X)],
		# Reserved for the combat milestone (not used in the Windrest demo).
		"attack": [_key(KEY_K), _pad(JOY_BUTTON_RIGHT_SHOULDER)],
		"dodge": [_key(KEY_L), _pad(JOY_BUTTON_LEFT_SHOULDER)],
	}


static func apply_defaults() -> void:
	var d := defaults()
	for action in d.keys():
		var typed: Array[InputEvent] = []
		for e in d[action]:
			typed.append(e)
		set_action_events(action, typed)
	# Make sure menus work on a controller even if project defaults change.
	for pair in [["ui_accept", JOY_BUTTON_A], ["ui_cancel", JOY_BUTTON_B]]:
		var ev := _pad(pair[1])
		if not InputMap.action_has_event(pair[0], ev):
			InputMap.action_add_event(pair[0], ev)


static func set_action_events(action: String, events: Array) -> void:
	if not InputMap.has_action(action):
		InputMap.add_action(action, 0.35)
	InputMap.action_erase_events(action)
	for e in events:
		InputMap.action_add_event(action, e)


static func serialize_events(events: Array) -> Array:
	var out := []
	for e in events:
		if e is InputEventKey:
			out.append({"t": "key", "code": int(e.physical_keycode if e.physical_keycode else e.keycode)})
		elif e is InputEventJoypadButton:
			out.append({"t": "pad", "button": int(e.button_index)})
		elif e is InputEventJoypadMotion:
			out.append({"t": "axis", "axis": int(e.axis), "dir": float(signf(e.axis_value))})
		elif e is InputEventMouseButton:
			out.append({"t": "mouse", "button": int(e.button_index)})
	return out


static func deserialize_events(data: Array) -> Array[InputEvent]:
	var out: Array[InputEvent] = []
	for d in data:
		if not d is Dictionary:
			continue
		match d.get("t", ""):
			"key":
				out.append(_key(int(d["code"])))
			"pad":
				out.append(_pad(int(d["button"])))
			"axis":
				out.append(_axis(int(d["axis"]), float(d["dir"])))
			"mouse":
				var m := InputEventMouseButton.new()
				m.button_index = int(d["button"])
				out.append(m)
	return out


static func event_label(e: InputEvent) -> String:
	if e is InputEventKey:
		var code: int = e.physical_keycode if e.physical_keycode else e.keycode
		return OS.get_keycode_string(code)
	if e is InputEventJoypadButton:
		return PAD_NAMES.get(e.button_index, "Button %d" % e.button_index)
	if e is InputEventJoypadMotion:
		var names := {JOY_AXIS_LEFT_X: "Left stick", JOY_AXIS_LEFT_Y: "Left stick",
			JOY_AXIS_TRIGGER_LEFT: "LT", JOY_AXIS_TRIGGER_RIGHT: "RT"}
		return names.get(e.axis, "Axis %d" % e.axis)
	if e is InputEventMouseButton:
		return "Mouse %d" % e.button_index
	return "?"


static func action_label(action: String, device: String) -> String:
	if not InputMap.has_action(action):
		return "?"
	for e in InputMap.action_get_events(action):
		var is_pad := e is InputEventJoypadButton or e is InputEventJoypadMotion
		if (device == "gamepad") == is_pad:
			return event_label(e)
	return "—"
