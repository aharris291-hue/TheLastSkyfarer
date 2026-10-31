extends Node
## Save / load with crash-safe writes (autoload "SaveManager").
##
## Each slot is a JSON file in user://saves/. Writes go to a temporary file,
## are read back and verified, the previous save is kept as a .bak, and only
## then is the temporary file renamed into place. Loading falls back to the
## .bak if the main file is missing or corrupt. See SAVE_SYSTEM_SPECIFICATION.md.

signal saved(slot: String)
signal loaded(slot: String)

const DIR := "user://saves"
const SLOTS := ["slot1", "slot2", "slot3"]
const AUTO := "auto"

var last_error := ""


func _ready() -> void:
	DirAccess.make_dir_recursive_absolute(DIR)


func _path(slot: String) -> String:
	return "%s/%s.json" % [DIR, slot]


func _capture_scene_state() -> void:
	var level := get_tree().get_first_node_in_group("level")
	if level and level.has_method("capture_state"):
		level.capture_state()


func save_game(slot: String) -> bool:
	_capture_scene_state()
	var data := GameState.to_dict()
	data["meta"] = {
		"slot": slot,
		"saved_at": Time.get_datetime_string_from_system(false, true),
		"unix": Time.get_unix_time_from_system(),
		"chapter": GameState.chapter,
		"location": _location_label(),
		"playtime": GameState.playtime,
		"game_version": ProjectSettings.get_setting("application/config/version", "0"),
	}
	var ok := write_atomic(_path(slot), JSON.stringify(data, "\t"))
	if ok:
		saved.emit(slot)
	return ok


func autosave() -> bool:
	var ok := save_game(AUTO)
	if ok:
		GameState.notify.emit("Progress saved", "save")
	return ok


func write_atomic(path: String, text: String) -> bool:
	var tmp := path + ".tmp"
	var f := FileAccess.open(tmp, FileAccess.WRITE)
	if f == null:
		last_error = "Could not open %s for writing (%s)" % [tmp, error_string(FileAccess.get_open_error())]
		push_error(last_error)
		return false
	f.store_string(text)
	f.flush()
	f.close()
	# Verify what actually reached the disk before replacing anything.
	var check := FileAccess.open(tmp, FileAccess.READ)
	if check == null or not JSON.parse_string(check.get_as_text()) is Dictionary:
		last_error = "Verification of %s failed" % tmp
		push_error(last_error)
		DirAccess.remove_absolute(tmp)
		return false
	check.close()
	if FileAccess.file_exists(path):
		var bak := path + ".bak"
		if FileAccess.file_exists(bak):
			DirAccess.remove_absolute(bak)
		DirAccess.rename_absolute(path, bak)
	var err := DirAccess.rename_absolute(tmp, path)
	if err != OK:
		last_error = "Rename failed: %s" % error_string(err)
		push_error(last_error)
		return false
	return true


func read_slot(slot: String) -> Dictionary:
	## Returns the parsed save, falling back to the backup. Empty if neither works.
	for p in [_path(slot), _path(slot) + ".bak"]:
		if not FileAccess.file_exists(p):
			continue
		var f := FileAccess.open(p, FileAccess.READ)
		if f == null:
			continue
		var parsed = JSON.parse_string(f.get_as_text())
		if parsed is Dictionary and parsed.has("version") and parsed.has("flags"):
			if p.ends_with(".bak"):
				push_warning("Save %s was unreadable; recovered from backup." % slot)
				parsed["meta"] = parsed.get("meta", {})
				parsed["meta"]["recovered"] = true
			return _migrate(parsed)
	return {}


func _migrate(d: Dictionary) -> Dictionary:
	## Upgrade older save formats here. Version 1 is the first format.
	var v := int(d.get("version", 1))
	if v > GameState.SAVE_VERSION:
		push_warning("Save is from a newer version of the game (%d)." % v)
	return d


func has_save(slot: String) -> bool:
	return FileAccess.file_exists(_path(slot)) or FileAccess.file_exists(_path(slot) + ".bak")


func any_save() -> bool:
	for s in SLOTS + [AUTO]:
		if has_save(s):
			return true
	return false


func latest_slot() -> String:
	var best := ""
	var best_t := -1.0
	for s in SLOTS + [AUTO]:
		var m: Dictionary = read_slot(s).get("meta", {})
		if m.is_empty():
			continue
		if float(m.get("unix", 0)) > best_t:
			best_t = float(m.get("unix", 0))
			best = s
	return best


func slot_meta(slot: String) -> Dictionary:
	return read_slot(slot).get("meta", {})


func load_game(slot: String) -> bool:
	var d := read_slot(slot)
	if d.is_empty():
		last_error = "No valid save in %s" % slot
		return false
	GameState.from_dict(d)
	loaded.emit(slot)
	var scene: String = GameState.scene_path
	if scene == "" or not ResourceLoader.exists(scene):
		scene = "res://scenes/world/windrest.tscn"
		GameState.has_position = false
	Router.go(scene, "", true)
	return true


func delete_slot(slot: String) -> void:
	for p in [_path(slot), _path(slot) + ".bak", _path(slot) + ".tmp"]:
		if FileAccess.file_exists(p):
			DirAccess.remove_absolute(p)


func _location_label() -> String:
	var level := get_tree().get_first_node_in_group("level")
	if level and level.has_method("location_label"):
		return level.location_label()
	return "Brindle Isle"


static func format_time(seconds: float) -> String:
	var s := int(seconds)
	return "%d:%02d:%02d" % [s / 3600, (s / 60) % 60, s % 60]
