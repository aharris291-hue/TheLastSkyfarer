extends Level
## Brindle Isle exterior: Cloud Edge → Whispermill Fields → Windrest Village →
## Skywatch Point → Upper Cliffs → Old Cartographer's Bluff → the open sky.
##
## Laid out west-to-east as on the Windrest Village map (the Bluff is on the
## east side, facing the prevailing winds). Chapter 1 begins at the workshop.

const GROUND := 900.0
const BLUFF := 820.0
const EDGE_X := 10060.0

var edge_wall: StaticBody2D
var glider_prop: Node2D
var fog_layer: CanvasLayer
var fog_rect: ColorRect


func build() -> void:
	level_id = "windrest"
	music = "windrest"
	bounds = Rect2(0, -700, 18400, 1900)
	death_y = 1500.0
	spawns = {
		"default": Vector2(9060, BLUFF),
		"workshop_door": Vector2(8740, BLUFF),
		"bluff_edge": Vector2(9700, BLUFF),
	}
	_build_backdrop()
	_build_cloud_edge()
	_build_fields()
	_build_village()
	_build_skywatch()
	_build_upper_cliffs()
	_build_bluff()
	_build_sky_route()


# --- Backdrop -------------------------------------------------------------------

func _build_backdrop() -> void:
	# Distant floating islands drift in a parallax layer behind everything.
	var far := Parallax2D.new()
	far.scroll_scale = Vector2(0.18, 0.4)
	far.z_index = -20
	far.texture_filter = CanvasItem.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS
	world.add_child(far)
	var rng := RandomNumberGenerator.new()
	rng.seed = 42
	for i in 26:
		var s := Sprite2D.new()
		var choice: String = ["brindle/brindle_03_4x.png", "brindle/brindle_05_4x.png", "brindle/brindle_04_4x.png"][i % 3]
		s.texture = tex(choice)
		var sc := rng.randf_range(0.25, 0.7)
		s.scale = Vector2(sc, sc)
		s.position = Vector2(i * 720.0 + rng.randf_range(-200, 200), rng.randf_range(80, 520))
		s.modulate = Color(0.75, 0.82, 0.95, rng.randf_range(0.45, 0.75))
		far.add_child(s)
		# Distant islands bob slowly on the wind.
		var bob := s.create_tween().set_loops().set_trans(Tween.TRANS_SINE)
		var dy := rng.randf_range(8.0, 18.0)
		var period := rng.randf_range(4.0, 7.0)
		bob.tween_property(s, "position:y", dy, period).as_relative()
		bob.tween_property(s, "position:y", -dy, period).as_relative()
	_build_clouds()
	# Soft painted hills in two hazy layers (the Brindle Isle interior).
	_hills(0.5, 520.0, 230.0, Color(0.55, 0.7, 0.62), Color(0.75, 0.84, 0.86, 0.0), 11)
	_hills(0.7, 640.0, 200.0, Color(0.42, 0.6, 0.42), Color(0.62, 0.74, 0.7, 0.0), 23)


func _build_clouds() -> void:
	# Two bands of soft clouds that drift on the wind, looping forever.
	for band in [[0.12, 0.3, 160.0, -9.0, 0.55], [0.3, 0.55, 330.0, -18.0, 0.8]]:
		var layer := Parallax2D.new()
		layer.scroll_scale = Vector2(band[0], band[1])
		layer.repeat_size = Vector2(5200, 0)
		layer.repeat_times = 3
		layer.autoscroll = Vector2(band[3], 0)
		layer.z_index = -18 if band[0] < 0.2 else -16
		world.add_child(layer)
		var rng := RandomNumberGenerator.new()
		rng.seed = int(band[2])
		for i in 7:
			var c := Sprite2D.new()
			c.texture = tex("res://assets/environments/fx/cloud_%d.png" % (i % 3))
			var sc: float = rng.randf_range(0.5, 1.0) * float(band[4])
			c.scale = Vector2(sc, sc * rng.randf_range(0.8, 1.0))
			c.position = Vector2(i * 740.0 + rng.randf_range(-120, 120), band[2] + rng.randf_range(-90, 90))
			c.modulate.a = rng.randf_range(0.55, 0.9)
			c.flip_h = rng.randf() < 0.5
			layer.add_child(c)


## Leaves (and a few petals in the village) carried along by the wind.
func _add_wind_motes(x0: float, x1: float, petals := false) -> void:
	var p := CPUParticles2D.new()
	p.texture = tex("res://assets/environments/fx/petal.png" if petals else "res://assets/environments/fx/leaf.png")
	p.amount = int((x1 - x0) / 140.0)
	p.lifetime = 9.0
	p.preprocess = 9.0
	p.emission_shape = CPUParticles2D.EMISSION_SHAPE_RECTANGLE
	p.emission_rect_extents = Vector2((x1 - x0) * 0.5, 260)
	p.position = Vector2((x0 + x1) * 0.5, GROUND - 420)
	p.direction = Vector2(-1, 0.15)
	p.spread = 25.0
	p.gravity = Vector2(0, 14)
	p.initial_velocity_min = 40.0
	p.initial_velocity_max = 90.0
	p.angular_velocity_min = -120.0
	p.angular_velocity_max = 120.0
	p.angle_min = 0.0
	p.angle_max = 360.0
	p.scale_amount_min = 0.7
	p.scale_amount_max = 1.2
	var fade := Gradient.new()
	fade.set_color(0, Color(1, 1, 1, 0))
	fade.set_color(1, Color(1, 1, 1, 0))
	fade.add_point(0.15, Color(1, 1, 1, 0.95))
	fade.add_point(0.85, Color(1, 1, 1, 0.95))
	p.color_ramp = fade
	p.z_index = 4
	world.add_child(p)


func _hills(scroll: float, base_y: float, amp: float, top_col: Color, bottom_col: Color, seed_: int) -> void:
	var layer := Parallax2D.new()
	layer.scroll_scale = Vector2(scroll, 0.85)
	layer.z_index = -14 if scroll < 0.6 else -12
	layer.texture_filter = CanvasItem.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS
	world.add_child(layer)
	var rng := RandomNumberGenerator.new()
	rng.seed = seed_
	# Hills only behind the island itself; they drop away before the open sky.
	var width := EDGE_X * scroll + 960.0 * (1.0 - scroll) + 600.0
	var pts := PackedVector2Array()
	var cols := PackedColorArray()
	var x := -500.0
	var phase := rng.randf() * 10.0
	while x <= width:
		var y := base_y - amp * (0.55 + 0.25 * sin(x * 0.0011 + phase) + 0.2 * sin(x * 0.0037 + phase * 2.0))
		y += maxf(0.0, x - (width - 900.0)) * 0.45     # slope down at the east end
		pts.append(Vector2(x, y))
		# ...and fade out there, so the end of the hills never shows an edge.
		cols.append(Color(top_col, clampf((width - x) / 900.0, 0.0, 1.0)))
		x += 60.0
	pts.append(Vector2(width, base_y + 700))
	cols.append(bottom_col)
	pts.append(Vector2(-500, base_y + 700))
	cols.append(top_col)    # opaque; the solid body below continues it
	var poly := Polygon2D.new()
	poly.polygon = pts
	poly.vertex_colors = cols
	layer.add_child(poly)
	# Solid ground colour below the hills, behind the island only, so no sky
	# shows between the hills and the village. It fades out sideways before
	# the hills slope away at the east end.
	var solid := top_col
	var clear := Color(solid, 0.0)
	var y0 := base_y
	var y1 := base_y + 900.0
	var xe := width - 1100.0
	var body := Polygon2D.new()
	body.polygon = PackedVector2Array([Vector2(-500, y0), Vector2(xe, y0), Vector2(xe, y1), Vector2(-500, y1)])
	body.color = solid
	body.z_index = -1
	layer.add_child(body)
	var edge := Polygon2D.new()
	edge.polygon = PackedVector2Array([Vector2(xe, y0), Vector2(xe + 400, y0), Vector2(xe + 400, y1), Vector2(xe, y1)])
	edge.vertex_colors = PackedColorArray([solid, clear, clear, solid])
	edge.z_index = -1
	layer.add_child(edge)
	# A few distant trees and windmills for scale.
	for i in int(width / 900.0):
		var px := rng.randf_range(0, width - 900.0)
		var py := base_y - amp * (0.55 + 0.25 * sin(px * 0.0011 + phase) + 0.2 * sin(px * 0.0037 + phase * 2.0))
		var windmill := rng.randf() < 0.3
		var s := make_prop_sprite("brindle/brindle_07_4x.png" if windmill else "brindle/brindle_17_4x.png")
		var hgt := (150.0 if windmill else 110.0) * (scroll + 0.3)
		s.scale = Vector2.ONE * hgt / s.texture.get_height()
		s.position = Vector2(px, py + 12)
		s.modulate = top_col.lerp(Color(1, 1, 1), 0.35)
		layer.add_child(s)


# --- Areas --------------------------------------------------------------------------

func _build_cloud_edge() -> void:
	add_ground(160, 7360, GROUND)
	_add_wind_motes(200, 3000)
	_add_wind_motes(3000, 6600, true)
	_add_wind_motes(6600, 9900)   # one continuous stretch: Cloud Edge to the Upper Cliffs
	add_wall(120)
	add_location("cloud_edge", 120, 1500)
	for x in [260, 330, 400]:
		add_prop("brindle/brindle_09_4x.png", Vector2(x, GROUND + 6), 70)
	for x in [520, 980, 1240]:
		add_prop("brindle/brindle_08_4x.png", Vector2(x, GROUND + 8), 120)
	add_prop("brindle/brindle_17_4x.png", Vector2(1380, GROUND + 10), 360, -1)
	add_trigger(Vector2(300, GROUND), Vector2(160, 300), "seen_edge_warning", null, "edge_warning")
	add_collectible("note_cloud_edge", Vector2(470, GROUND))
	add_npc("villager", "res://assets/characters/elara/elara_side.png", Vector2(760, GROUND), 182, true, [
		{"if": "item:parcel_cliffs", "dialogue": "villager_deliver"},
		{"dialogue": "villager_after", "repeat": true},
	])


func _build_fields() -> void:
	add_location("whispermill", 1560, 3000)
	for x in [1760, 2380, 2900]:
		add_prop("brindle/brindle_07_4x.png", Vector2(x, GROUND - 14), 560, -1, x == 2380, Color(0.92, 0.94, 1.0))
	add_inspect("windmill", Vector2(2380, GROUND), "Look", [{"dialogue": "windmill", "repeat": true}], Vector2(200, 220))
	for x in [1650, 1720, 1900, 1970, 2600, 2670]:
		add_prop("brindle/brindle_10_4x.png", Vector2(x, GROUND + 6), 70)
	# A crate stack to climb for Elias's note.
	add_platform(2140, GROUND - 120, 120, "brindle/brindle_11_4x.png")
	add_platform(2260, GROUND - 240, 120, "brindle/brindle_11_4x.png")
	add_prop("brindle/brindle_12_4x.png", Vector2(2140, GROUND + 4), 130)
	add_prop("brindle/brindle_12_4x.png", Vector2(2260, GROUND + 4), 130)
	add_prop("brindle/brindle_11_4x.png", Vector2(2260, GROUND - 116), 130)
	add_collectible("note_wind", Vector2(2265, GROUND - 240))


func _build_village() -> void:
	add_location("windrest", 3060, 6600)
	# Background homes (the same atlas house, varied by flip and tint).
	var homes := [[3320, false, Color(1, 0.95, 0.9)], [4060, true, Color(0.95, 0.92, 1.0)],
		[4420, false, Color(0.9, 0.95, 0.9)], [6280, true, Color(1, 1, 1)]]
	for h in homes:
		add_prop("brindle/brindle_06_4x.png", Vector2(h[0], GROUND - 14), 520, -1, h[1], h[2])
	# Windsong Tavern
	add_prop("brindle/brindle_06_4x.png", Vector2(3640, GROUND - 12), 600, -1, true, Color(1.0, 0.9, 0.78))
	add_sign("Windsong Tavern", Vector2(3640, GROUND - 330))
	add_prop("brindle/brindle_13_4x.png", Vector2(3860, GROUND + 6), 200)
	add_location("tavern", 3420, 3880)
	add_npc("tavern", "res://assets/characters/bram/bram_side.png", Vector2(3760, GROUND), 196, false, [
		{"if": "item:parcel_tavern", "dialogue": "tavern_deliver"},
		{"dialogue": "tavern_after", "repeat": true},
	])
	# Central Square: bulletin board, fountain, market stalls.
	add_prop("brindle/brindle_17_4x.png", Vector2(4560, GROUND + 10), 380, -1)
	_add_board(Vector2(4700, GROUND))
	add_inspect("board", Vector2(4700, GROUND), "Read", [{"dialogue": "board", "repeat": true}], Vector2(180, 220))
	_add_fountain(Vector2(4980, GROUND))
	add_inspect("fountain", Vector2(4980, GROUND), "Look", [{"dialogue": "fountain", "repeat": true}], Vector2(220, 200))
	add_prop("brindle/brindle_16_4x.png", Vector2(5230, GROUND + 6), 300)
	add_prop("brindle/brindle_15_4x.png", Vector2(5420, GROUND - 120), 150, -1)
	add_prop("brindle/brindle_18_4x.png", Vector2(5560, GROUND + 6), 210)
	# Post House
	add_prop("brindle/brindle_06_4x.png", Vector2(5980, GROUND - 12), 600, -1, false, Color(0.95, 0.98, 1.05))
	add_sign("Post House", Vector2(5980, GROUND - 330), 34)
	add_location("post_house", 5800, 6200)
	add_npc("maren", "res://assets/characters/maren/maren_placeholder.png", Vector2(6080, GROUND), 192, false, [
		{"if": "!obj:morning_deliveries:report", "dialogue": "maren_intro"},
		{"if": ["quest:morning_deliveries:active", "obj:morning_deliveries:tavern", "obj:morning_deliveries:tessa", "obj:morning_deliveries:cliffs"], "dialogue": "maren_return"},
		{"if": "quest:morning_deliveries:active", "dialogue": "maren_waiting", "repeat": true},
		{"if": ["quest:morning_deliveries:complete", "!deed_received"], "dialogue": "maren_deed"},
		{"dialogue": "maren_after", "repeat": true},
	])
	for x in [3200, 4280, 5700, 6480]:
		add_prop("brindle/brindle_08_4x.png", Vector2(x, GROUND + 8), 110)


func _build_skywatch() -> void:
	# A climb over the market stall and old scaffolding up to Skywatch Point.
	add_platform(5050, GROUND - 120, 110, "brindle/brindle_11_4x.png")   # crate step
	add_prop("brindle/brindle_12_4x.png", Vector2(5050, GROUND + 4), 124)
	add_platform(5230, GROUND - 236, 230, "")                         # stall roof
	add_platform(5430, GROUND - 350, 170, "brindle/platform_small_a.png")
	add_platform(5230, GROUND - 470, 170, "brindle/platform_small_b.png")
	add_platform(5470, GROUND - 590, 170, "brindle/platform_small_a.png")
	add_platform(5720, GROUND - 690, 160, "brindle/platform_small_b.png")
	# The lookout deck
	add_platform(6060, GROUND - 760, 470, "brindle/brindle_04_4x.png")
	add_prop("brindle/brindle_14_4x.png", Vector2(6230, GROUND - 760), 300)
	add_prop("brindle/brindle_15_4x.png", Vector2(5900, GROUND - 760), 150)
	add_sign("Skywatch Point", Vector2(6060, GROUND - 980), 28)
	add_location("skywatch", 5850, 6300, GROUND - 760, 600)
	add_npc("tessa", "res://assets/characters/tessa/tessa_side.png", Vector2(6150, GROUND - 760), 184, false, [
		{"if": "item:parcel_tessa", "dialogue": "tessa_deliver"},
		{"dialogue": "tessa_after", "repeat": true},
	])
	add_trigger(Vector2(5300, GROUND), Vector2(200, 300), "seen_skywatch_hint", "item:parcel_tessa", "skywatch_hint")
	# Elias Was Here: a note on a floating rock off the end of the deck.
	add_platform(6520, GROUND - 880, 150, "brindle/platform_small_b.png")
	add_collectible("note_sky_map", Vector2(6520, GROUND - 880))


func _build_upper_cliffs() -> void:
	add_ground(7340, 8060, BLUFF + 40)
	add_location("upper_cliffs", 6660, 8000)
	add_prop("brindle/brindle_17_4x.png", Vector2(7000, GROUND + 10), 420, -1)
	add_prop("brindle/brindle_03_4x.png", Vector2(7700, BLUFF + 60), 170)
	add_collectible("note_three_decades", Vector2(7800, BLUFF + 40))
	for x in [6800, 7200, 7500, 7950]:
		add_prop("brindle/brindle_08_4x.png", Vector2(x, (GROUND if x < 7360 else BLUFF + 40) + 8), 100)


func _build_bluff() -> void:
	add_ground(8040, EDGE_X, BLUFF)
	add_location("bluff", 8040, EDGE_X)
	# Elias's workshop — the atlas house with its blue roof, as on the map.
	add_prop("brindle/brindle_06_4x.png", Vector2(8700, BLUFF - 12), 620, -1, true, Color(0.95, 0.97, 1.08))
	add_sign("Workshop", Vector2(8600, BLUFF - 250), 28)
	# Observation tower
	add_prop("brindle/brindle_14_4x.png", Vector2(9330, BLUFF + 10), 760, -1, false, Color(0.9, 0.92, 1.0))
	add_prop("brindle/brindle_13_4x.png", Vector2(9100, BLUFF + 6), 190)
	add_door("workshop_door", Vector2(8740, BLUFF), "Enter workshop", [
		{"if": "!deed_received", "dialogue": "workshop_locked_ch1", "repeat": true},
		{"if": "!has_glider", "do": [{"event": "enter_workshop"}]},
	])
	edge_wall = add_wall(EDGE_X - 70)
	add_trigger(Vector2(EDGE_X - 160, BLUFF), Vector2(140, 300), "", "!piko_joined", "edge_warning")
	# The glider waiting at the edge on the morning of Chapter 3, with Piko on it.
	glider_prop = _make_glider()
	glider_prop.position = Vector2(9820, BLUFF)
	glider_prop.visible = GameState.has_flag("compass_active")
	world.add_child(glider_prop)
	add_inspect("glider", Vector2(9820, BLUFF), "Approach", [
		{"if": ["compass_active", "!piko_joined"], "dialogue": "piko_meeting"},
	], Vector2(260, 200), "compass_active")
	add_trigger(Vector2(9700, BLUFF), Vector2(200, 300), "seen_launch_ready", "piko_joined", "launch_ready")


func _build_sky_route() -> void:
	add_location("open_sky", EDGE_X + 200, 18400)
	# Islands double as checkpoints.
	_island(Vector2(12050, 780), 470, "brindle/brindle_04_4x.png")
	add_collectible("note_each_island", Vector2(12120, 780))
	_island(Vector2(14450, 560), 420, "brindle/brindle_04_4x.png")
	_island(Vector2(16500, 640), 260, "brindle/platform_small_a.png")
	add_updraft(Vector2(11000, 1450), Vector2(280, 1000))
	add_updraft(Vector2(12950, 1450), Vector2(300, 1150), true, "revealed_wind_1")
	add_updraft(Vector2(15350, 1450), Vector2(300, 1100))
	# Decorative small rocks along the route
	var rocks := [[10600, 520, 0.5], [11600, 300, 0.4], [13600, 260, 0.55], [15900, 330, 0.45], [17000, 820, 0.6]]
	for r in rocks:
		add_prop("brindle/brindle_03_4x.png", Vector2(r[0], r[1]), 240 * r[2] / 0.5, 0, false, Color(0.95, 0.95, 1.0))
	# The island in the mist where the wind refuses to go.
	add_prop("brindle/brindle_05_4x.png", Vector2(17950, 760), 900, -1, false, Color(0.55, 0.62, 0.75, 0.55))
	add_trigger(Vector2(16900, 1400), Vector2(240, 2400), "reached_fog", "piko_joined", "wind_refuses")
	add_wall(18200)
	fog_layer = CanvasLayer.new()
	fog_layer.layer = 5
	fog_rect = ColorRect.new()
	fog_rect.set_anchors_preset(Control.PRESET_FULL_RECT)
	fog_rect.color = Color(0.92, 0.94, 0.98, 0.0)
	fog_rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	fog_layer.add_child(fog_rect)
	add_child(fog_layer)


func _island(top_center: Vector2, width: float, texture_path: String) -> void:
	add_platform(top_center.x, top_center.y, width, texture_path)
	add_trigger(top_center, Vector2(width, 200), "", null, "", [], func(): set_checkpoint(top_center))


# --- Bespoke props ------------------------------------------------------------------

func _add_board(pos: Vector2) -> void:
	var n := Node2D.new()
	n.position = pos
	n.z_index = -1
	var post := Polygon2D.new()
	post.polygon = PackedVector2Array([Vector2(-70, 0), Vector2(-56, 0), Vector2(-56, -230), Vector2(-70, -230)])
	post.color = Color(0.35, 0.22, 0.12)
	n.add_child(post)
	var post2 := post.duplicate()
	post2.position.x = 126
	n.add_child(post2)
	var board := Polygon2D.new()
	board.polygon = PackedVector2Array([Vector2(-90, -230), Vector2(90, -230), Vector2(90, -110), Vector2(-90, -110)])
	board.color = Color(0.5, 0.33, 0.18)
	n.add_child(board)
	var rng := RandomNumberGenerator.new()
	rng.seed = 7
	for i in 5:
		var note := Polygon2D.new()
		var x := -78 + i * 32 + rng.randf_range(-4, 4)
		var y := -218 + rng.randf_range(0, 40)
		note.polygon = PackedVector2Array([Vector2(x, y), Vector2(x + 28, y + 2), Vector2(x + 26, y + 46), Vector2(x - 2, y + 44)])
		note.color = Color(0.95, 0.9, 0.75).darkened(rng.randf_range(0.0, 0.15))
		n.add_child(note)
	world.add_child(n)


func _add_fountain(pos: Vector2) -> void:
	var n := Node2D.new()
	n.position = pos
	n.z_index = -1
	var stone := Color(0.7, 0.66, 0.6)
	var dark := Color(0.32, 0.28, 0.26)
	var shapes := [
		# lower basin, rim, water, pedestal, upper bowl
		[[Vector2(-125, 4), Vector2(125, 4), Vector2(110, -58), Vector2(-110, -58)], stone.darkened(0.12)],
		[[Vector2(-136, -58), Vector2(136, -58), Vector2(128, -76), Vector2(-128, -76)], stone],
		[[Vector2(-118, -70), Vector2(118, -70), Vector2(112, -76), Vector2(-112, -76)], Color(0.55, 0.78, 0.92)],
		[[Vector2(-18, -76), Vector2(18, -76), Vector2(12, -150), Vector2(-12, -150)], stone.darkened(0.05)],
		[[Vector2(-60, -150), Vector2(60, -150), Vector2(44, -176), Vector2(-44, -176)], stone],
	]
	for sh in shapes:
		var p := Polygon2D.new()
		p.polygon = PackedVector2Array(sh[0])
		p.color = sh[1]
		n.add_child(p)
		var outline := Line2D.new()
		outline.points = PackedVector2Array(sh[0] + [sh[0][0]])
		outline.width = 3.0
		outline.default_color = dark
		n.add_child(outline)
	# Carved wind-chart lines on the basin
	for i in 5:
		var l := Line2D.new()
		var x := -90.0 + i * 45.0
		l.points = PackedVector2Array([Vector2(x, -12), Vector2(x + 18, -30), Vector2(x + 6, -46)])
		l.width = 2.0
		l.default_color = dark.lightened(0.15)
		n.add_child(l)
	var spray := CPUParticles2D.new()
	spray.position = Vector2(0, -180)
	spray.amount = 60
	spray.lifetime = 1.1
	spray.direction = Vector2(0, -1)
	spray.spread = 28.0
	spray.initial_velocity_min = 150.0
	spray.initial_velocity_max = 210.0
	spray.gravity = Vector2(0, 480)
	spray.scale_amount_min = 3.0
	spray.scale_amount_max = 6.0
	spray.color = Color(0.82, 0.94, 1.0, 0.85)
	n.add_child(spray)
	world.add_child(n)


func _make_glider() -> Node2D:
	## Placeholder glider (no concept art supplied yet): brass frame and canvas.
	var g := Node2D.new()
	g.z_index = -1
	var wing := Polygon2D.new()
	wing.polygon = PackedVector2Array([Vector2(-150, -40), Vector2(0, -78), Vector2(150, -40), Vector2(0, -52)])
	wing.color = Color(0.9, 0.84, 0.7)
	g.add_child(wing)
	var frame := Line2D.new()
	frame.points = PackedVector2Array([Vector2(-150, -40), Vector2(0, -78), Vector2(150, -40)])
	frame.width = 6.0
	frame.default_color = Color(0.78, 0.58, 0.25)
	g.add_child(frame)
	var strut := Line2D.new()
	strut.points = PackedVector2Array([Vector2(0, -78), Vector2(0, -6)])
	strut.width = 5.0
	strut.default_color = Color(0.6, 0.42, 0.18)
	g.add_child(strut)
	var stand := Polygon2D.new()
	stand.polygon = PackedVector2Array([Vector2(-40, 0), Vector2(40, 0), Vector2(30, -10), Vector2(-30, -10)])
	stand.color = Color(0.4, 0.28, 0.16)
	g.add_child(stand)
	return g


# --- Story flow ----------------------------------------------------------------------

func after_ready() -> void:
	_apply_story_state()
	if not GameState.has_flag("opening_done"):
		GameState.set_time_of_day("dawn")
		sky.apply("dawn", 0.0)
		player.facing = 1
		player.locked = true
		await get_tree().create_timer(0.8).timeout
		HUD.banner("THE LAST SKYFARER", "Chapter 1 — The Edge of Tomorrow", 3.0)
		await get_tree().create_timer(2.6).timeout
		player.locked = false
		await DialogueUI.play("opening")
		player.facing = -1
		HUD.show_tutorial("Move with A / D or the left stick.  Hold {key} to run.", "run")
		await get_tree().create_timer(6.0).timeout
		HUD.show_tutorial("Press {key} to jump.", "jump")
		await get_tree().create_timer(4.0).timeout
		HUD.hide_tutorial()
		SaveManager.autosave()
	elif GameState.has_flag("compass_active") and not GameState.has_flag("chapter3_banner"):
		GameState.set_flag("chapter3_banner")
		HUD.banner("Chapter 3", "Into the Clouds", 3.0)
		SaveManager.autosave()


func _apply_story_state() -> void:
	glider_prop.visible = GameState.has_flag("compass_active") and not GameState.has_flag("piko_joined")
	if GameState.has_flag("compass_active") and not GameState.has_flag("piko_joined"):
		_place_piko_on_glider()
	if GameState.has_flag("piko_joined") and edge_wall:
		edge_wall.queue_free()
		edge_wall = null
	if GameState.has_flag("piko_joined"):
		AudioManager.play_music("sky" if player and player.global_position.x > EDGE_X else "windrest")


var _perched_piko: Sprite2D


func _place_piko_on_glider() -> void:
	if _perched_piko:
		return
	_perched_piko = Sprite2D.new()
	_perched_piko.texture = load("res://assets/characters/piko/piko_side.png")
	_perched_piko.scale = Vector2(0.87, 0.87)
	_perched_piko.position = Vector2(9820 - 10, BLUFF - 130)
	world.add_child(_perched_piko)


func _on_story_event(event_name: String) -> void:
	match event_name:
		"sunset_fade":
			await Router.fade_through(func(): GameState.set_time_of_day("sunset"), 1.2, "Later that day...")
			sky.apply("sunset", 0.0)
			await DialogueUI.play("maren_deed")
		"enter_workshop":
			capture_state()
			GameState.player_position = spawns["workshop_door"]
			Router.go("res://scenes/world/workshop.tscn", "door")
		"piko_joins":
			if _perched_piko:
				var start := _perched_piko.global_position
				_perched_piko.queue_free()
				_perched_piko = null
				spawn_piko()
				piko.global_position = start
				piko.react("♪", "piko_trill")
			glider_prop.visible = false
			if edge_wall:
				edge_wall.queue_free()
				edge_wall = null
			GameState.set_flag("has_glider")
			HUD.show_tutorial("Jump off the edge, then hold {key} to glide. Rising wind lifts you higher.", "glide")
			await get_tree().create_timer(8.0).timeout
			HUD.hide_tutorial()
			SaveManager.autosave()
		"demo_end":
			await get_tree().create_timer(0.6).timeout
			SaveManager.autosave()
			open_menu(preload("res://scripts/ui/demo_end.gd").new())


func _on_piko_sensed(_target: Node) -> void:
	await get_tree().create_timer(0.4).timeout
	if not GameState.has_flag("seen_piko_wind"):
		GameState.set_flag("seen_piko_wind")
		DialogueUI.play("piko_found_wind")


func _process(_delta: float) -> void:
	if player == null:
		return
	var x := player.global_position.x
	# Music shifts to the sky theme once Kieran leaves the island.
	if GameState.has_flag("piko_joined"):
		AudioManager.play_music("sky" if x > EDGE_X + 100 else "windrest")
	# Fog thickens approaching the place where the wind refuses to go.
	if fog_rect:
		var f := clampf((x - 15600.0) / 1800.0, 0.0, 1.0)
		fog_rect.color.a = f * 0.55
		sky.set_fog(f * 0.6)
