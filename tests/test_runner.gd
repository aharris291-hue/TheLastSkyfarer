extends Node
## Automated tests for The Last Skyfarer.
##
## Run headless from the project root:
##   godot --headless --path . res://tests/test_runner.tscn
## Exit code 0 = all passed. Results are also written to user://test_report.txt.
##
## Covers: data integrity (dialogue/quests/items/journal cross-references),
## save system (write, read, overwrite, corruption recovery, interrupted
## writes, missing files), quest logic, input remap persistence, and a full
## playthrough bot that drives the real scenes and physics from New Game to
## the end of the demo (including the glide route and Piko's hidden current).

var _worker := false
var passed := 0
var failed := 0
var log_lines: PackedStringArray = []


func _ready() -> void:
	if not _worker:
		var w := Node.new()
		w.set_script(get_script())
		w.set("_worker", true)
		w.process_mode = Node.PROCESS_MODE_ALWAYS
		get_tree().root.add_child.call_deferred(w)
		return
	await get_tree().process_frame
	_say("== The Last Skyfarer test run ==")
	test_data_integrity()
	test_save_system()
	test_quest_logic()
	test_input_remap()
	test_sprite_quality()
	await test_level_geometry()
	await test_playthrough()
	_say("== %d passed, %d failed ==" % [passed, failed])
	var f := FileAccess.open("user://test_report.txt", FileAccess.WRITE)
	if f:
		f.store_string("\n".join(log_lines))
	get_tree().quit(1 if failed > 0 else 0)


func _say(s: String) -> void:
	print(s)
	log_lines.append(s)


func ok(cond: bool, what: String) -> void:
	if cond:
		passed += 1
	else:
		failed += 1
		_say("  FAIL: " + what)


# --- Data -------------------------------------------------------------------------

func test_data_integrity() -> void:
	_say("-- data integrity")
	var speakers := DialogueDB.speakers
	for id in DialogueDB.dialogues.keys():
		var steps: Array = DialogueDB.dialogues[id]
		ok(steps.size() > 0, "dialogue %s is empty" % id)
		for st in steps:
			if st.has("t"):
				ok(speakers.has(st.get("s", "")), "dialogue %s: unknown speaker %s" % [id, st.get("s", "")])
				if st.has("p"):
					var tex := DialogueDB.portrait(st["s"], st["p"])
					ok(tex != null, "dialogue %s: missing portrait %s_%s" % [id, st["s"], st["p"]])
			if st.has("goto"):
				ok(DialogueDB.has(st["goto"]), "dialogue %s: goto %s missing" % [id, st["goto"]])
			for c in st.get("choice", []):
				if c.has("goto"):
					ok(DialogueDB.has(c["goto"]), "dialogue %s: choice goto missing" % id)
			_check_actions(st.get("do", []), "dialogue %s" % id)
	for qid in GameState.quests_db.keys():
		var q: Dictionary = GameState.quests_db[qid]
		ok(q.has("title") and q.has("objectives"), "quest %s malformed" % qid)
		for r in q.get("rewards", []):
			ok(GameState.items_db.has(r), "quest %s reward %s unknown" % [qid, r])
	for jid in GameState.journal_db.keys():
		ok(GameState.journal_db[jid].has("text"), "journal %s has no text" % jid)
	_say("   dialogues=%d quests=%d items=%d journal=%d" % [DialogueDB.dialogues.size(),
		GameState.quests_db.size(), GameState.items_db.size(), GameState.journal_db.size()])


func _check_actions(actions: Array, where: String) -> void:
	for a in actions:
		for k in a.keys():
			var v := str(a[k])
			match k:
				"give", "take":
					ok(GameState.items_db.has(v), "%s: unknown item %s" % [where, v])
				"quest_start", "quest_complete":
					ok(GameState.quests_db.has(v), "%s: unknown quest %s" % [where, v])
				"objective":
					var p := v.split(":")
					ok(not GameState.objective_def(p[0], p[1]).is_empty(), "%s: unknown objective %s" % [where, v])
				"journal":
					ok(GameState.journal_db.has(v), "%s: unknown journal %s" % [where, v])


# --- Save system ------------------------------------------------------------------

func test_save_system() -> void:
	_say("-- save system")
	var slot := "test_slot"
	SaveManager.delete_slot(slot)
	ok(SaveManager.read_slot(slot).is_empty(), "missing save should read as empty")
	ok(not SaveManager.load_game(slot), "loading a missing save should fail cleanly")

	GameState.reset()
	GameState.set_flag("test_flag")
	GameState.give_item("deed", 1, true)
	GameState.start_quest("morning_deliveries")
	GameState.advance_objective("morning_deliveries", "report")
	GameState.add_journal("note_wind", true)
	GameState.chapter = 2
	GameState.playtime = 123.0
	GameState.scene_path = "res://scenes/world/windrest.tscn"
	GameState.player_position = Vector2(1234, 567)
	ok(SaveManager.save_game(slot), "save should succeed")
	var d := SaveManager.read_slot(slot)
	ok(d.get("flags", {}).get("test_flag", false), "flag persisted")
	ok(int(d.get("inventory", {}).get("deed", 0)) == 1, "inventory persisted")
	ok(d.get("quests", {}).has("morning_deliveries"), "quest persisted")
	ok("note_wind" in d.get("journal", []), "journal persisted")
	ok(int(d.get("meta", {}).get("chapter", 0)) == 2, "meta chapter")

	# Round trip into GameState
	GameState.reset()
	GameState.from_dict(SaveManager.read_slot(slot))
	ok(GameState.has_flag("test_flag") and GameState.has_item("deed"), "from_dict restores state")
	ok(GameState.objective_done("morning_deliveries", "report"), "objective progress restored")
	ok(GameState.player_position.is_equal_approx(Vector2(1234, 567)), "position restored")

	# Overwrite keeps a backup of the previous save
	GameState.set_flag("second_save")
	ok(SaveManager.save_game(slot), "overwrite should succeed")
	ok(FileAccess.file_exists("user://saves/%s.json.bak" % slot), "backup created on overwrite")
	ok(SaveManager.read_slot(slot).get("flags", {}).get("second_save", false), "overwrite has new data")

	# Corrupt the main file: loader must fall back to the backup.
	var f := FileAccess.open("user://saves/%s.json" % slot, FileAccess.WRITE)
	f.store_string("{ this is not json")
	f.close()
	var rec := SaveManager.read_slot(slot)
	ok(not rec.is_empty(), "corrupt save recovers from backup")
	ok(rec.get("meta", {}).get("recovered", false), "recovered save is flagged")

	# Interrupted write: a stray .tmp must not break reading.
	var t := FileAccess.open("user://saves/%s.json.tmp" % slot, FileAccess.WRITE)
	t.store_string("{\"partial\":")
	t.close()
	ok(not SaveManager.read_slot(slot).is_empty(), "stray tmp file is ignored")
	ok(SaveManager.save_game(slot), "save after interrupted write succeeds")
	ok(not SaveManager.read_slot(slot).get("meta", {}).get("recovered", false), "fresh save no longer flagged recovered")

	# Totally invalid files in both places → empty, no crash
	for p in ["user://saves/%s.json" % slot, "user://saves/%s.json.bak" % slot]:
		var g := FileAccess.open(p, FileAccess.WRITE)
		g.store_string("[]")
		g.close()
	ok(SaveManager.read_slot(slot).is_empty(), "invalid save data reads as empty")
	SaveManager.delete_slot(slot)
	ok(not SaveManager.has_save(slot), "delete removes slot")


# --- Quests ---------------------------------------------------------------------------

func test_quest_logic() -> void:
	_say("-- quest logic")
	GameState.reset()
	GameState.start_quest("morning_deliveries")
	ok(GameState.current_objective_text().begins_with("Report"), "first objective shown")
	GameState.advance_objective("morning_deliveries", "report")
	ok(GameState.current_objective_text().begins_with("Deliver"), "deliveries revealed after report")
	for o in ["tavern", "tessa", "cliffs"]:
		GameState.advance_objective("morning_deliveries", o)
	ok(GameState.current_objective_text().begins_with("Return"), "return objective after deliveries")
	ok(GameState.quest_state("morning_deliveries") == "active", "manual turn-in quest stays active")
	GameState.complete_quest("morning_deliveries")
	ok(GameState.quest_state("morning_deliveries") == "complete", "quest completes")
	ok(GameState.has_item("courier_wages"), "reward granted")
	GameState.start_quest("hidden_workshop")
	for i in 3:
		GameState.advance_objective("hidden_workshop", "search")
	ok(GameState.objective_done("hidden_workshop", "search"), "counted objective completes at 3")
	GameState.advance_objective("hidden_workshop", "enter")
	GameState.advance_objective("hidden_workshop", "compartment")
	GameState.advance_objective("hidden_workshop", "journal")
	ok(GameState.quest_state("hidden_workshop") == "complete", "auto-complete quest completes")
	ok(GameState.check(["quest:hidden_workshop:complete", "!nonexistent_flag"]), "condition arrays")


func test_input_remap() -> void:
	_say("-- input remap")
	var IC := preload("res://scripts/systems/input_config.gd")
	var before := IC.action_label("jump", "keyboard")
	var k := InputEventKey.new()
	k.physical_keycode = KEY_K
	Settings.remap("jump", k)
	ok(IC.action_label("jump", "keyboard") == "K", "remap applies")
	ok(IC.action_label("jump", "gamepad") == "A", "remap keeps the other device's binding")
	var ser := IC.serialize_events(InputMap.action_get_events("jump"))
	var de := IC.deserialize_events(ser)
	ok(de.size() == ser.size(), "serialise round trip")
	Settings.reset_controls()
	ok(IC.action_label("jump", "keyboard") == before, "reset restores defaults")


# --- Level geometry ------------------------------------------------------------------

## Visual regressions from the first demo build: Kieran's feet were cut off
## in the jump frames and his body was half transparent.
func test_sprite_quality() -> void:
	var frames := {"idle": 5, "walk": 6, "run": 6, "jump": 4, "glide": 3}
	for anim in frames.keys():
		var img: Image = load("res://assets/characters/kieran/kieran_%s.png" % anim).get_image()
		if img.is_compressed():
			img.decompress()
		var n: int = frames[anim]
		var fw := img.get_width() / n
		var h := img.get_height()
		var clipped := 0
		var solid := 0
		var visible := 0
		for f in n:
			# The bottom 3 rows of every frame stay empty: nothing touches the edge.
			for x in range(f * fw, (f + 1) * fw):
				for y in range(h - 3, h):
					if img.get_pixel(x, y).a > 0.05:
						clipped += 1
			for x in range(f * fw, (f + 1) * fw, 2):
				for y in range(0, h, 2):
					var a := img.get_pixel(x, y).a
					if a > 0.05:
						visible += 1
						if a > 0.98:
							solid += 1
		ok(clipped == 0, "kieran_%s frames are not clipped at the bottom" % anim)
		ok(visible > 0 and float(solid) / visible > 0.85, "kieran_%s body is opaque (%.0f%% solid)" % [anim, 100.0 * solid / maxi(visible, 1)])
	# NPC sprites are pre-sized for the game (no 3x minification shimmer).
	for path in ["tessa/tessa_side", "bram/bram_side", "elara/elara_side", "maren/maren_placeholder", "piko/piko_side"]:
		var t: Texture2D = load("res://assets/characters/%s.png" % path)
		ok(t.get_height() <= 240, "%s is pre-sized (%d px tall)" % [path, t.get_height()])


func test_level_geometry() -> void:
	_say("-- level geometry: Skywatch climb reachability")
	# Max jump height with default tuning: v^2 / 2g.
	var g: float = ProjectSettings.get_setting("physics/2d/default_gravity")
	var v := 1080.0
	var max_h := v * v / (2.0 * g)
	ok(max_h > 200.0, "jump height %.0f px clears 200 px steps" % max_h)
	# Platform tops along the climb: [x, top, width]
	var climb := [[5050, 780, 110], [5230, 664, 230], [5430, 550, 170], [5230, 430, 170], [5470, 310, 170], [5720, 210, 160], [6060, 140, 470]]
	var prev := [5000.0, 900.0, 200.0]
	for p in climb:
		var dy: float = prev[1] - p[1]
		var gap: float = absf(p[0] - prev[0]) - (p[2] + prev[2]) * 0.5
		ok(dy <= max_h - 20.0, "step to platform at %d rises %.0f px (max %.0f)" % [p[0], dy, max_h])
		ok(gap <= 380.0, "gap to platform at %d is %.0f px" % [p[0], gap])
		prev = [float(p[0]), float(p[1]), float(p[2])]


# --- Playthrough bot -------------------------------------------------------------

var level: Node


func _advance_dialogue() -> void:
	var ev := InputEventAction.new()
	ev.action = "advance"
	ev.pressed = true
	Input.parse_input_event(ev)
	var up := InputEventAction.new()
	up.action = "advance"
	up.pressed = false
	Input.parse_input_event(up)


func _run_dialogues(max_time := 30.0) -> void:
	var t := 0.0
	while t < max_time:
		await get_tree().create_timer(0.08, true, true).timeout
		t += 0.08
		if DialogueUI.active:
			if DialogueUI.choices_box.visible:
				var first := DialogueUI.choices_box.get_child(0) as Button
				if first:
					first.pressed.emit()
			else:
				_advance_dialogue()
		elif t > 0.6:
			return


func _talk(node_name: String) -> void:
	var n: Node = level.world.get_node_or_null(node_name)
	ok(n != null, "node %s exists" % node_name)
	if n == null:
		return
	level.player.global_position = n.global_position + Vector2(-60, 0)
	await get_tree().create_timer(0.2).timeout
	ok(n.can_interact(), "%s can be interacted with" % node_name)
	n.interact(level.player)
	await _run_dialogues()


func _goto_scene(path: String, flag_wait := 2.0) -> void:
	await get_tree().create_timer(flag_wait).timeout
	level = get_tree().get_first_node_in_group("level")
	ok(level != null and level.scene_file_path == path, "scene %s loaded" % path)


func _wait_scene(path: String, timeout := 10.0) -> void:
	var t := 0.0
	while t < timeout:
		await get_tree().create_timer(0.2).timeout
		t += 0.2
		var l := get_tree().get_first_node_in_group("level")
		if l and l.scene_file_path == path and not Router.busy:
			level = l
			await get_tree().create_timer(0.5).timeout
			return
	ok(false, "timed out waiting for scene %s" % path)


func test_playthrough() -> void:
	_say("-- playthrough bot (real scenes and physics)")
	Settings.text_speed = 0.0
	GameState.reset()
	Router.go("res://scenes/world/windrest.tscn", "", false, 0.05)
	await _wait_scene("res://scenes/world/windrest.tscn")
	# Opening: banner + monologue
	await get_tree().create_timer(3.8).timeout
	await _run_dialogues()
	ok(GameState.has_flag("opening_done"), "opening played")
	ok(GameState.quest_state("morning_deliveries") == "active", "deliveries quest started")
	_say("   chapter 1: deliveries")
	await _talk("maren")
	ok(GameState.has_item("parcel_tessa") and GameState.has_item("parcel_tavern") and GameState.has_item("parcel_cliffs"), "parcels received")
	await _talk("tavern")
	await _talk("tessa")
	await _talk("villager")
	ok(GameState.objective_done("morning_deliveries", "tavern"), "tavern delivered")
	ok(GameState.objective_done("morning_deliveries", "tessa"), "tessa delivered")
	ok(GameState.objective_done("morning_deliveries", "cliffs"), "cloud edge delivered")
	await _talk("maren")
	await get_tree().create_timer(3.5).timeout   # sunset fade, then the deed scene
	await _run_dialogues()
	ok(GameState.quest_state("morning_deliveries") == "complete", "deliveries complete")
	ok(GameState.has_item("deed") and GameState.time_of_day == "sunset", "deed received at sunset")
	ok(SaveManager.has_save("auto"), "autosave written at chapter milestone")
	# Collect the island's notes (Elias Was Here)
	for c in level.world.get_children():
		if c is Collectible and c.visible:
			level.player.global_position = c.global_position
			await get_tree().create_timer(0.15).timeout
			c.interact(level.player)
			await get_tree().create_timer(0.2).timeout
	ok(GameState.collectible_count("elias_notes").x >= 4, "Elias's notes collected on Brindle Isle")
	_say("   chapter 2: workshop")
	await _talk("workshop_door")
	await _wait_scene("res://scenes/world/workshop.tscn")
	await get_tree().create_timer(4.6).timeout
	await _run_dialogues()
	ok(GameState.objective_done("hidden_workshop", "enter"), "workshop entered")
	for n in ["maps", "sketches", "notes"]:
		await _talk(n)
	await get_tree().create_timer(0.8).timeout
	await _run_dialogues()
	ok(GameState.objective_done("hidden_workshop", "search"), "workshop searched")
	await _talk("floorboard")
	ok(GameState.has_item("ancient_glider"), "glider found")
	await _talk("floorboard")
	await get_tree().create_timer(1.0).timeout
	await _run_dialogues()
	ok(GameState.quest_state("hidden_workshop") == "complete", "chapter 2 complete")
	ok(GameState.has_flag("has_glider") and GameState.has_flag("compass_active"), "compass awakened")
	_say("   chapter 3: first flight")
	await _wait_scene("res://scenes/world/windrest.tscn", 15.0)
	await get_tree().create_timer(1.0).timeout
	ok(GameState.time_of_day == "dawn", "next morning")
	await _talk("glider")
	await get_tree().create_timer(0.5).timeout
	ok(GameState.has_flag("piko_joined") and level.piko != null, "Piko joined")
	await _fly_route()


func _hold(action: String, on: bool) -> void:
	if on:
		Input.action_press(action)
	else:
		Input.action_release(action)


func _fly_route() -> void:
	var p: CharacterBody2D = level.player
	await get_tree().create_timer(1.0).timeout
	while DialogueUI.active:
		_advance_dialogue()
		await get_tree().create_timer(0.1).timeout
	p.global_position = Vector2(9700, 820)
	await get_tree().create_timer(0.3).timeout
	await _run_dialogues(4.0)
	# Leg 1: run off the bluff, glide through the first updraft to the first island.
	_hold("move_right", true)
	_hold("run", true)
	var max_x := 0.0
	var t := 0.0
	var jumped := false
	while t < 14.0:
		await get_tree().physics_frame
		t += get_physics_process_delta_time()
		max_x = maxf(max_x, p.global_position.x)
		if not jumped and p.global_position.x > 9930:
			_hold("jump", true)
			jumped = true
		if jumped:
			_hold("glide", true)
		if p.is_on_floor() and p.global_position.x > 11700:
			break
	_hold("move_right", false)
	_hold("glide", false)
	_hold("jump", false)
	_hold("run", false)
	ok(p.global_position.x > 11700 and p.is_on_floor(), "landed on the first island (x=%.0f, y=%.0f)" % [p.global_position.x, p.global_position.y])
	# Leg 2: wait at the island's edge for Piko to sense the hidden current.
	p.global_position = Vector2(12230, 780)
	t = 0.0
	var u2_revealed := false
	while t < 10.0:
		await get_tree().create_timer(0.2).timeout
		t += 0.2
		if DialogueUI.active:
			_advance_dialogue()
		if GameState.has_flag("revealed_wind_1"):
			u2_revealed = true
			break
	ok(u2_revealed, "Piko revealed the hidden wind current")
	await _run_dialogues(6.0)
	# Leg 3 and 4: glide on via the revealed current, the second island, and the last updraft.
	_hold("move_right", true)
	_hold("run", true)
	var reached := false
	var deaths := 0
	t = 0.0
	var started_jump := false
	var dbg := 0.0
	while t < 40.0:
		await get_tree().physics_frame
		t += get_physics_process_delta_time()
		dbg += get_physics_process_delta_time()
		if dbg > 2.0:
			dbg = 0.0
			print("   [route] x=%.0f y=%.0f floor=%s locked=%s dlg=%s glide=%s vel=%s" % [p.global_position.x, p.global_position.y, p.is_on_floor(), p.locked, DialogueUI.active, p.gliding, p.velocity])
		if DialogueUI.active:
			_hold("glide", false)
			_advance_dialogue()
			await get_tree().create_timer(0.1).timeout
			if GameState.has_flag("demo_complete"):
				reached = true
				break
			continue
		if p.is_on_floor():
			if not started_jump:
				_hold("jump", true)
				started_jump = true
			else:
				_hold("jump", false)
				started_jump = false
		_hold("glide", not p.is_on_floor())
		if p.global_position.y > 1450:
			deaths += 1
		if GameState.has_flag("demo_complete"):
			reached = true
			break
	for a in ["move_right", "run", "glide", "jump"]:
		_hold(a, false)
	ok(reached, "reached where the wind refuses to go (x=%.0f)" % p.global_position.x)
	await _run_dialogues(8.0)
	ok(GameState.quest_state("into_the_clouds") == "complete", "chapter 3 objective complete")
	ok(deaths == 0, "no falls on the scripted route")
	_say("   notes found: %s, playtime %.0fs" % [str(GameState.collectible_count("elias_notes")), GameState.playtime])
