"""Known answers for the rename planner: demo plan, case styles, collisions, the byte limit, refused inputs."""
import unittest

import util_batch_rename as rename


class RenameTests(unittest.TestCase):
    def test_demo_plan(self):
        plan = dict(map(tuple, rename.plan_renames()["report"]["renames"]))
        self.assertEqual(plan, {"Cube": "SM_cube_01", "Cube.001": "SM_cube_02", "Cube.002": "SM_cube_03",
                                "Sphere": "SM_sphere", "lampPost": "SM_lamp_post", "Old Barrel": "SM_old_barrel",
                                "SM_rock": "SM_rock"})

    def test_case_styles(self):
        self.assertEqual(rename.words("lampPost2 x"), ["lamp", "Post", "2", "x"])
        self.assertEqual(rename.styled("HTTPServer main", "snake"), "http_server_main")
        self.assertEqual(rename.styled("old barrel", "pascal"), "OldBarrel")

    def test_names_outside_the_batch_are_avoided(self):
        plan = rename.plan_renames(["Box"], ["SM_box"], numbering="none")["report"]["renames"]
        self.assertEqual(plan, [["Box", "SM_box_02"]])
        plan = rename.plan_renames(["Box"], ["SM_box"])["report"]["renames"]
        self.assertEqual(plan, [["Box", "SM_box_01"]])

    def test_every_new_name_is_unique_and_fits(self):
        names = [f"Very Long Object Name Number {index} " + "x" * 40 for index in range(30)]
        plan = rename.plan_renames(names, numbering="always", case="pascal")["report"]["renames"]
        new = [pair[1] for pair in plan]
        self.assertEqual(len(new), len(set(new)))
        self.assertTrue(all(len(name.encode("utf-8")) <= 63 for name in new))

    def test_regex_replace(self):
        plan = rename.plan_renames(["rock_v2_final"], use_regex=True, find=r"_v[0-9]+_final$", replace="",
                                   prefix="")["report"]["renames"]
        self.assertEqual(plan, [["rock_v2_final", "rock"]])

    def test_known_wrong_inputs_are_refused(self):
        with self.assertRaises(ValueError):
            rename.plan_renames(use_regex=True, find="(unclosed")
        with self.assertRaises(ValueError):
            rename.plan_renames(["a", "a"])
        with self.assertRaises(ValueError):
            rename.plan_renames(prefix="x" * 64)


if __name__ == "__main__":
    unittest.main()
