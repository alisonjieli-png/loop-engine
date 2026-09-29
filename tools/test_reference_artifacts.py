"""A harness may pick up a reference image, a mask, a pose layout, a 3D model or a template, and the owner,
September 29, 2026, asked for exactly that: "images could be harness component files, masks could be harness
component masks, etc, 3D models, STL files, 3D files, autocode styles, etc, all of these could be reference
files that a harness could analyze, understand".

A harness is handed these bytes and interprets them, so nothing in the file itself says how. The known-wrong
cases here are all silent: an artifact with no role reads as a reference when it was meant as evidence, a pose
layout read as the wrong keypoint set puts joints in the wrong places, and a mask with no stated polarity
inverts every selection made from it while still looking plausible.
"""
import unittest

from loop_engine.core.service_runtime.catalogue_attributes import (
    ASSET_ROLES, COMPONENT_FORM_KINDS, COMPONENT_FORMS, HARNESS_KINDS, MASK_POLARITIES, POSE_LAYOUTS,
    asset_role_problems)


class ReferenceArtifactVocabulary(unittest.TestCase):
    def test_every_reference_form_is_a_declared_form_and_a_harness_kind(self):
        for form in ("reference_image", "mask", "pose_layout", "three_d_model", "cad_model", "template"):
            self.assertIn(form, COMPONENT_FORMS, form)
            kinds = COMPONENT_FORM_KINDS[form]
            self.assertTrue(kinds, form)
            for kind in kinds:
                self.assertIn(kind, HARNESS_KINDS, kind)

    def test_an_artifact_with_no_role_is_refused(self):
        # KNOWN_WRONG: the bytes are valid and the component is otherwise complete, but nothing says what a
        # harness may do with them, so the same PNG serves as guidance in one package and as evidence in another.
        self.assertEqual(asset_role_problems("reference_image", {}),
                         ["the artifact declares no asset_role"])

    def test_a_role_outside_the_vocabulary_is_refused(self):
        self.assertEqual(asset_role_problems("template", {"asset_role": "inspiration"}),
                         ["the artifact declares the asset role 'inspiration'"])

    def test_a_pose_layout_with_no_layout_is_refused(self):
        # KNOWN_WRONG: a pose drawn as 25 body keypoints read as an 18 keypoint layout puts every joint in the
        # wrong place, and the result is a plausible-looking figure with the wrong skeleton.
        self.assertEqual(asset_role_problems("pose_layout", {"asset_role": "reference"}),
                         ["the pose layout names no layout, so its keypoints cannot be read"])

    def test_a_pose_layout_naming_an_unknown_layout_is_refused(self):
        self.assertEqual(asset_role_problems("pose_layout", {"asset_role": "reference", "pose_layout": "coco17"}),
                         ["the pose layout names the layout 'coco17'"])

    def test_a_mask_with_no_polarity_is_refused(self):
        # KNOWN_WRONG: a mask whose painted pixels were not stated inverts every selection drawn from it, and
        # an inverted selection still looks like a plausible result.
        self.assertEqual(asset_role_problems("mask", {"asset_role": "generation_input"}),
                         ["the mask states no polarity, so its painted pixels are ambiguous"])

    def test_a_complete_artifact_passes(self):
        for form, attributes in (("reference_image", {"asset_role": "reference"}),
                                 ("mask", {"asset_role": "test_evidence", "mask_polarity": "foreground"}),
                                 ("pose_layout", {"asset_role": "generation_input", "pose_layout": "openpose25"}),
                                 ("three_d_model", {"asset_role": "editable_source"}),
                                 ("code_example", {"asset_role": "reference"})):
            self.assertEqual(asset_role_problems(form, attributes), [], form)

    def test_a_text_component_is_exempt(self):
        # A skill, an instruction file and a code module say what they are by being what they are. These rules
        # are for the artifacts a harness has to interpret, and adding them to every component would be noise.
        for form in ("skill", "instructions", "code_module", "schema"):
            self.assertEqual(asset_role_problems(form, {}), [], form)

    def test_the_vocabularies_name_what_they_admit(self):
        self.assertEqual(ASSET_ROLES, ("reference", "generation_input", "editable_source", "test_evidence"))
        self.assertIn("openpose25", POSE_LAYOUTS)
        self.assertEqual(MASK_POLARITIES, ("foreground", "background"))


if __name__ == "__main__":
    unittest.main()
