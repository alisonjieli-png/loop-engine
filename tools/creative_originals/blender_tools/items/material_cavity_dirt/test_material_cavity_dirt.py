"""Known answers for cavity dirt: open surfaces stay clean, crevices get dirty, streaks add dirt, refusals."""
import unittest

import graphcheck
import material_cavity_dirt as dirt


class CavityDirtTests(unittest.TestCase):
    def test_open_surface_is_clean(self):
        self.assertEqual(dirt.dirt_mask(1.0, 0.0), 0.0)

    def test_crevice_is_dirty(self):
        self.assertEqual(dirt.dirt_mask(0.1, 0.5), 1.0)

    def test_streaks_add_dirt(self):
        self.assertGreater(dirt.dirt_mask(0.55, 1.0, streaks=0.8), dirt.dirt_mask(0.55, 1.0, streaks=0.0))

    def test_graph_is_wired(self):
        self.assertEqual(graphcheck.tree_problems(dirt.material_graph()["trees"][0]), [])

    def test_known_wrong_inputs_are_refused(self):
        for bad in ({"ao_distance": 0.0}, {"dirt_amount": 1.2}, {"streak_scale": 0.0}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                dirt.material_graph(**bad)


if __name__ == "__main__":
    unittest.main()
