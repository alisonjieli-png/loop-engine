"""Known answers for the three-point rig: aim directions, inverse-square powers and refused inputs."""
import math
import unittest

import light_three_point as rig


class RigTests(unittest.TestCase):
    def test_aim_rotation_points_minus_z_at_the_target(self):
        cases = [([0.0, -4.0, 1.0], [0.0, 0.0, 1.0], [90.0, 0.0, 0.0]), ([0.0, 0.0, 5.0], [0.0, 0.0, 0.0],
                                                                          [0.0, 0.0, 0.0])]
        for position, target, rotation in cases:
            self.assertEqual([round(value, 9) for value in rig.aim_rotation(position, target)], rotation)
        layout = rig.rig_layout()
        target = rig.parameters()["target"]
        for item in layout["objects"][1:]:
            direction = [b - a for a, b in zip(item["world_location"], target)]
            length = math.sqrt(sum(value * value for value in direction))
            aimed = rig.rotate_minus_z(item["rotation"])
            for got, want in zip(aimed, direction):
                self.assertAlmostEqual(got, want / length, places=7)

    def test_illuminance_ratios_hold_at_the_target(self):
        layout = rig.rig_layout(key_fill_ratio=4.0, rim_ratio=0.5, key_distance=3.0, fill_distance=6.0,
                                key_power=500.0)
        powers = layout["report"]["powers_w"]
        illuminance = {item["name"]: powers[item["name"]] / sum(v * v for v in item["location"])
                       for item in layout["objects"][1:]}
        self.assertAlmostEqual(illuminance["Key Light"] / illuminance["Fill Light"], 4.0, places=6)
        self.assertAlmostEqual(illuminance["Rim Light"] / illuminance["Key Light"], 0.5, places=6)
        self.assertAlmostEqual(powers["Fill Light"], 500.0 / 4.0 * 4.0)

    def test_light_distances_match_parameters(self):
        layout = rig.rig_layout(key_distance=2.5)
        key = next(item for item in layout["objects"] if item["name"] == "Key Light")
        self.assertAlmostEqual(math.sqrt(sum(v * v for v in key["location"])), 2.5)

    def test_known_wrong_inputs_are_refused(self):
        with self.assertRaises(ValueError):
            rig.aim_rotation([1.0, 1.0, 1.0], [1.0, 1.0, 1.0])
        for bad in ({"key_fill_ratio": 0.5}, {"target": [0.0, 0.0]}, {"key_color": [0.0, 2.0, 0.0]}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                rig.rig_layout(**bad)


if __name__ == "__main__":
    unittest.main()
