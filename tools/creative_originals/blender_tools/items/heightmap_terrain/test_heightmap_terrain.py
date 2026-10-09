"""Known answers for the terrain: grid counts, sea flattening, closed base, noise range, refusals."""
import unittest

import heightmap_terrain as terrain
import meshcheck


class TerrainTests(unittest.TestCase):
    def test_grid_counts(self):
        mesh = terrain.build_geometry(resolution=10)
        self.assertEqual(len(mesh["vertices"]), 121)
        self.assertEqual(len(mesh["faces"]), 100)
        self.assertEqual(len(meshcheck.boundary_edges(mesh["faces"])), 40)

    def test_base_closes_the_solid(self):
        mesh = terrain.build_geometry(resolution=12, base_depth=2.0)
        self.assertEqual(meshcheck.closed_problems(mesh["faces"]), [])
        self.assertGreater(meshcheck.signed_volume(mesh["vertices"], mesh["faces"]), 20.0 * 20.0 * 2.0 * 0.99)
        self.assertEqual(meshcheck.bounds(mesh["vertices"])[0][2], -2.0)

    def test_sea_level_flattens(self):
        mesh = terrain.build_geometry(resolution=16, sea_level=0.6)
        self.assertEqual(min(vertex[2] for vertex in mesh["vertices"]), 0.0)
        self.assertGreater(len(mesh["groups"]["sea"]), 0)
        self.assertTrue(all(mesh["vertices"][index][2] == 0.0 for index in mesh["groups"]["sea"]))

    def test_noise_is_bounded_and_varies(self):
        values = [terrain.gradient_noise(x * 0.31, x * 0.17, 3) for x in range(300)]
        self.assertTrue(all(-1.01 <= value <= 1.01 for value in values))
        self.assertGreater(max(values) - min(values), 0.6)
        self.assertEqual(terrain.gradient_noise(4.0, 7.0, 3), 0.0)

    def test_terraces_quantise(self):
        rows = terrain.height_field(resolution=8, terraces=4, sea_level=0.0, island=0.0, height=1.0)
        self.assertTrue(all(0.0 <= value <= 1.0 for row in rows for value in row))

    def test_known_wrong_inputs_are_refused(self):
        for bad in ({"resolution": 1}, {"gain": 1.0}, {"octaves": 0}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                terrain.build_geometry(**bad)


if __name__ == "__main__":
    unittest.main()
