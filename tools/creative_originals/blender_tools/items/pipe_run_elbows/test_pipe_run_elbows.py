"""Known answers for the pipe run: elbow geometry, centreline length, closed sweep, refusals."""
import math
import unittest

import meshcheck
import pipe_run_elbows as pipe


class PipeTests(unittest.TestCase):
    def test_right_angle_elbow_length(self):
        report = pipe.build_geometry(points="0,0,0; 2,0,0; 2,2,0", bend_radius=0.5, bend_segments=64,
                                     flanges=False)["report"]
        expected = (2 - 0.5) * 2 + math.pi * 0.5 / 2
        self.assertEqual(report["bend_angles_degrees"], [90.0])
        self.assertAlmostEqual(report["centreline_length_m"], expected, places=3)

    def test_arc_stays_at_bend_radius(self):
        samples, _joints, _bends = pipe.centreline(points="0,0,0; 2,0,0; 2,2,0", bend_radius=0.5)
        centre = [1.5, 0.5, 0.0]
        arc = [point for point, _tangent in samples if 1.5 - 1e-9 <= point[0] and point[1] <= 0.5 + 1e-9]
        self.assertTrue(all(abs(math.dist(point, centre) - 0.5) < 1e-9 for point in arc))

    def test_frames_are_perpendicular_to_tangents(self):
        samples, _joints, _bends = pipe.centreline()
        for (_point, tangent), normal in zip(samples, pipe._frames(samples)):
            self.assertAlmostEqual(sum(a * b for a, b in zip(tangent, normal)), 0.0, places=9)

    def test_closed_solids(self):
        mesh = pipe.build_geometry()
        self.assertEqual(meshcheck.closed_problems(mesh["faces"]), [])
        self.assertEqual(meshcheck.euler_characteristic(mesh["vertices"], mesh["faces"]),
                         2 * (1 + mesh["report"]["flanges"]))

    def test_known_wrong_inputs_are_refused(self):
        for bad in ({"points": "0,0,0"}, {"points": "0,0,0; 1,0,0; 0,0,0"}, {"points": "0,0; 1,1,1"},
                    {"points": "0,0,0; 0.2,0,0; 0.2,0.2,0", "bend_radius": 1.0}, {"bend_radius": 0.01}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                pipe.build_geometry(**bad)


if __name__ == "__main__":
    unittest.main()
