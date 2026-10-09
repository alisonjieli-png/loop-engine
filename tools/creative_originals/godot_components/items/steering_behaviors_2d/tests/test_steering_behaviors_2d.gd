extends "../baltor_test.gd"
## Tests for BaltorSteering: seek and flee forces, the panic distance, arriving and stopping, pursuit lead, the
## integrator's limits and repeatable wander.

const Subject := preload("../steering_behaviors_2d.gd")


func test_seek_and_flee_point_the_right_way() -> void:
	assert_eq(Subject.seek(Vector2.ZERO, Vector2.ZERO, Vector2(10, 0), 5.0), Vector2(5, 0))
	assert_eq(Subject.seek(Vector2.ZERO, Vector2(0, 5), Vector2(10, 0), 5.0), Vector2(5, -5))
	assert_eq(Subject.flee(Vector2.ZERO, Vector2.ZERO, Vector2(3, 0), 4.0), Vector2(-4, 0))
	assert_eq(Subject.flee(Vector2.ZERO, Vector2.ZERO, Vector2(30, 0), 4.0, 20.0), Vector2.ZERO, "beyond panic range")


func test_arrive_slows_down_and_stops_on_the_target() -> void:
	assert_almost_eq(Subject.arrive(Vector2.ZERO, Vector2.ZERO, Vector2(50, 0), 100.0, 100.0), Vector2(50, 0), 0.0001)
	var position := Vector2.ZERO
	var velocity := Vector2.ZERO
	for _i in range(1200):
		var force: Vector2 = Subject.arrive(position, velocity, Vector2(200, 100), 120.0, 80.0)
		var state: Dictionary = Subject.integrate(position, velocity, force, 400.0, 120.0, 1.0, 1.0 / 60.0)
		position = state["position"]
		velocity = state["velocity"]
	assert_almost_eq(position, Vector2(200, 100), 1.0)
	assert_lt(velocity.length(), 2.0)


func test_pursue_and_evade_lead_the_target() -> void:
	var force: Vector2 = Subject.pursue(Vector2.ZERO, Vector2.ZERO, Vector2(100, 0), Vector2(0, 50), 100.0)
	assert_almost_eq(force.normalized(), Vector2(100, 50).normalized(), 0.0001, "aims one second ahead")
	var capped: Vector2 = Subject.pursue(Vector2.ZERO, Vector2.ZERO, Vector2(1000, 0), Vector2(0, 50), 100.0, 0.5)
	assert_almost_eq(capped.normalized(), Vector2(1000, 25).normalized(), 0.0001)
	var away: Vector2 = Subject.evade(Vector2.ZERO, Vector2.ZERO, Vector2(100, 0), Vector2(0, 50), 100.0)
	assert_almost_eq(away.normalized(), -Vector2(100, 50).normalized(), 0.0001)


func test_integrate_caps_force_and_speed() -> void:
	var state: Dictionary = Subject.integrate(Vector2.ZERO, Vector2.ZERO, Vector2(1000, 0), 10.0, 100.0, 2.0, 1.0)
	assert_eq(state["velocity"], Vector2(5, 0), "force capped at 10, mass 2")
	var fast: Dictionary = Subject.integrate(Vector2.ZERO, Vector2(90, 0), Vector2(1000, 0), 1000.0, 100.0, 1.0, 1.0)
	assert_eq(fast["velocity"], Vector2(100, 0), "speed capped")
	assert_eq(Subject.truncate(Vector2(3, 4), 1.0), Vector2(0.6, 0.8))


func test_wander_is_smooth_bounded_and_repeatable() -> void:
	var first: Subject = Subject.new(42)
	var second: Subject = Subject.new(42)
	var other: Subject = Subject.new(7)
	var differs: bool = false
	var previous: float = 0.0
	for _i in range(50):
		var a: Vector2 = first.wander(Vector2(10, 0), 10.0)
		assert_eq(a, second.wander(Vector2(10, 0), 10.0))
		differs = differs or not a.is_equal_approx(other.wander(Vector2(10, 0), 10.0))
		assert_true(absf(first.get_wander_angle() - previous) <= 0.6 + 0.0001, "the angle changes by the jitter at most")
		previous = first.get_wander_angle()
		assert_true((a + Vector2(10, 0)).length() <= 10.0 + 0.0001)
	assert_true(differs, "another seed wanders differently")
