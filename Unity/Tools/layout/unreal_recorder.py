# Recording stand-in for the Unreal Python API: lets build_brindle_greybox.py run outside Unreal and records what it places.
RECORD = []

class Any:
    def __init__(self, *a, **k): pass
    def __getattr__(self, n): return Any()
    def __call__(self, *a, **k): return Any()
    def __iter__(self): return iter(())
    def __bool__(self): return True

class Member(str):
    def __call__(self, *a, **k): return Any()
    def __getattr__(self, n): return Member(n)

class ClassRef:
    def __init__(self, name): self.name = name
    def __getattr__(self, n): return Member(n)
    def __call__(self, *a, **k): return Any()
    def static_class(self): return self.name

class Vector(tuple):
    def __new__(cls, x=0.0, y=0.0, z=0.0): return tuple.__new__(cls, (x, y, z))

def Rotator(roll=0.0, pitch=0.0, yaw=0.0): return {"pitch": pitch, "yaw": yaw, "roll": roll}
def LinearColor(*a): return list(a)
def Text(t): return t
def load_asset(path): return Member(path.split("/")[-1].split(".")[0])

class Comp:
    def __init__(self, actor): self.actor = actor
    def set_static_mesh(self, m): self.actor.d["mesh"] = str(m)
    def set_material(self, i, m): self.actor.d["material"] = str(m)
    def set_collision_enabled(self, c): self.actor.d["collision"] = False
    def set_cast_shadow(self, s): self.actor.d["shadow"] = bool(s)
    def set_editor_property(self, n, v):
        if n == "ld_max_draw_distance": self.actor.d["cull"] = v / 100.0
        else: self.actor.d.setdefault("props", {})[n] = v if isinstance(v, (int, float, str, bool)) else str(v)
    def set_box_extent(self, e): self.actor.d["extent"] = list(e)
    def __getattr__(self, n): return Any()

class Spline:
    def __init__(self, actor): self.actor = actor
    def add_spline_point(self, p, *a): self.actor.d.setdefault("points", []).append([c / 100.0 for c in p])
    def __getattr__(self, n): return Any()

class Actor:
    def __init__(self, cls, loc, rot):
        self.d = {"class": getattr(cls, "name", str(cls)), "loc": [c / 100.0 for c in loc], "rot": rot or {"pitch": 0, "yaw": 0, "roll": 0},
                  "scale": [1.0, 1.0, 1.0], "hidden": False, "collision": True, "tags": []}
        self.comp = Comp(self)
        RECORD.append(self.d)
    def set_actor_label(self, l): self.d["label"] = l
    def set_folder_path(self, f): self.d["folder"] = f
    def set_actor_scale3d(self, s): self.d["scale"] = list(s)
    def set_actor_hidden_in_game(self, h): self.d["hidden"] = bool(h)
    def set_actor_enable_collision(self, c): self.d["collision"] = bool(c)
    def set_editor_property(self, n, v):
        if isinstance(v, (int, float, str, bool)): self.d.setdefault("props", {})[n] = v
    def get_editor_property(self, n): return self.comp
    def get_component_by_class(self, c): return Spline(self)
    @property
    def static_mesh_component(self): return self.comp
    @property
    def tags(self): return self.d["tags"]
    @tags.setter
    def tags(self, t): self.d["tags"] = [str(x) for x in t]
    def __getattr__(self, n): return Any()

class _Actors:
    def spawn_actor_from_class(self, cls, loc, rot=None): return Actor(cls, loc, rot)
    def __getattr__(self, n): return Any()

class _Levels:
    def new_level(self, *a): return True
    def save_current_level(self): return True
    def __getattr__(self, n): return Any()

def get_editor_subsystem(cls):
    return _Actors() if getattr(cls, "name", "") == "EditorActorSubsystem" else _Levels()

class EditorAssetLibrary:
    @staticmethod
    def does_asset_exist(p): return False
    @staticmethod
    def delete_asset(p): return True

def log(*a): pass
def log_warning(*a): pass

def __getattr__(name): return ClassRef(name)
