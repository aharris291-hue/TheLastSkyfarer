extends MenuBase
## Shown when Kieran reaches the place where the wind refuses to go.


func _ready() -> void:
	make_backdrop(0.72)
	var b := make_panel(1000, "End of the Demo")
	var notes := GameState.collectible_count("elias_notes")
	var lines := [
		"Kieran and Piko have found where the wind refuses to go.",
		"Beyond the mist: Veilmist Isle — the island that shouldn't exist.",
		"",
		"Elias's notes found: %d / %d" % [notes.x, notes.y],
		"Time played: %s" % SaveManager.format_time(GameState.playtime),
		"",
		"Next in development: Chapter 4 — The Island That Shouldn't Exist.",
		"Thank you for playing.",
	]
	for l in lines:
		var lab := make_label(l, 30, Color(0.95, 0.9, 0.82), true)
		lab.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		b.add_child(lab)
	add_button(b, "Keep exploring", close)
	add_button(b, "Return to Title", func():
		get_tree().paused = false
		HUD.set_gameplay(false)
		Router.go("res://scenes/ui/title_screen.tscn"))
	focus_first()
