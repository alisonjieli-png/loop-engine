"""The card's documents and api.json describe one surface, and the check refuses a card that differs from it.

Known-wrong controls: a surface missing an item, a changed default value or declared type, an item the documents
do not hold, documents that lost a heading, and another class's title are each reported as a disagreement.
"""
import copy
import json
import unittest
from pathlib import Path

import api_card

HERE = Path(__file__).resolve().parent
CONTROL_METHOD = {"name": "known_wrong_control", "returns": {"type": "int"}, "params": []}


def read_card():
    api = json.loads((HERE / "api.json").read_text(encoding="utf-8"))
    names = [path.name for path in HERE.iterdir() if path.is_file()]
    texts = [(HERE / name).read_text(encoding="utf-8") for name in api_card.documents(names)]
    return api, texts


def first_item(api):
    """(section, index) of the first item of the surface, or None for a surface with no item."""
    for section in api_card.SECTIONS:
        if api["sections"].get(section):
            return section, 0
    return None


class CardTests(unittest.TestCase):
    def setUp(self):
        self.api, self.texts = read_card()

    def test_the_documents_agree_with_api_json(self):
        self.assertEqual(api_card.disagreements(self.api, self.texts), [])

    def test_every_document_is_named_by_the_component_card(self):
        component = json.loads((HERE / "component.json").read_text(encoding="utf-8"))
        names = [path.name for path in HERE.iterdir() if path.is_file()]
        self.assertEqual(component["documents"], api_card.documents(names))
        self.assertEqual(component["job"], {"engine": self.api["engine"]["name"],
                                            "version": self.api["engine"]["api_version"],
                                            "class": self.api["class"]})
        self.assertEqual(component["title"], api_card.title_line(self.api))

    def test_known_wrong_a_missing_item_is_reported(self):
        changed = copy.deepcopy(self.api)
        found = first_item(changed)
        if found is None:
            changed["inherits"] = changed["inherits"][1:]
        else:
            section, index = found
            del changed["sections"][section][index]
        self.assertTrue(api_card.disagreements(changed, self.texts))

    def test_known_wrong_a_changed_default_or_type_is_reported(self):
        changed = copy.deepcopy(self.api)
        target = None
        for section in api_card.SECTIONS:
            for item in changed["sections"].get(section) or []:
                for candidate in [item] + list(item.get("params", ())):
                    if "default" in candidate and target is None:
                        target = candidate
        if target is not None:
            target["default"] = str(target["default"]) + "0"
        else:
            changed["sections"][api_card.METHODS] = [dict(CONTROL_METHOD, returns={"type": "Variant"})]
        self.assertTrue(api_card.disagreements(changed, self.texts))
        # The control's own premise: the unchanged card agrees.
        self.assertEqual(api_card.disagreements(self.api, self.texts), [])

    def test_known_wrong_an_item_the_documents_do_not_hold_is_reported(self):
        changed = copy.deepcopy(self.api)
        changed["sections"].setdefault(api_card.METHODS, []).append(dict(CONTROL_METHOD))
        problems = api_card.disagreements(changed, self.texts)
        self.assertTrue(any("known_wrong_control" in problem for problem in problems), problems)

    def test_known_wrong_documents_that_lost_a_heading_are_reported(self):
        prefix = api_card.ITEM_PREFIX if first_item(self.api) else api_card.TITLE_PREFIX
        damaged = []
        removed = False
        for text in self.texts:
            lines = text.split("\n")
            for position, line in enumerate(lines):
                if not removed and line.startswith(prefix):
                    del lines[position]
                    removed = True
                    break
            damaged.append("\n".join(lines))
        self.assertTrue(removed)
        self.assertTrue(api_card.disagreements(self.api, damaged))

    def test_known_wrong_another_class_title_is_reported(self):
        changed = copy.deepcopy(self.api)
        changed["class"] = changed["class"] + "Other"
        self.assertTrue(api_card.disagreements(changed, self.texts))


if __name__ == "__main__":
    unittest.main()
