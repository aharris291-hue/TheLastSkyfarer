extends Node
## Captures screenshots of key moments for milestone reviews.
## Run (needs a display; use xvfb-run on a server):
##   godot --path . res://tests/shot_runner.tscn -- --out=/tmp/shots

var out_dir := "user://shots"

const SHOTS := [
	["00_title", "res://scenes/ui/title_screen.tscn", Vector2.ZERO, "dawn", [], ""],
	# name, scene, position, time of day, flags, extra
	["01_bluff_dawn", "res://scenes/world/windrest.tscn", Vector2(9060, 820), "dawn", ["opening_done"], ""],
	["02_village_square", "res://scenes/world/windrest.tscn", Vector2(4850, 900), "day", ["opening_done"], ""],
	["03_post_house", "res://scenes/world/windrest.tscn", Vector2(5900, 900), "day", ["opening_done"], "talk_maren"],
	["04_skywatch", "res://scenes/world/windrest.tscn", Vector2(6000, 140), "day", ["opening_done"], ""],
	["05_tavern", "res://scenes/world/windrest.tscn", Vector2(3700, 900), "day", ["opening_done"], ""],
	["06_whispermill", "res://scenes/world/windrest.tscn", Vector2(2300, 900), "sunset", ["opening_done"], ""],
	["07_cloud_edge", "res://scenes/world/windrest.tscn", Vector2(700, 900), "day", ["opening_done"], ""],
	["08_workshop", "res://scenes/world/workshop.tscn", Vector2(1300, 900), "night", ["opening_done", "deed_received", "workshop_entered"], ""],
	["09_piko_glider", "res://scenes/world/windrest.tscn", Vector2(9600, 820), "dawn", ["opening_done", "deed_received", "compass_active", "has_glider", "chapter3_banner"], ""],
	["10_gliding", "res://scenes/world/windrest.tscn", Vector2(11000, 600), "dawn", ["opening_done", "deed_received", "compass_active", "has_glider", "piko_joined", "chapter3_banner"], "glide"],
	["11_fog", "res://scenes/world/windrest.tscn", Vector2(16700, 500), "dawn", ["opening_done", "deed_received", "compass_active", "has_glider", "piko_joined", "chapter3_banner", "reached_fog"], "glide"],
	["13_journal_quests", "res://scenes/world/windrest.tscn", Vector2(6000, 900), "day", ["opening_done"], "quests"],
	["12_journal_map", "res://scenes/world/windrest.tscn", Vector2(6000, 900), "day", ["opening_done"], "map"],
]


var _worker := false


func _ready() -> void:
	if not _worker:
		# The scene we start in is replaced on every scene change, so hand the
		# work to a copy parented to the root.
		var w := Node.new()
		w.set_script(get_script())
		w.set("_worker", true)
		w.process_mode = Node.PROCESS_MODE_ALWAYS
		get_tree().root.add_child.call_deferred(w)
		return
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--out="):
			out_dir = a.substr(6)
	DirAccess.make_dir_recursive_absolute(out_dir)
	await get_tree().process_frame
	for s in SHOTS:
		await _shot(s)
	get_tree().quit()


func _shot(s: Array) -> void:
	GameState.reset()
	for f in s[4]:
		GameState.flags[f] = true
	GameState.time_of_day = s[3]
	if "piko_joined" in s[4] or "compass_active" in s[4]:
		GameState.quests["into_the_clouds"] = {"state": "active", "obj": {"bluff": 1 if "piko_joined" in s[4] else 0, "glide": 0, "edge": 0}}
		GameState.tracked_quest = "into_the_clouds"
	else:
		GameState.start_quest("morning_deliveries")
	GameState.discovered = ["cloud_edge", "whispermill", "windrest", "post_house", "tavern", "skywatch", "bluff"]
	GameState.player_position = s[2]
	GameState.has_position = true
	GameState.scene_path = s[1]
	Router.go(s[1], "", true, 0.05)
	await get_tree().create_timer(1.6).timeout
	var level := get_tree().get_first_node_in_group("level")
	if level and level.player:
		level.player.global_position = s[2]
		level.camera.snap()
		match s[5]:
			"glide":
				level.player.gliding = true
				level.player.facing = 1
				level.player.sprite.play("glide")
				if level.piko == null:
					level.spawn_piko()
				level.piko.global_position = s[2] + Vector2(-150, -150)
			"talk_maren":
				var m: Node = level.world.get_node_or_null("maren")
				if m:
					m.interact(level.player)
			"quests":
				GameState.add_journal("note_wind", true)
				GameState.give_item("parcel_tessa", 1, true)
				level.open_menu(preload("res://scripts/ui/journal_menu.gd").new())
			"map":
				var j := preload("res://scripts/ui/journal_menu.gd").new()
				j.start_tab = 3
				level.open_menu(j)
	await get_tree().create_timer(1.4).timeout
	var img := get_viewport().get_texture().get_image()
	img.save_png("%s/%s.png" % [out_dir, s[0]])
	print("shot ", s[0])
	if level:
		for c in level.menu_layer.get_children():
			c.queue_free()
	get_tree().paused = false
	if DialogueUI.active:
		DialogueUI.root.visible = false
