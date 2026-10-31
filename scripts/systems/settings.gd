extends Node
## Player settings and input bindings (autoload "Settings").
##
## Owns the InputMap: default bindings are defined in InputConfig and any
## player remaps are layered on top and persisted to user://settings.cfg.

signal changed

const PATH := "user://settings.cfg"
const InputConfig := preload("res://scripts/systems/input_config.gd")

var master_volume := 0.9
var music_volume := 0.7
var sfx_volume := 0.85
var ambience_volume := 0.7
var fullscreen := false
var vsync := true
var text_scale := 1.0        # dialogue / HUD text size multiplier (1.0 - 1.5)
var text_speed := 1.0        # 0 = instant, 1 = normal, 2 = fast
var screen_shake := true
var glide_hold := true       # true: hold jump to glide, false: press to toggle
var remaps := {}             # action -> Array of serialised events

## "keyboard" or "gamepad" — the most recently used device, for prompt glyphs.
var last_device := "keyboard"


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_ensure_buses()
	InputConfig.apply_defaults()
	load_settings()
	apply()


func _input(event: InputEvent) -> void:
	var dev := last_device
	if event is InputEventJoypadButton or (event is InputEventJoypadMotion and absf(event.axis_value) > 0.4):
		dev = "gamepad"
	elif event is InputEventKey or event is InputEventMouseButton:
		dev = "keyboard"
	if dev != last_device:
		last_device = dev
		changed.emit()


func _ensure_buses() -> void:
	for bus_name in ["Music", "SFX", "Ambience"]:
		if AudioServer.get_bus_index(bus_name) == -1:
			AudioServer.add_bus()
			var idx := AudioServer.bus_count - 1
			AudioServer.set_bus_name(idx, bus_name)
			AudioServer.set_bus_send(idx, "Master")


func apply() -> void:
	_set_bus("Master", master_volume)
	_set_bus("Music", music_volume)
	_set_bus("SFX", sfx_volume)
	_set_bus("Ambience", ambience_volume)
	if not DisplayServer.get_name() == "headless":
		var mode := DisplayServer.WINDOW_MODE_FULLSCREEN if fullscreen else DisplayServer.WINDOW_MODE_WINDOWED
		if DisplayServer.window_get_mode() != mode:
			DisplayServer.window_set_mode(mode)
		DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_ENABLED if vsync else DisplayServer.VSYNC_DISABLED)
	for action in remaps.keys():
		InputConfig.set_action_events(action, InputConfig.deserialize_events(remaps[action]))
	changed.emit()


func _set_bus(bus_name: String, linear: float) -> void:
	var idx := AudioServer.get_bus_index(bus_name)
	if idx == -1:
		return
	AudioServer.set_bus_volume_db(idx, linear_to_db(maxf(linear, 0.0001)))
	AudioServer.set_bus_mute(idx, linear <= 0.001)


func remap(action: String, event: InputEvent) -> void:
	## Replace the binding for this device class (keyboard or gamepad) only.
	var events := InputMap.action_get_events(action)
	var is_pad := event is InputEventJoypadButton or event is InputEventJoypadMotion
	var kept: Array[InputEvent] = []
	for e in events:
		var e_pad := e is InputEventJoypadButton or e is InputEventJoypadMotion
		if e_pad != is_pad:
			kept.append(e)
	kept.append(event)
	InputConfig.set_action_events(action, kept)
	remaps[action] = InputConfig.serialize_events(kept)
	save_settings()
	changed.emit()


func reset_controls() -> void:
	remaps.clear()
	InputConfig.apply_defaults()
	save_settings()
	changed.emit()


func to_dict() -> Dictionary:
	return {
		"master_volume": master_volume, "music_volume": music_volume,
		"sfx_volume": sfx_volume, "ambience_volume": ambience_volume,
		"fullscreen": fullscreen, "vsync": vsync, "text_scale": text_scale,
		"text_speed": text_speed, "screen_shake": screen_shake,
		"glide_hold": glide_hold, "remaps": remaps,
	}


func from_dict(d: Dictionary) -> void:
	for k in d.keys():
		if k in self and k != "remaps":
			set(k, d[k])
	if d.has("remaps") and d["remaps"] is Dictionary:
		remaps = d["remaps"]


func save_settings() -> void:
	var cfg := ConfigFile.new()
	var d := to_dict()
	for k in d.keys():
		cfg.set_value("settings", k, d[k])
	cfg.save(PATH)


func load_settings() -> void:
	var cfg := ConfigFile.new()
	if cfg.load(PATH) != OK:
		return
	var d := {}
	for k in cfg.get_section_keys("settings"):
		d[k] = cfg.get_value("settings", k)
	from_dict(d)


## Human-readable label for the first binding of an action on the active device.
func action_label(action: String) -> String:
	return InputConfig.action_label(action, last_device)
