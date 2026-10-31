extends Node2D
class_name Level
## Base class for playable areas. Sets up the sky, lighting, player, camera,
## Piko and menus, and provides small builder helpers so area scripts read
## like a layout description rather than node plumbing.

const PLAYER_SCENE := preload("res://scenes/player/player.tscn")
const PikoScript := preload("res://scripts/companion/piko.gd")
const CameraScript := preload("res://scripts/player/player_camera.gd")
const PauseMenu := preload("res://scripts/ui/pause_menu.gd")
const JournalMenu := preload("res://scripts/ui/journal_menu.gd")
const ENV := "res://assets/environments/"

var level_id := "level"
var music := ""
var ambience := "wind"
var spawns := {}                     # name -> Vector2
var bounds := Rect2(0, -600, 4000, 2000)
var death_y := 1600.0
var checkpoint := Vector2.ZERO
var current_location := ""

var world: Node2D
var back_layer: Node2D               # behind the player
var front_layer: Node2D              # in front of the player
var player: Player
var piko: Node2D
var camera: Camera2D
var sky: SkyLayer
var canvas_mod: CanvasModulate
var menu_layer: CanvasLayer
var _respawning := false


func _ready() -> void:
	add_to_group("level")
	canvas_mod = CanvasModulate.new()
	add_child(canvas_mod)
	sky = SkyLayer.new()
	add_child(sky)
	world = Node2D.new()
	world.name = "World"
	add_child(world)
	back_layer = Node2D.new()
	back_layer.z_index = -5
	world.add_child(back_layer)
	front_layer = Node2D.new()
	front_layer.z_index = 10
	world.add_child(front_layer)
	menu_layer = CanvasLayer.new()
	menu_layer.layer = 60
	menu_layer.process_mode = Node.PROCESS_MODE_ALWAYS
	add_child(menu_layer)

	build()

	player = PLAYER_SCENE.instantiate()
	world.add_child(player)
	camera = CameraScript.new()
	world.add_child(camera)
	camera.target = player
	camera.set_bounds(bounds)
	_place_player()
	camera.snap()
	sky.setup(camera, canvas_mod, GameState.time_of_day)
	GameState.time_of_day_changed.connect(func(tod): sky.apply(tod))
	GameState.story_event.connect(_on_story_event)
	GameState.flag_changed.connect(_on_flag_changed)
	if GameState.has_flag("piko_joined"):
		spawn_piko()
	GameState.scene_path = scene_file_path
	HUD.set_gameplay(true)
	AudioManager.play_music(music)
	AudioManager.play_ambience(ambience, -6.0)
	after_ready()


## Override: create the area's geometry, props, NPCs and triggers.
func build() -> void:
	pass


## Override: runs after the player exists (start cutscenes etc.).
func after_ready() -> void:
	pass


func _place_player() -> void:
	var pos: Vector2 = spawns.get("default", Vector2(200, 900))
	if Router.use_saved_position and GameState.has_position and GameState.scene_path == scene_file_path:
		pos = GameState.player_position
	elif Router.pending_spawn != "" and spawns.has(Router.pending_spawn):
		pos = spawns[Router.pending_spawn]
	Router.use_saved_position = false
	Router.pending_spawn = ""
	player.global_position = pos
	checkpoint = pos
	if pos.x > bounds.get_center().x:
		player.facing = -1


func spawn_piko() -> void:
	if piko:
		return
	piko = PikoScript.new()
	world.add_child(piko)
	piko.attach(player)
	piko.sensed.connect(_on_piko_sensed)


func _on_piko_sensed(_target: Node) -> void:
	pass


func capture_state() -> void:
	GameState.scene_path = scene_file_path
	if player:
		var p := player.global_position
		if not player.is_on_floor():
			p = checkpoint
		GameState.player_position = p
		GameState.has_position = true


func location_label() -> String:
	if current_location != "" and GameState.locations_db.has(current_location):
		return GameState.locations_db[current_location]["name"]
	return "Brindle Isle"


func _physics_process(_delta: float) -> void:
	if player and player.global_position.y > death_y and not _respawning:
		respawn()


func respawn() -> void:
	_respawning = true
	player.locked = true
	var reset := func():
		player.global_position = checkpoint
		player.velocity = Vector2.ZERO
		player.gliding = false
		camera.snap()
		if piko:
			piko.global_position = checkpoint + Vector2(-80, -200)
	await Router.fade_through(reset, 0.3)
	player.locked = false
	_respawning = false
	if piko:
		piko.react("!", "piko_trill")


func set_checkpoint(pos: Vector2) -> void:
	checkpoint = pos


func _unhandled_input(event: InputEvent) -> void:
	if DialogueUI.active or Router.busy or menu_layer.get_child_count() > 0:
		return
	if player and player.locked:
		return
	if event.is_action_pressed("pause"):
		open_menu(PauseMenu.new())
	elif event.is_action_pressed("journal"):
		open_menu(JournalMenu.new())
	elif event.is_action_pressed("map"):
		var j := JournalMenu.new()
		j.start_tab = 3
		open_menu(j)


func open_menu(menu: Control) -> void:
	get_tree().paused = true
	HUD.hide_prompt()
	menu_layer.add_child(menu)
	menu.tree_exited.connect(func():
		if menu_layer.get_child_count() == 0 and is_inside_tree():
			get_tree().paused = false)


func _on_story_event(_name: String) -> void:
	pass


func _on_flag_changed(_flag: String, _value: bool) -> void:
	pass


# --- Builder helpers -----------------------------------------------------------

func tex(path: String) -> Texture2D:
	if not path.begins_with("res://"):
		path = ENV + path
	return load(path)


func add_ground(x0: float, x1: float, y: float, underbelly := 300.0) -> void:
	var body := StaticBody2D.new()
	body.collision_layer = 1
	var shape := CollisionShape2D.new()
	var rect := RectangleShape2D.new()
	rect.size = Vector2(x1 - x0, 400)
	shape.shape = rect
	shape.position = Vector2((x0 + x1) * 0.5, y + 200)
	body.add_child(shape)
	world.add_child(body)
	# Rock underside of the floating island, fading into the cloud sea below.
	var poly := Polygon2D.new()
	var pts := PackedVector2Array()
	var cols := PackedColorArray()
	var top := y + 110.0
	pts.append(Vector2(x0 + 30, top))
	pts.append(Vector2(x1 - 30, top))
	var steps := int((x1 - x0) / 120.0) + 2
	var rng := RandomNumberGenerator.new()
	rng.seed = int(x0 * 13 + x1)
	for i in range(steps, -1, -1):
		var fx := x0 + 30 + (x1 - x0 - 60) * float(i) / steps
		var depth := underbelly * (0.35 + 0.65 * sin(PI * float(i) / steps)) + rng.randf_range(-50, 50)
		pts.append(Vector2(fx, top + maxf(depth, 30.0)))
	for i in pts.size():
		var d := clampf((pts[i].y - top) / underbelly, 0.0, 1.0)
		cols.append(Color(0.33, 0.27, 0.25).lerp(Color(0.75, 0.74, 0.82, 0.0), d))
	poly.polygon = pts
	poly.vertex_colors = cols
	poly.z_index = -1
	world.add_child(poly)
	# Grass-topped rock from the Brindle Isle atlas: end caps + seamless tile.
	var h := 153.0
	var tile := TextureRect.new()
	tile.texture = tex("brindle/ground_tile.png")
	tile.stretch_mode = TextureRect.STRETCH_TILE
	tile.texture_repeat = CanvasItem.TEXTURE_REPEAT_ENABLED
	tile.position = Vector2(x0 + 100, y - 30)
	tile.size = Vector2(maxf(x1 - x0 - 200, 0), h)
	tile.mouse_filter = Control.MOUSE_FILTER_IGNORE
	tile.z_index = 1
	world.add_child(tile)
	for side in [["brindle/ground_cap_left.png", x0], ["brindle/ground_cap_right.png", x1 - 150]]:
		var cap := Sprite2D.new()
		cap.texture = tex(side[0])
		cap.centered = false
		cap.position = Vector2(side[1], y - 30)
		cap.z_index = 2
		world.add_child(cap)


func add_wall(x: float, y_top := -2000.0, y_bottom := 1600.0) -> StaticBody2D:
	var body := StaticBody2D.new()
	var shape := CollisionShape2D.new()
	var rect := RectangleShape2D.new()
	rect.size = Vector2(40, y_bottom - y_top)
	shape.shape = rect
	shape.position = Vector2(x, (y_top + y_bottom) * 0.5)
	body.add_child(shape)
	world.add_child(body)
	return body


## One-way platform. `top` is the walkable surface height.
func add_platform(x: float, top: float, width: float, texture_path := "brindle/platform_small_a.png",
		visual_scale := 3.0, sink := 18.0) -> StaticBody2D:
	var body := StaticBody2D.new()
	var shape := CollisionShape2D.new()
	var rect := RectangleShape2D.new()
	rect.size = Vector2(width, 20)
	shape.shape = rect
	shape.one_way_collision = true
	shape.position = Vector2(x, top + 10)
	body.add_child(shape)
	world.add_child(body)
	if texture_path != "":
		var s := Sprite2D.new()
		s.texture = tex(texture_path)
		var sc := width / s.texture.get_width()
		if visual_scale > 0:
			sc = maxf(sc, 0.0)
		s.scale = Vector2(sc, sc)
		s.centered = false
		s.position = Vector2(x - width * 0.5, top - sink * sc / 3.0)
		s.z_index = 1
		body.add_child(s)
	return body


func add_prop(texture_path: String, pos: Vector2, height: float, layer := 0, flip := false,
		tint := Color.WHITE) -> Sprite2D:
	## pos is the bottom-centre of the prop. layer: -1 back, 0 world, 1 front.
	var s := Sprite2D.new()
	s.texture = tex(texture_path)
	var sc := height / s.texture.get_height()
	s.scale = Vector2(sc, sc)
	s.centered = true
	s.offset = Vector2(0, -s.texture.get_height() * 0.5)
	s.position = pos
	s.flip_h = flip
	s.modulate = tint
	match layer:
		-1:
			back_layer.add_child(s)
		1:
			front_layer.add_child(s)
		_:
			s.z_index = -1
			world.add_child(s)
	return s


func add_sign(text: String, pos: Vector2, size := 30) -> void:
	var panel := PanelContainer.new()
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0.36, 0.24, 0.14)
	sb.border_color = Color(0.2, 0.12, 0.06)
	sb.set_border_width_all(4)
	sb.set_corner_radius_all(6)
	sb.content_margin_left = 16
	sb.content_margin_right = 16
	sb.content_margin_top = 6
	sb.content_margin_bottom = 6
	panel.add_theme_stylebox_override("panel", sb)
	var l := Label.new()
	l.text = text
	l.add_theme_font_override("font", load("res://assets/ui/fonts/LiberationSerif-Bold.ttf"))
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", Color(1.0, 0.9, 0.7))
	panel.add_child(l)
	panel.position = pos
	panel.z_index = -1
	panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	world.add_child(panel)
	await get_tree().process_frame
	panel.position.x = pos.x - panel.size.x * 0.5


func add_npc(id: String, texture_path: String, pos: Vector2, height: float, faces_right: bool,
		rules: Array) -> NPC:
	var n := NPC.new()
	n.name = id
	n.texture = load(texture_path)
	n.sprite_height = height
	n.faces_right = faces_right
	n.rules = rules
	n.position = pos
	world.add_child(n)
	return n


func add_inspect(id: String, pos: Vector2, prompt: String, rules: Array, size := Vector2(150, 200),
		available_if = null) -> Interactable:
	var i := Interactable.new()
	i.name = id
	i.prompt = prompt
	i.size = size
	i.rules = rules
	i.available_if = available_if
	i.position = pos
	world.add_child(i)
	return i


func add_trigger(pos: Vector2, size: Vector2, once_flag: String, condition = null,
		dialogue := "", actions := [], callback := Callable()) -> TriggerZone:
	var t := TriggerZone.new()
	t.size = size
	t.once_flag = once_flag
	t.once = once_flag != ""
	t.condition = condition
	t.dialogue = dialogue
	t.actions = actions
	t.callback = callback
	t.position = pos
	world.add_child(t)
	return t


func add_location(id: String, x0: float, x1: float, y := 1000.0, height := 3000.0) -> void:
	var t := TriggerZone.new()
	t.size = Vector2(x1 - x0, height)
	t.once = false
	t.position = Vector2((x0 + x1) * 0.5, y)
	t.callback = func():
		current_location = id
		if not id in GameState.discovered:
			GameState.discover(id)
			var loc: Dictionary = GameState.locations_db[id]
			HUD.banner(loc["name"], loc.get("subtitle", ""))
	world.add_child(t)


func add_collectible(journal_id: String, pos: Vector2) -> Collectible:
	var c := Collectible.new()
	c.journal_id = journal_id
	c.position = pos
	world.add_child(c)
	c.interacted.connect(func(_b):
		if GameState.journal_db.get(journal_id, {}).get("collectible", "") == "elias_notes":
			GameState.advance_objective("elias_was_here", "notes"))
	return c


func add_updraft(pos: Vector2, size: Vector2, hidden := false, reveal_flag := "") -> Updraft:
	var u := Updraft.new()
	u.size = size
	u.concealed = hidden
	u.reveal_flag = reveal_flag
	u.position = pos
	if hidden:
		u.add_to_group("piko_sense")
	world.add_child(u)
	return u


func add_door(id: String, pos: Vector2, prompt: String, rules: Array) -> Interactable:
	return add_inspect(id, pos, prompt, rules, Vector2(160, 240))
