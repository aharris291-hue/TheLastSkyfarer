extends Node
## Single source of truth for persistent game progress (autoload "GameState").
##
## Gameplay code changes progress only through this API (flags, items, quests,
## journal, discoveries) so that everything is saved consistently and UI can
## react through signals instead of polling.

signal flag_changed(flag: String, value: bool)
signal inventory_changed
signal quest_changed(quest_id: String)
signal objective_changed(quest_id: String)
signal journal_added(entry_id: String)
signal location_discovered(location_id: String)
signal notify(text: String, kind: String)
signal story_event(event_name: String)
signal time_of_day_changed(tod: String)

const SAVE_VERSION := 1

var items_db := {}
var quests_db := {}
var journal_db := {}
var locations_db := {}

var flags := {}
var inventory := {}            # item_id -> count
var quests := {}               # quest_id -> {"state": String, "obj": {obj_id: int}}
var tracked_quest := ""
var journal := []              # entry ids in discovery order
var discovered := []           # location ids
var time_of_day := "dawn"
var chapter := 1
var playtime := 0.0
var scene_path := ""
var player_position := Vector2.ZERO
var has_position := false
var settings_snapshot := {}


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	items_db = _load_json("res://data/items.json")
	quests_db = _load_json("res://data/quests.json")
	journal_db = _load_json("res://data/journal.json")
	locations_db = _load_json("res://data/locations.json")


func _process(delta: float) -> void:
	if not get_tree().paused and scene_path != "":
		playtime += delta


static func _load_json(path: String) -> Dictionary:
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null:
		push_error("Missing data file: %s" % path)
		return {}
	var parsed = JSON.parse_string(f.get_as_text())
	if parsed is Dictionary:
		return parsed
	push_error("Invalid JSON in %s" % path)
	return {}


func reset() -> void:
	flags.clear()
	inventory.clear()
	quests.clear()
	journal.clear()
	discovered.clear()
	tracked_quest = ""
	time_of_day = "dawn"
	chapter = 1
	playtime = 0.0
	scene_path = ""
	player_position = Vector2.ZERO
	has_position = false


# --- Flags -----------------------------------------------------------------

func has_flag(flag: String) -> bool:
	return flags.get(flag, false)


func set_flag(flag: String, value := true) -> void:
	if flags.get(flag, false) == value:
		return
	flags[flag] = value
	flag_changed.emit(flag, value)


# --- Inventory -------------------------------------------------------------

func give_item(item_id: String, count := 1, silent := false) -> void:
	inventory[item_id] = inventory.get(item_id, 0) + count
	inventory_changed.emit()
	if not silent:
		notify.emit("Received: %s" % item_name(item_id), "item")


func take_item(item_id: String, count := 1) -> bool:
	if inventory.get(item_id, 0) < count:
		return false
	inventory[item_id] -= count
	if inventory[item_id] <= 0:
		inventory.erase(item_id)
	inventory_changed.emit()
	return true


func has_item(item_id: String) -> bool:
	return inventory.get(item_id, 0) > 0


func item_name(item_id: String) -> String:
	return items_db.get(item_id, {}).get("name", item_id)


# --- Quests ----------------------------------------------------------------

func start_quest(quest_id: String) -> void:
	if quests.has(quest_id):
		return
	var def: Dictionary = quests_db.get(quest_id, {})
	if def.is_empty():
		push_error("Unknown quest %s" % quest_id)
		return
	var obj := {}
	for o in def.get("objectives", []):
		obj[o["id"]] = 0
	quests[quest_id] = {"state": "active", "obj": obj}
	if def.get("main", false) or tracked_quest == "":
		tracked_quest = quest_id
	quest_changed.emit(quest_id)
	notify.emit("New quest: %s" % def.get("title", quest_id), "quest_start")


func quest_state(quest_id: String) -> String:
	return quests.get(quest_id, {}).get("state", "none")


func advance_objective(quest_id: String, obj_id: String, amount := 1) -> void:
	if quest_state(quest_id) != "active":
		return
	var q: Dictionary = quests[quest_id]
	var def := objective_def(quest_id, obj_id)
	if def.is_empty():
		return
	var need: int = def.get("count", 1)
	var before: int = q["obj"].get(obj_id, 0)
	if before >= need:
		return
	q["obj"][obj_id] = mini(before + amount, need)
	objective_changed.emit(quest_id)
	if q["obj"][obj_id] >= need:
		notify.emit("Objective complete: %s" % def.get("text", obj_id), "objective")
	if quests_db[quest_id].get("auto_complete", false) and all_objectives_done(quest_id):
		complete_quest(quest_id)


func objective_def(quest_id: String, obj_id: String) -> Dictionary:
	for o in quests_db.get(quest_id, {}).get("objectives", []):
		if o["id"] == obj_id:
			return o
	return {}


func objective_done(quest_id: String, obj_id: String) -> bool:
	if quest_state(quest_id) == "complete":
		return true
	var def := objective_def(quest_id, obj_id)
	return quests.get(quest_id, {}).get("obj", {}).get(obj_id, 0) >= def.get("count", 1)


func all_objectives_done(quest_id: String) -> bool:
	for o in quests_db.get(quest_id, {}).get("objectives", []):
		if o.get("optional", false):
			continue
		if not objective_done(quest_id, o["id"]):
			return false
	return true


func complete_quest(quest_id: String) -> void:
	if quest_state(quest_id) != "active":
		return
	quests[quest_id]["state"] = "complete"
	var def: Dictionary = quests_db.get(quest_id, {})
	for reward in def.get("rewards", []):
		give_item(reward, 1)
	if tracked_quest == quest_id:
		tracked_quest = ""
		for qid in quests.keys():
			if quests[qid]["state"] == "active":
				tracked_quest = qid
				if quests_db.get(qid, {}).get("main", false):
					break
	quest_changed.emit(quest_id)
	notify.emit("Quest complete: %s" % def.get("title", quest_id), "quest_complete")


## Text of the first unfinished objective of the tracked quest, for the HUD.
func current_objective_text() -> String:
	if tracked_quest == "" or quest_state(tracked_quest) != "active":
		return ""
	for o in quests_db[tracked_quest].get("objectives", []):
		if o.has("hidden_until") and not check(o["hidden_until"]):
			continue
		if not objective_done(tracked_quest, o["id"]):
			var t: String = o.get("text", "")
			if o.get("count", 1) > 1:
				t += " (%d/%d)" % [quests[tracked_quest]["obj"].get(o["id"], 0), o["count"]]
			return t
	return quests_db[tracked_quest].get("turn_in", "")


# --- Journal & discoveries --------------------------------------------------

func add_journal(entry_id: String, silent := false) -> void:
	if entry_id in journal or not journal_db.has(entry_id):
		return
	journal.append(entry_id)
	journal_added.emit(entry_id)
	if not silent:
		var kind: String = journal_db[entry_id].get("kind", "journal")
		var label := "Piko's Notes updated" if kind == "piko" else "Journal: %s" % journal_db[entry_id].get("title", "")
		notify.emit(label, "journal")


func discover(location_id: String) -> void:
	if location_id in discovered or not locations_db.has(location_id):
		return
	discovered.append(location_id)
	location_discovered.emit(location_id)


func collectible_count(group: String) -> Vector2i:
	var total := 0
	var found := 0
	for id in journal_db.keys():
		if journal_db[id].get("collectible", "") == group:
			total += 1
			if id in journal:
				found += 1
	return Vector2i(found, total)


func set_time_of_day(tod: String) -> void:
	if tod == time_of_day:
		return
	time_of_day = tod
	time_of_day_changed.emit(tod)


# --- Conditions and actions (used by dialogue, triggers, NPCs) ---------------

## Evaluates a condition string or array of strings (AND).
## Forms: "flag", "!flag", "item:id", "quest:id:state", "obj:quest:obj".
func check(cond) -> bool:
	if cond == null:
		return true
	if cond is Array:
		for c in cond:
			if not check(c):
				return false
		return true
	var s := str(cond).strip_edges()
	if s == "":
		return true
	if s.begins_with("!"):
		return not check(s.substr(1))
	var parts := s.split(":")
	match parts[0]:
		"item":
			return has_item(parts[1])
		"quest":
			return quest_state(parts[1]) == (parts[2] if parts.size() > 2 else "active")
		"obj":
			return objective_done(parts[1], parts[2])
		"tod":
			return time_of_day == parts[1]
	return has_flag(s)


func run_actions(actions: Array) -> void:
	for a in actions:
		if not a is Dictionary:
			continue
		for key in a.keys():
			var v = a[key]
			match key:
				"set":
					set_flag(str(v), true)
				"clear":
					set_flag(str(v), false)
				"give":
					give_item(str(v), int(a.get("n", 1)))
				"take":
					take_item(str(v), int(a.get("n", 1)))
				"quest_start":
					start_quest(str(v))
				"objective":
					var p := str(v).split(":")
					advance_objective(p[0], p[1], int(a.get("n", 1)))
				"quest_complete":
					complete_quest(str(v))
				"journal":
					add_journal(str(v))
				"sfx":
					AudioManager.play_sfx(str(v))
				"event":
					story_event.emit(str(v))
				"time":
					set_time_of_day(str(v))
				"chapter":
					chapter = int(v)
				"autosave":
					SaveManager.autosave()


# --- Serialisation ----------------------------------------------------------

func to_dict() -> Dictionary:
	return {
		"version": SAVE_VERSION,
		"flags": flags.duplicate(true),
		"inventory": inventory.duplicate(true),
		"quests": quests.duplicate(true),
		"tracked_quest": tracked_quest,
		"journal": journal.duplicate(),
		"discovered": discovered.duplicate(),
		"time_of_day": time_of_day,
		"chapter": chapter,
		"playtime": playtime,
		"scene_path": scene_path,
		"player_position": [player_position.x, player_position.y],
	}


func from_dict(d: Dictionary) -> void:
	reset()
	flags = d.get("flags", {})
	inventory = {}
	for k in d.get("inventory", {}).keys():
		inventory[k] = int(d["inventory"][k])
	quests = {}
	var raw_q: Dictionary = d.get("quests", {})
	for qid in raw_q.keys():
		var obj := {}
		for oid in raw_q[qid].get("obj", {}).keys():
			obj[oid] = int(raw_q[qid]["obj"][oid])
		quests[qid] = {"state": str(raw_q[qid].get("state", "active")), "obj": obj}
	tracked_quest = d.get("tracked_quest", "")
	journal = Array(d.get("journal", []))
	discovered = Array(d.get("discovered", []))
	time_of_day = d.get("time_of_day", "dawn")
	chapter = int(d.get("chapter", 1))
	playtime = float(d.get("playtime", 0.0))
	scene_path = d.get("scene_path", "")
	var p = d.get("player_position", [0, 0])
	player_position = Vector2(float(p[0]), float(p[1]))
	has_position = true
