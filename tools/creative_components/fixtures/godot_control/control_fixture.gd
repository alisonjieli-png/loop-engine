extends Node3D

var ship: CharacterBody3D
var tick: int = 0
var stopped: bool = false

func box(size: Vector3, color: Color, point: Vector3) -> MeshInstance3D:
    var result := MeshInstance3D.new()
    var mesh := BoxMesh.new()
    mesh.size = size
    var material := StandardMaterial3D.new()
    material.albedo_color = color
    material.roughness = 0.65
    mesh.material = material
    result.mesh = mesh
    result.position = point
    return result

func _ready() -> void:
    InputMap.add_action("fixture_forward")
    add_child(box(Vector3(18, 0.2, 10), Color(0.07, 0.12, 0.18), Vector3(4, -1.2, 0)))
    var wall := StaticBody3D.new()
    wall.position = Vector3(4, 0, 0)
    add_child(wall)
    var shape := BoxShape3D.new()
    shape.size = Vector3(0.4, 3, 4)
    var collision := CollisionShape3D.new()
    collision.shape = shape
    if not OS.get_cmdline_user_args().has("--broken-wall"):
        wall.add_child(collision)
    else:
        collision.free()
    wall.add_child(box(shape.size, Color(0.92, 0.35, 0.15), Vector3.ZERO))
    ship = CharacterBody3D.new()
    ship.motion_mode = CharacterBody3D.MOTION_MODE_FLOATING
    add_child(ship)
    var ship_shape := BoxShape3D.new()
    ship_shape.size = Vector3(1.2, 0.3, 1.5)
    var ship_collision := CollisionShape3D.new()
    ship_collision.shape = ship_shape
    ship.add_child(ship_collision)
    ship.add_child(box(Vector3(1.2, 0.3, 0.5), Color(0.1, 0.75, 0.95), Vector3.ZERO))
    ship.add_child(box(Vector3(0.4, 0.1, 1.5), Color(0.6, 0.85, 1), Vector3(-0.15, 0, 0)))
    var light := DirectionalLight3D.new()
    light.rotation_degrees = Vector3(-55, -25, 0)
    light.light_energy = 1.8
    add_child(light)
    var environment := WorldEnvironment.new()
    environment.environment = Environment.new()
    environment.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
    environment.environment.ambient_light_color = Color(0.55, 0.65, 0.8)
    environment.environment.ambient_light_energy = 0.7
    add_child(environment)
    var camera := Camera3D.new()
    camera.position = Vector3(-5, 6, 10)
    add_child(camera)
    camera.look_at(Vector3(3, 0, 0))
    camera.current = true
    Input.action_press("fixture_forward")

func _physics_process(_delta: float) -> void:
    if stopped:
        return
    ship.velocity = Vector3(5, 0, 0) if Input.is_action_pressed("fixture_forward") else Vector3.ZERO
    ship.move_and_slide()
    tick += 1
    if tick == 120:
        stopped = true
        Input.action_release("fixture_forward")
        finish.call_deferred()

func finish() -> void:
    var headless := DisplayServer.get_name() == "headless"
    var captured := false
    if not headless:
        await RenderingServer.frame_post_draw
        captured = get_viewport().get_texture().get_image().save_png("res://capture.png") == OK
    var passed := absf(ship.position.x - 3.2) < 0.02
    var result := {
        "record_type": "baltor_game_control_fixture/v1",
        "engine_version": Engine.get_version_info().string,
        "ticks": tick,
        "input_injected": true,
        "position": [ship.position.x, ship.position.y, ship.position.z],
        "collision_assertion_passed": passed,
        "headless": headless,
        "frame_captured": captured,
        "rendering_method": RenderingServer.get_current_rendering_method(),
        "qualification": "first_party_fixture_only"
    }
    var run_name := "negative" if OS.get_cmdline_user_args().has("--broken-wall") else ("headless" if headless else "render")
    var stream := FileAccess.open("res://%s-result.json" % run_name, FileAccess.WRITE)
    stream.store_string(JSON.stringify(result, "  "))
    stream.close()
    print(JSON.stringify(result))
    get_tree().quit(0 if passed and (headless or captured) else 1)
