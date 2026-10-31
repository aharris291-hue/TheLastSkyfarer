extends Level
## Elias Thorn's workshop on Old Cartographer's Bluff (Chapter 2).
## Search for clues → hidden floor compartment → final journal entry → the
## compass wakes. Lit by lanterns at night.

const FLOOR := 900.0
const ROOM_W := 2600.0

var compartment: Node2D
var compass: Node2D
var _gust: CPUParticles2D


func build() -> void:
	level_id = "workshop"
	music = "workshop"
	ambience = ""
	bounds = Rect2(0, 0, ROOM_W, 1080)
	death_y = 5000.0
	spawns = {"default": Vector2(300, FLOOR), "door": Vector2(300, FLOOR)}
	_build_room()
	_build_props()
	_build_interactions()


func after_ready() -> void:
	# Indoors the sky is hidden behind the walls, but keep night outside the windows.
	if GameState.time_of_day != "night":
		GameState.set_time_of_day("night")
	sky.apply("night", 0.0)
	canvas_mod.color = Color(0.86, 0.8, 0.72)
	if not GameState.has_flag("workshop_entered"):
		GameState.set_flag("workshop_entered")
		GameState.discover("workshop")
		HUD.banner("Chapter 2", "The Hidden Workshop", 3.0)
		await get_tree().create_timer(1.2).timeout
		await DialogueUI.play("workshop_enter")
		HUD.show_tutorial("Look around. Things worth inspecting are marked with a diamond. Press {key}.", "interact")
		await get_tree().create_timer(7.0).timeout
		HUD.hide_tutorial()


func _build_room() -> void:
	# Back wall: warm timber with windows onto the night sky.
	var wall := Polygon2D.new()
	wall.polygon = PackedVector2Array([Vector2(0, 0), Vector2(ROOM_W, 0), Vector2(ROOM_W, FLOOR), Vector2(0, FLOOR)])
	wall.vertex_colors = PackedColorArray([Color(0.3, 0.2, 0.14), Color(0.3, 0.2, 0.14), Color(0.48, 0.33, 0.22), Color(0.48, 0.33, 0.22)])
	wall.z_index = -30
	world.add_child(wall)
	for x in range(0, int(ROOM_W), 180):
		var plank := Line2D.new()
		plank.points = PackedVector2Array([Vector2(x, 0), Vector2(x, FLOOR)])
		plank.width = 3.0
		plank.default_color = Color(0.22, 0.14, 0.09, 0.6)
		plank.z_index = -29
		world.add_child(plank)
	for wx in [700.0, 1900.0]:
		_window(Vector2(wx, 260))
	# Beams
	for y in [70.0, 640.0]:
		var beam := Polygon2D.new()
		beam.polygon = PackedVector2Array([Vector2(0, y), Vector2(ROOM_W, y), Vector2(ROOM_W, y + 34), Vector2(0, y + 34)])
		beam.color = Color(0.25, 0.16, 0.1)
		beam.z_index = -25
		world.add_child(beam)
	# Floor
	var floor_poly := Polygon2D.new()
	floor_poly.polygon = PackedVector2Array([Vector2(0, FLOOR), Vector2(ROOM_W, FLOOR), Vector2(ROOM_W, 1080), Vector2(0, 1080)])
	floor_poly.color = Color(0.36, 0.24, 0.15)
	floor_poly.z_index = 2
	world.add_child(floor_poly)
	for x in range(0, int(ROOM_W), 140):
		var seam := Line2D.new()
		seam.points = PackedVector2Array([Vector2(x, FLOOR), Vector2(x - 40, 1080)])
		seam.width = 2.0
		seam.default_color = Color(0.22, 0.14, 0.08)
		seam.z_index = 3
		world.add_child(seam)
	var body := StaticBody2D.new()
	var shape := CollisionShape2D.new()
	var rect := RectangleShape2D.new()
	rect.size = Vector2(ROOM_W, 200)
	shape.shape = rect
	shape.position = Vector2(ROOM_W * 0.5, FLOOR + 100)
	body.add_child(shape)
	world.add_child(body)
	add_wall(60, -200, 1200)
	add_wall(ROOM_W - 60, -200, 1200)


func _window(center: Vector2) -> void:
	var frame := Polygon2D.new()
	frame.polygon = PackedVector2Array([Vector2(-130, -150), Vector2(130, -150), Vector2(130, 150), Vector2(-130, 150)])
	frame.color = Color(0.2, 0.12, 0.07)
	frame.position = center
	frame.z_index = -28
	world.add_child(frame)
	var glass := Polygon2D.new()
	glass.polygon = PackedVector2Array([Vector2(-114, -134), Vector2(114, -134), Vector2(114, 134), Vector2(-114, 134)])
	glass.vertex_colors = PackedColorArray([Color(0.08, 0.1, 0.24), Color(0.08, 0.1, 0.24), Color(0.2, 0.26, 0.45), Color(0.2, 0.26, 0.45)])
	glass.position = center
	glass.z_index = -27
	world.add_child(glass)
	var rng := RandomNumberGenerator.new()
	rng.seed = int(center.x)
	for i in 14:
		var star := Polygon2D.new()
		var p := Vector2(rng.randf_range(-105, 105), rng.randf_range(-125, 40))
		star.polygon = PackedVector2Array([p + Vector2(0, -2), p + Vector2(2, 0), p + Vector2(0, 2), p + Vector2(-2, 0)])
		star.color = Color(1, 1, 0.9, rng.randf_range(0.5, 1.0))
		star.position = center
		star.z_index = -26
		world.add_child(star)
	for line in [[Vector2(0, -134), Vector2(0, 134)], [Vector2(-114, 0), Vector2(114, 0)]]:
		var bar := Line2D.new()
		bar.points = PackedVector2Array(line)
		bar.width = 8.0
		bar.default_color = Color(0.2, 0.12, 0.07)
		bar.position = center
		bar.z_index = -25
		world.add_child(bar)


func _framed(texture_path: String, center: Vector2, height: float, z := -20) -> Sprite2D:
	var t: Texture2D = load(texture_path)
	var sc := height / t.get_height()
	var w := t.get_width() * sc
	var frame := Polygon2D.new()
	var m := 14.0
	frame.polygon = PackedVector2Array([Vector2(-w / 2 - m, -height / 2 - m), Vector2(w / 2 + m, -height / 2 - m),
		Vector2(w / 2 + m, height / 2 + m), Vector2(-w / 2 - m, height / 2 + m)])
	frame.color = Color(0.55, 0.38, 0.16)
	frame.position = center
	frame.z_index = z
	world.add_child(frame)
	var s := Sprite2D.new()
	s.texture = t
	s.scale = Vector2(sc, sc)
	s.position = center
	s.z_index = z + 1
	world.add_child(s)
	return s


func _build_props() -> void:
	# Elias's own atlas of Brindle Isle hangs on the wall.
	_framed("res://assets/ui/brindle_atlas.jpg", Vector2(1230, 330), 330)
	# Portrait of Elias
	var bg := Polygon2D.new()
	bg.polygon = PackedVector2Array([Vector2(-95, -120), Vector2(95, -120), Vector2(95, 120), Vector2(-95, 120)])
	bg.color = Color(0.85, 0.78, 0.62)
	bg.position = Vector2(2250, 330)
	bg.z_index = -21
	world.add_child(bg)
	_framed("res://assets/portraits/elias_portrait.png", Vector2(2250, 330), 230)
	add_prop("workshop/bookshelf_4x.png", Vector2(420, FLOOR + 4), 430, 0)
	add_prop("workshop/bookshelf_4x.png", Vector2(2420, FLOOR + 4), 430, 0, true)
	add_prop("workshop/desk_4x.png", Vector2(1560, FLOOR + 4), 170, 0)
	add_prop("workshop/armillary_large_4x.png", Vector2(980, FLOOR + 4), 330, 0)
	add_prop("workshop/chest_4x.png", Vector2(1850, FLOOR + 4), 150, 0)
	add_prop("workshop/lantern_4x.png", Vector2(620, FLOOR + 4), 220, 0)
	add_prop("workshop/lantern_b_4x.png", Vector2(2060, FLOOR + 4), 220, 0)
	for x in [620.0, 2060.0, 1300.0]:
		var glow := Sprite2D.new()
		glow.texture = preload("res://scripts/world/fx.gd").glow_texture()
		glow.modulate = Color(1.0, 0.75, 0.4, 0.35)
		glow.scale = Vector2(6, 6)
		glow.position = Vector2(x, FLOOR - 150 if x != 1300.0 else 120)
		glow.z_index = 5
		var mat := CanvasItemMaterial.new()
		mat.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
		glow.material = mat
		world.add_child(glow)
	# Pinned sketches and notes
	var rng := RandomNumberGenerator.new()
	rng.seed = 3
	for i in 7:
		var page := Sprite2D.new()
		page.texture = preload("res://scripts/world/fx.gd").page_texture()
		page.position = Vector2(1580 + i * 46 + rng.randf_range(-6, 6), 520 + rng.randf_range(-30, 30))
		page.rotation = rng.randf_range(-0.2, 0.2)
		page.z_index = -18
		world.add_child(page)
	# The compass on the desk
	compass = Node2D.new()
	compass.position = Vector2(1600, FLOOR - 158)
	compass.z_index = 4
	var case_ := Polygon2D.new()
	var pts := PackedVector2Array()
	for i in 24:
		pts.append(Vector2(cos(TAU * i / 24.0), sin(TAU * i / 24.0)) * 18.0)
	case_.polygon = pts
	case_.color = Color(0.8, 0.6, 0.25)
	compass.add_child(case_)
	var needle := Polygon2D.new()
	needle.name = "Needle"
	needle.polygon = PackedVector2Array([Vector2(0, -15), Vector2(4, 0), Vector2(0, 15), Vector2(-4, 0)])
	needle.color = Color(0.3, 0.6, 0.9)
	compass.add_child(needle)
	world.add_child(compass)
	# Hidden compartment (revealed later)
	compartment = Node2D.new()
	compartment.position = Vector2(1400, FLOOR)
	compartment.z_index = 4
	var hole := Polygon2D.new()
	hole.polygon = PackedVector2Array([Vector2(-140, 2), Vector2(140, 2), Vector2(130, 40), Vector2(-130, 40)])
	hole.color = Color(0.1, 0.06, 0.04)
	compartment.add_child(hole)
	var glider := Polygon2D.new()
	glider.polygon = PackedVector2Array([Vector2(-120, 12), Vector2(0, 4), Vector2(120, 12), Vector2(0, 22)])
	glider.color = Color(0.9, 0.84, 0.7)
	compartment.add_child(glider)
	var brass := Line2D.new()
	brass.points = PackedVector2Array([Vector2(-120, 12), Vector2(0, 4), Vector2(120, 12)])
	brass.width = 4.0
	brass.default_color = Color(0.85, 0.65, 0.3)
	compartment.add_child(brass)
	compartment.visible = GameState.has_flag("compartment_open")
	world.add_child(compartment)
	_gust = CPUParticles2D.new()
	_gust.position = Vector2(700, 400)
	_gust.amount = 80
	_gust.lifetime = 2.0
	_gust.one_shot = true
	_gust.emitting = false
	_gust.explosiveness = 0.3
	_gust.emission_shape = CPUParticles2D.EMISSION_SHAPE_RECTANGLE
	_gust.emission_rect_extents = Vector2(40, 260)
	_gust.direction = Vector2(1, 0)
	_gust.spread = 15.0
	_gust.initial_velocity_min = 500.0
	_gust.initial_velocity_max = 800.0
	_gust.gravity = Vector2.ZERO
	_gust.scale_amount_min = 2.0
	_gust.scale_amount_max = 5.0
	_gust.color = Color(0.85, 0.95, 1.0, 0.6)
	_gust.z_index = 8
	world.add_child(_gust)


func _build_interactions() -> void:
	add_door("door", Vector2(200, FLOOR), "Go outside", [
		{"if": "compass_active", "do": [{"event": "leave"}]},
		{"dialogue": "workshop_leave_night", "repeat": true},
	])
	add_inspect("maps", Vector2(1230, FLOOR), "Study the maps", [
		{"if": "!searched_maps", "dialogue": "inspect_maps"},
	], Vector2(260, 220))
	add_inspect("sketches", Vector2(1720, FLOOR), "Look at the sketches", [
		{"if": "!searched_sketches", "dialogue": "inspect_sketches"},
	], Vector2(200, 220))
	add_inspect("notes", Vector2(420, FLOOR), "Read the weather logs", [
		{"if": "!searched_notes", "dialogue": "inspect_notes"},
		{"dialogue": "inspect_shelf", "repeat": true},
	], Vector2(220, 220))
	add_inspect("portrait", Vector2(2250, FLOOR), "Look at the portrait", [
		{"dialogue": "inspect_portrait", "repeat": true},
	], Vector2(200, 220))
	add_inspect("instruments", Vector2(980, FLOOR), "Examine the instruments", [
		{"dialogue": "inspect_instruments", "repeat": true},
	], Vector2(200, 220))
	add_inspect("floorboard", Vector2(1400, FLOOR), "Lift the floorboard", [
		{"if": "!compartment_open", "dialogue": "compartment"},
		{"if": ["compartment_open", "!compass_active"], "dialogue": "final_entry"},
	], Vector2(240, 160), "obj:hidden_workshop:search")


func _on_flag_changed(flag: String, value: bool) -> void:
	if flag == "compartment_open" and value:
		AudioManager.play_sfx("compartment")
		compartment.visible = true
	if flag in ["searched_maps", "searched_sketches", "searched_notes"] and GameState.objective_done("hidden_workshop", "search") \
			and not GameState.has_flag("search_done_said"):
		GameState.set_flag("search_done_said")
		await get_tree().create_timer(0.3).timeout
		while DialogueUI.active:
			await get_tree().process_frame
		await DialogueUI.play("search_done")


func _on_story_event(event_name: String) -> void:
	match event_name:
		"compass_awakens":
			AudioManager.play_sfx("gust")
			_gust.restart()
			_gust.emitting = true
			AudioManager.play_sfx("compass")
			var needle: Node2D = compass.get_node("Needle")
			var tw := create_tween()
			tw.tween_property(needle, "rotation", TAU * 2.0 + 1.2, 2.2).set_trans(Tween.TRANS_ELASTIC)
			await get_tree().create_timer(0.4).timeout
			await DialogueUI.play("compass_awakens")
		"next_morning":
			HUD.banner("Chapter 2 complete", "An impossible wind current appears on the map.", 2.5)
			await get_tree().create_timer(3.2).timeout
			GameState.chapter = 3
			GameState.set_time_of_day("dawn")
			GameState.start_quest("into_the_clouds")
			GameState.player_position = Vector2(8740, 820)
			Router.go("res://scenes/world/windrest.tscn", "workshop_door")
		"leave":
			Router.go("res://scenes/world/windrest.tscn", "workshop_door")
