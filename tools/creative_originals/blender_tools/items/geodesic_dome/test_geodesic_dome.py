"""Known answers for the geodesic dome: 2V counts and chord factors, flat rim, closed parts, refusals."""
import unittest

import geodesic_dome as dome
import meshcheck


class DomeTests(unittest.TestCase):
    def test_two_frequency_counts_and_chord_factors(self):
        report = dome.build_geometry(frequency=2, radius=1.0)["report"]
        self.assertEqual(report["hubs"], 26)
        self.assertEqual(report["struts"], 65)
        self.assertEqual(report["panels"], 40)
        factors = [row["chord_factor"] for row in report["strut_classes"]]
        self.assertEqual(len(factors), 2)
        self.assertAlmostEqual(factors[0], 0.546533, places=5)
        self.assertAlmostEqual(factors[1], 0.618034, places=5)

    def test_even_frequency_rim_is_flat(self):
        hubs, triangles, lift = dome.dome_surface(4, 2.0)
        self.assertEqual(lift, 0.0)
        boundary = meshcheck.boundary_edges(triangles)
        self.assertTrue(all(abs(hubs[a][2]) < 1e-9 and abs(hubs[b][2]) < 1e-9 for a, b in boundary))

    def test_parts_are_closed(self):
        for mode in ("struts", "panels"):
            mesh = dome.build_geometry(frequency=2, mode=mode)
            self.assertEqual(meshcheck.closed_problems(mesh["faces"]), [], mode)
        panels = dome.build_geometry(frequency=3, mode="panels")
        self.assertEqual(meshcheck.euler_characteristic(panels["vertices"], panels["faces"]), 2)

    def test_known_wrong_inputs_are_refused(self):
        for bad in ({"mode": "panels", "thickness": 2.0}, {"hub_radius": 0.01}, {"frequency": 0}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                dome.build_geometry(**bad)


if __name__ == "__main__":
    unittest.main()
