extends RefCounted
## Small procedurally generated textures shared by world objects.

static var _glow: Texture2D
static var _page: Texture2D


static func glow_texture() -> Texture2D:
	if _glow == null:
		var g := GradientTexture2D.new()
		g.fill = GradientTexture2D.FILL_RADIAL
		g.fill_from = Vector2(0.5, 0.5)
		g.fill_to = Vector2(1.0, 0.5)
		g.width = 128
		g.height = 128
		var grad := Gradient.new()
		grad.set_color(0, Color(1, 1, 1, 0.9))
		grad.set_color(1, Color(1, 1, 1, 0.0))
		g.gradient = grad
		_glow = g
	return _glow


static func page_texture() -> Texture2D:
	if _page == null:
		var img := Image.create(44, 56, false, Image.FORMAT_RGBA8)
		img.fill(Color(0.96, 0.9, 0.75))
		for y in range(10, 50, 7):
			for x in range(6, 38):
				img.set_pixel(x, y, Color(0.45, 0.35, 0.25, 0.8))
		for x in 44:
			img.set_pixel(x, 0, Color(0.5, 0.38, 0.22))
			img.set_pixel(x, 55, Color(0.5, 0.38, 0.22))
		for y in 56:
			img.set_pixel(0, y, Color(0.5, 0.38, 0.22))
			img.set_pixel(43, y, Color(0.5, 0.38, 0.22))
		_page = ImageTexture.create_from_image(img)
	return _page
