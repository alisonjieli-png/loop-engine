"""Known answers for the brick bonds: course rules, joints that never line up, counts, refused inputs."""
import unittest

import brick_wall_bonds as wall
import meshcheck

BRICK = [0.215, 0.1025, 0.065]


class BondTests(unittest.TestCase):
    def test_stretcher_courses_shift_half_a_brick(self):
        even = wall.course_layout("stretcher", 0, 2.0, BRICK, 0.01, 6)
        odd = wall.course_layout("stretcher", 1, 2.0, BRICK, 0.01, 6)
        self.assertAlmostEqual(odd[0][0] - even[0][0], -0.1125)
        self.assertEqual({row[4] for row in even}, {"stretcher"})

    def test_english_header_course_starts_with_a_queen_closer(self):
        header = wall.course_layout("english", 1, 2.0, BRICK, 0.01, 6)
        self.assertEqual(header[0][4], "closer")
        self.assertAlmostEqual(header[0][1] - header[0][0], (0.1025 - 0.01) / 2)
        self.assertTrue(all(row[3] - row[2] > 0.2 for row in header))

    def test_flemish_alternates_headers_and_stretchers(self):
        course = wall.course_layout("flemish", 0, 2.0, BRICK, 0.01, 6)
        front = [row for row in course if row[2] == 0.0]
        self.assertEqual([row[4] for row in front[:4]], ["header", "stretcher", "header", "stretcher"])

    def test_vertical_joints_do_not_line_up(self):
        for bond in ("stretcher", "english", "flemish"):
            first = {round(row[1], 6) for row in wall.course_layout(bond, 0, 2.0, BRICK, 0.01, 6) if row[2] == 0.0}
            second = {round(row[1], 6) for row in wall.course_layout(bond, 1, 2.0, BRICK, 0.01, 6) if row[2] == 0.0}
            self.assertFalse(first & second - {round(2.0, 6)}, bond)

    def test_wall_extent_and_closed_bricks(self):
        mesh = wall.build_geometry(length=1.5, courses=4, bond="stretcher")
        low, high = meshcheck.bounds(mesh["vertices"])
        self.assertAlmostEqual(high[0], 1.5)
        self.assertAlmostEqual(high[2], 4 * 0.075 - 0.01)
        self.assertEqual(meshcheck.closed_problems(mesh["faces"]), [])
        self.assertEqual(len(mesh["face_materials"]), len(mesh["faces"]))

    def test_known_wrong_inputs_are_refused(self):
        for bad in ({"brick": [0.1, 0.1, 0.05]}, {"bond": "herringbone"}, {"recess": 0.03, "brick": [0.215, 0.05, 0.065]}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                wall.build_geometry(**bad)


if __name__ == "__main__":
    unittest.main()
