"""Prompt elements and response style as declared, optimizable dimensions.

A prompt resource is built from named elements (task background, context
background, atomic information, inputs and outputs, expectations, format)
and asks for one response style (concise, only what was asked, full). Which
elements are present and which style is asked for are configuration
choices, not habits of the author, so a grid can vary them and the
evaluation product can measure what each contributes to verified outcomes
and tokens. This module owns the vocabularies, the typed selection, the two
grid axes that address every combination, the deterministic rendering of
the style instruction, and the render digest that records exactly which
slot a cell changed. It grants nothing and calls no model.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

PROMPT_ELEMENTS = ("task_background", "context_background", "atomic_information",
                   "inputs_and_outputs", "expectations", "format")
RESPONSE_STYLES = ("concise", "only_what_was_asked", "full")
#: The instruction each style renders; data, not branches, so a new style is a new row.
STYLE_INSTRUCTIONS = (
    (RESPONSE_STYLES[0], "Answer in as few words as carry the result; no preamble, no restatement, "
                         "no closing remark."),
    (RESPONSE_STYLES[1], "Answer only what was asked, in the requested shape; add nothing that was "
                         "not requested."),
    (RESPONSE_STYLES[2], "Answer in full: the result, the reasoning that supports it, the "
                         "assumptions made, and the checks performed."),
)
AXIS_NAMES = ("prompt_element_set", "response_style_index")
RECORD_TYPE = "prompt_element_selection/v1"
_STYLE_TEXT = dict(STYLE_INSTRUCTIONS)


class PromptElementError(ValueError):
    """A selection, axis address, or rendering request is invalid."""


@dataclass(frozen=True)
class PromptElementSelection:
    """Which elements a prompt carries and which response style it asks for."""

    elements: tuple[str, ...] = PROMPT_ELEMENTS
    response_style: str = RESPONSE_STYLES[2]

    def __post_init__(self):
        elements = tuple(self.elements)
        if any(item not in PROMPT_ELEMENTS for item in elements) or len(set(elements)) != len(elements):
            raise PromptElementError(f"elements must be unique names from {PROMPT_ELEMENTS}")
        if self.response_style not in RESPONSE_STYLES:
            raise PromptElementError(f"response style must be one of {RESPONSE_STYLES}")
        # Kept in the declared order so two selections of the same set are equal.
        object.__setattr__(self, "elements", tuple(item for item in PROMPT_ELEMENTS if item in elements))

    @property
    def element_index(self) -> int:
        """The bit set of the elements, the first axis address."""
        return sum(1 << position for position, name in enumerate(PROMPT_ELEMENTS) if name in self.elements)

    @property
    def style_index(self) -> int:
        return RESPONSE_STYLES.index(self.response_style)

    def address(self) -> dict:
        return {AXIS_NAMES[0]: self.element_index, AXIS_NAMES[1]: self.style_index}

    def includes(self, element: str) -> bool:
        if element not in PROMPT_ELEMENTS:
            raise PromptElementError(f"unknown prompt element {element!r}")
        return element in self.elements

    def render_style_instruction(self) -> str:
        return _STYLE_TEXT[self.response_style]

    def to_dict(self) -> dict:
        return {"record_type": RECORD_TYPE, "elements": list(self.elements),
                "response_style": self.response_style, **self.address()}

    @property
    def render_digest(self) -> str:
        """The digest of exactly what a rendered prompt carries from this selection."""
        body = json.dumps({"elements": list(self.elements),
                           "style_instruction": self.render_style_instruction()},
                          sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(body.encode("utf-8")).hexdigest()


def selection_from_address(element_index: int, style_index: int) -> PromptElementSelection:
    """The selection at one grid address; an address outside the axes is refused."""
    if type(element_index) is not int or not 0 <= element_index < 2 ** len(PROMPT_ELEMENTS):
        raise PromptElementError(f"element index must be an integer below {2 ** len(PROMPT_ELEMENTS)}")
    if type(style_index) is not int or not 0 <= style_index < len(RESPONSE_STYLES):
        raise PromptElementError(f"style index must be an integer below {len(RESPONSE_STYLES)}")
    elements = tuple(name for position, name in enumerate(PROMPT_ELEMENTS) if element_index & (1 << position))
    return PromptElementSelection(elements, RESPONSE_STYLES[style_index])


def axes() -> tuple[dict, ...]:
    """The two integer-range axes a configuration space declares for these dimensions."""
    return ({"name": AXIS_NAMES[0], "kind": "integer_range", "minimum": 0,
             "maximum": 2 ** len(PROMPT_ELEMENTS) - 1, "cardinality": 2 ** len(PROMPT_ELEMENTS)},
            {"name": AXIS_NAMES[1], "kind": "integer_range", "minimum": 0,
             "maximum": len(RESPONSE_STYLES) - 1, "cardinality": len(RESPONSE_STYLES)})


def render_prompt(selection: PromptElementSelection, parts: dict) -> str:
    """The prompt text from the selected elements, in the declared order, plus the style instruction.

    ``parts`` maps element names to their text; an element that is selected
    but absent from the parts is refused, so a cell never silently drops
    material it declared, and an element present in the parts but not
    selected is left out, which is the point of the axis.
    """
    if not isinstance(selection, PromptElementSelection):
        raise PromptElementError("render_prompt needs a typed PromptElementSelection")
    missing = [name for name in selection.elements if not str(parts.get(name, "")).strip()]
    if missing:
        raise PromptElementError(f"selected elements without text: {missing}")
    blocks = [f"[{name}]\n{str(parts[name]).strip()}" for name in selection.elements]
    blocks.append(f"[response_style:{selection.response_style}]\n{selection.render_style_instruction()}")
    return "\n\n".join(blocks)


def self_test() -> dict:
    """Vocabularies, addresses, rendering, digests, and refusals."""
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    def refuses(action):
        try:
            action()
        except PromptElementError:
            return True
        except Exception:  # noqa: BLE001  (a crash is not a typed refusal)
            return False
        return False

    full = PromptElementSelection()
    lean = PromptElementSelection(("format", "inputs_and_outputs"), RESPONSE_STYLES[0])
    check("a_selection_keeps_the_declared_order_and_addresses_both_axes",
          lean.elements == ("inputs_and_outputs", "format") and lean.element_index == (1 << 3) | (1 << 5)
          and lean.style_index == 0 and full.element_index == 2 ** len(PROMPT_ELEMENTS) - 1
          and full.address() == {AXIS_NAMES[0]: 63, AXIS_NAMES[1]: 2}
          and selection_from_address(lean.element_index, 0) == lean)
    space = axes()
    every = [selection_from_address(element, style) for element in range(64) for style in range(3)]
    check("the_two_axes_address_every_combination_exactly_once",
          space[0]["cardinality"] * space[1]["cardinality"] == 192 == len(every)
          and len({item.address()[AXIS_NAMES[0]] * 3 + item.address()[AXIS_NAMES[1]] for item in every}) == 192
          and refuses(lambda: selection_from_address(64, 0)) and refuses(lambda: selection_from_address(0, 3)))
    parts = {name: f"text for {name}" for name in PROMPT_ELEMENTS}
    rendered_full = render_prompt(full, parts)
    rendered_lean = render_prompt(lean, parts)
    check("rendering_carries_only_the_selected_elements_and_the_style_instruction",
          all(f"[{name}]" in rendered_full for name in PROMPT_ELEMENTS)
          and "[task_background]" not in rendered_lean and "[format]" in rendered_lean
          and rendered_lean.index("[inputs_and_outputs]") < rendered_lean.index("[format]")
          and rendered_lean.endswith(_STYLE_TEXT[RESPONSE_STYLES[0]])
          and rendered_full.endswith(_STYLE_TEXT[RESPONSE_STYLES[2]]))
    style_only = PromptElementSelection(("format", "inputs_and_outputs"), RESPONSE_STYLES[1])
    check("a_cell_that_changes_one_slot_changes_the_render_digest_and_nothing_else",
          lean.render_digest != style_only.render_digest
          and lean.elements == style_only.elements
          and lean.render_digest == PromptElementSelection(("inputs_and_outputs", "format"),
                                                          RESPONSE_STYLES[0]).render_digest
          and render_prompt(style_only, parts).replace(_STYLE_TEXT[RESPONSE_STYLES[1]], "")
          .replace(f"[response_style:{RESPONSE_STYLES[1]}]", "")
          == rendered_lean.replace(_STYLE_TEXT[RESPONSE_STYLES[0]], "")
          .replace(f"[response_style:{RESPONSE_STYLES[0]}]", ""))
    check("selected_elements_without_text_and_unknown_names_are_refused",
          refuses(lambda: render_prompt(lean, {"format": "x"}))
          and refuses(lambda: PromptElementSelection(("format", "format")))
          and refuses(lambda: PromptElementSelection(("tone",)))
          and refuses(lambda: PromptElementSelection((), "caveman"))
          and refuses(lambda: lean.includes("tone"))
          and render_prompt(PromptElementSelection((), RESPONSE_STYLES[0]), {}).startswith("[response_style:"))
    check("the_record_and_the_style_table_are_data",
          full.to_dict()["record_type"] == RECORD_TYPE and full.to_dict()["response_style"] == RESPONSE_STYLES[2]
          and [style for style, _text in STYLE_INSTRUCTIONS] == list(RESPONSE_STYLES)
          and lean.includes("format") and not lean.includes("expectations"))
    passed = sum(item["passed"] for item in tests)
    return {"record_type": "prompt_elements_test/v1", "tests": tests, "passed": passed,
            "total": len(tests), "all_passed": passed == len(tests)}
