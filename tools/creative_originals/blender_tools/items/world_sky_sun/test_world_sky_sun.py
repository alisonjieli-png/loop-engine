"""Known answers for the sky and sun: direction convention, lamp aim, report, refusals."""
import math
import unittest

import world_sky_sun as sky


def rotate_minus_z(rotation):
    rx, ry, rz = (math.radians(a) for a in rotation)
    x, y, z = 0.0, 0.0, -1.0
    y, z = y * math.cos(rx) - z * math.sin(rx), y * math.sin(rx) + z * math.cos(rx)
    x, z = x * math.cos(ry) + z * math.sin(ry), -x * math.sin(ry) + z * math.cos(ry)
    x, y = x * math.cos(rz) - y * math.sin(rz), x * math.sin(rz) + y * math.cos(rz)
    return [x, y, z]


class SkyTests(unittest.TestCase):
    def test_direction_convention(self):
        for got, want in zip(sky.sun_direction(0.0, 0.0), [0.0, 1.0, 0.0]):
            self.assertAlmostEqual(got, want)
        for got, want in zip(sky.sun_direction(0.0, 90.0), [1.0, 0.0, 0.0]):
            self.assertAlmostEqual(got, want)
        self.assertAlmostEqual(sky.sun_direction(30.0, 45.0)[2], 0.5)

    def test_lamp_shines_away_from_the_sun(self):
        for elevation, azimuth in ((28.0, 135.0), (5.0, 300.0), (80.0, 10.0)):
            light = rotate_minus_z(sky.lamp_rotation(elevation, azimuth))
            sun = sky.sun_direction(elevation, azimuth)
            for got, want in zip(light, sun):
                self.assertAlmostEqual(got, -want, places=9)

    def test_known_wrong_inputs_are_refused(self):
        for bad in ({"elevation": 95.0}, {"azimuth": -1.0}, {"sky_sun_disc": 1}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                sky.sky_setup(**bad)


if __name__ == "__main__":
    unittest.main()
