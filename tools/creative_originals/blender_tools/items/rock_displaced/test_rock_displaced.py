"""Known answers for the rock: icosphere counts, closed surface, flat base, seed determinism, noise range."""
import unittest

import meshcheck
import rock_displaced as rock


class RockTests(unittest.TestCase):
    def test_icosphere_counts(self):
        for level in range(4):
            vertices, faces = rock.icosphere(level)
            self.assertEqual(len(vertices), 10 * 4 ** level + 2)
            self.assertEqual(len(faces), 20 * 4 ** level)
            self.assertEqual(meshcheck.closed_problems(faces), [])
            self.assertAlmostEqual(meshcheck.signed_volume(vertices, faces) / (4.18879), 1.0, delta=0.4)

    def test_rock_is_closed_and_sits_on_its_base(self):
        mesh = rock.build_geometry(seed=11, flat_base=0.4)
        self.assertEqual(meshcheck.closed_problems(mesh["faces"]), [])
        self.assertEqual(min(vertex[2] for vertex in mesh["vertices"]), 0.0)
        flat = sum(1 for vertex in mesh["vertices"] if vertex[2] == 0.0)
        self.assertGreater(flat, 10)

    def test_seed_controls_the_shape(self):
        first = rock.build_geometry(seed=1)["vertices"]
        self.assertEqual(first, rock.build_geometry(seed=1)["vertices"])
        self.assertNotEqual(first, rock.build_geometry(seed=2)["vertices"])

    def test_noise_stays_in_range(self):
        samples = [rock.value_noise(x * 0.37, x * 0.11, x * 0.53, 5) for x in range(200)]
        self.assertTrue(all(-1.0 <= value <= 1.0 for value in samples))
        self.assertGreater(max(samples) - min(samples), 0.5)
        self.assertAlmostEqual(rock.value_noise(2.0, 3.0, 4.0, 9), rock._lattice(2, 3, 4, 9))

    def test_known_wrong_inputs_are_refused(self):
        for bad in ({"subdivisions": 7}, {"dimensions": [1.0, 1.0]}, {"roughness": -0.1}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                rock.build_geometry(**bad)


if __name__ == "__main__":
    unittest.main()
