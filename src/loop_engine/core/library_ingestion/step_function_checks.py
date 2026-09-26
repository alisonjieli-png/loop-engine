"""Known-wrong checks for the step function tagger, run offline with no model and no network.

Each check names the input that must be tagged, refused or left untagged.
The controls whose names start with ``removed_`` run a check with one rule
taken away and confirm that the check would then fail: without the file-role
rule a package that only holds a script loses its acting tag, without the
score threshold every function that is named once would be tagged, without
the body-only minimum three incidental body words tag a function, without
the headline-first order a purpose word loses to body words, and with the
dropped words back or the added words gone the sampled cases score as they
did under rules 1.0.0.
"""
from __future__ import annotations

from .record_rules import LibraryRecordError
from .step_functions import (
    ATTRIBUTE_NAME, BODY_ONLY_MINIMUM, MAXIMUM_FUNCTIONS, STEP_FUNCTIONS, STEP_FUNCTIONS_ATTRIBUTE, TEXT_BOUND,
    RulesStepFunctionTagger, StepFunctionMaterial, StepFunctionTags, _WORDS, _compile, entry_text)

TEST_SKILL = ("---\nname: run-tests\ndescription: Run the project's test suite and report each failing check.\n---\n\n"
              "# Run tests\n\nRun the tests, then verify every failing assertion against the change.\n")
DEPLOY_RUNBOOK = ("# Release to the cluster\n\nDeploy the image with the pipeline, then monitor the alerts and roll "
                  "back on an incident.\n")
PLAIN = "# Notes\n\nThe colour of the header is navy. The footer repeats the address.\n"
SCRIPT_ONLY = "#!/usr/bin/env python3\nprint('hello')\n"
#: Three verification words in a body that is about a door, then a fourth: the September 26, 2026 sample
#: found two or three incidental body words tag the wrong function far more often than the right one.
THREE_BODY_WORDS = "# Door\n\nCheck the lock. Test the latch. Verify the hinge before the guests arrive.\n"
FOUR_BODY_WORDS = THREE_BODY_WORDS + "Validate the key against the cylinder.\n"
#: Four body-only functions at score two, each from four distinct words, beside one word in the purpose.
CROWDED_BODY = ("Run the command, install the script and invoke the cli. Analyze, inspect, debug and profile the "
                "output. Build, implement, compile and refactor the module. Deploy, monitor, release and docker "
                "the service.\n")
#: The words the sample dropped, as the 1.0.0 vocabulary held them, to prove each drop changes the answer.
DROPPED_WORDS = {"acting": "apply|applies", "operating": "ci|cd|pipeline|pipelines|alert|alerts|infrastructure|infra",
                 "building": "create|creates|creating|generate|generates|generating|generator",
                 "reviewing": "approve|approval|pull request|pull requests"}
ADDED_WORDS = {"building": ("implementing", "coding"), "analysis": ("diagnosing", "inspecting"),
               "verification": ("verifying", "validating"), "reasoning": ("deciding", "judging")}


def _patterns_with(extra: dict) -> dict:
    return _compile({function: words + ("|" + extra[function] if function in extra else "")
                     for function, words in _WORDS.items()})


def _patterns_without(removed: dict) -> dict:
    return _compile({function: "|".join(part for part in words.split("|") if part not in removed.get(function, ()))
                     for function, words in _WORDS.items()})


def _refused(build) -> bool:
    try:
        build()
    except LibraryRecordError:
        return True
    return False


class _without:
    """Run one check with a rule of the tagger module replaced, then put the rule back whatever happens.

    The rules are the module globals the tagger's own functions read; they are reached through the tagger's
    function rather than by importing the module object, which keeps this check's imports within the boundary."""

    def __init__(self, **replacements):
        self.replacements = replacements
        self.rules = RulesStepFunctionTagger.scores.__globals__
        self.saved = {}

    def __enter__(self):
        self.saved = {name: self.rules[name] for name in self.replacements}
        self.rules.update(self.replacements)
        return self

    def __exit__(self, *_exception):
        self.rules.update(self.saved)
        return False


def self_test() -> dict:
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": str(detail)[:400]})

    tagger = RulesStepFunctionTagger()
    tests_skill = tagger.tag(StepFunctionMaterial("skill", "skill", "run-tests",
                                                  "Run the project's test suite and report each failing check.",
                                                  TEST_SKILL, ("skill_definition",)))
    runbook = tagger.tag(StepFunctionMaterial("instruction_file", "instruction_file", "release-runbook", "",
                                              DEPLOY_RUNBOOK, ("instruction_file",)))
    check("a_test_skill_is_tagged_verification_and_a_release_runbook_operating",
          "verification" in tests_skill.functions and tests_skill.functions[0] == "verification"
          and "operating" in runbook.functions and "verification" not in runbook.functions
          and all(basis for _function, basis in tests_skill.evidence),
          f"skill {tests_skill.functions}; runbook {runbook.functions}")

    # A script or a hook is something a harness runs: its roles say acting even when its words do not.
    scripted = tagger.tag(StepFunctionMaterial("skill", "skill", "hello", "", SCRIPT_ONLY,
                                               ("skill_definition", "skill_script")))
    hook = tagger.tag(StepFunctionMaterial("tool", "hook", "session-start", "", '{"hooks": {}}', ("hook",)))
    check("a_package_with_a_script_or_a_hook_is_tagged_acting_from_its_roles",
          scripted.functions == ("acting",) and hook.functions == ("acting",)
          and ("acting", "file role: skill_script") in scripted.evidence
          and ("acting", "harness kind: hook") in hook.evidence, (scripted.functions, hook.functions))
    with _without(ROLE_FUNCTIONS={}, HARNESS_KIND_FUNCTIONS={}):
        without_roles = tagger.tag(StepFunctionMaterial("skill", "skill", "hello", "", SCRIPT_ONLY,
                                                        ("skill_definition", "skill_script")))
    check("removed_role_rule_drops_the_acting_tag_of_a_script_package",
          scripted.functions == ("acting",) and without_roles.functions == (),
          f"with the rule {scripted.functions}; without {without_roles.functions}")

    # Silence is the honest answer: an item whose words name no function gets no tag and no attribute.
    plain = tagger.tag(StepFunctionMaterial("instruction_file", "instruction_file", "notes", "", PLAIN, ()))
    check("an_item_whose_words_name_no_function_gets_no_tag_and_no_attribute",
          plain.functions == () and plain.attribute_values() == {} and plain.evidence == ()
          and tests_skill.attribute_values() == {ATTRIBUTE_NAME: list(tests_skill.functions)},
          plain.to_dict())

    # One word alone is not enough: "check" once in a body must not tag verification.
    once = tagger.tag(StepFunctionMaterial("skill", "skill", "colours", "", "Check the header colour.\n", ()))
    with _without(MINIMUM_SCORE=1, BODY_ONLY_MINIMUM=1):
        once_without_threshold = tagger.tag(StepFunctionMaterial("skill", "skill", "colours", "",
                                                                 "Check the header colour.\n", ()))
    check("removed_score_threshold_tags_every_function_named_once",
          once.functions == () and once_without_threshold.functions == ("verification",),
          f"with the threshold {once.functions}; without {once_without_threshold.functions}")

    # Body words alone need four distinct matches (rules 1.1.0): three verification words in a text about a
    # door tag nothing; a fourth tags verification, with all four words in the evidence. One purpose word or
    # a role still suffices on its own.
    three = tagger.tag(StepFunctionMaterial("skill", "skill", "door", "", THREE_BODY_WORDS, ()))
    four = tagger.tag(StepFunctionMaterial("skill", "skill", "door", "", FOUR_BODY_WORDS, ()))
    purpose_word = tagger.tag(StepFunctionMaterial("skill", "skill", "door", "Verify the hinge.", PLAIN, ()))
    check("body_words_alone_need_four_distinct_matches_but_one_purpose_word_suffices",
          BODY_ONLY_MINIMUM == 4 and three.functions == () and four.functions == ("verification",)
          and [basis for function, basis in four.evidence] == ["text: check", "text: test", "text: validate",
                                                                "text: verify"]
          and purpose_word.functions == ("verification",)
          and tagger.describe()["body_only_minimum"] == BODY_ONLY_MINIMUM,
          f"three {three.functions}; four {four.functions}; purpose {purpose_word.functions}")
    with _without(BODY_ONLY_MINIMUM=2):
        three_without_minimum = tagger.tag(StepFunctionMaterial("skill", "skill", "door", "", THREE_BODY_WORDS, ()))
    check("removed_body_only_minimum_tags_three_incidental_body_words",
          three.functions == () and three_without_minimum.functions == ("verification",),
          f"with the minimum {three.functions}; without {three_without_minimum.functions}")

    # At equal scores, a function named in the purpose ranks above four body-only functions that precede it
    # in vocabulary order: "audit" in the purpose keeps reviewing within the four tags kept.
    audit = tagger.tag(StepFunctionMaterial("skill", "skill", "change-gate", "Audit the change.", CROWDED_BODY, ()))
    with _without(HEADLINE_FIRST=False):
        audit_by_order = tagger.tag(StepFunctionMaterial("skill", "skill", "change-gate", "Audit the change.",
                                                         CROWDED_BODY, ()))
    check("name_or_purpose_evidence_outranks_body_words_at_equal_score",
          audit.functions[0] == "reviewing" and len(audit.functions) == MAXIMUM_FUNCTIONS
          and all(tagger.scores(StepFunctionMaterial("skill", "skill", "change-gate", "Audit the change.",
                                                     CROWDED_BODY, ()))[function][0] == 2
                  for function in ("acting", "analysis", "building", "operating", "reviewing")),
          audit.functions)
    check("removed_headline_first_drops_the_audit_tag_behind_four_body_only_functions",
          "reviewing" in audit.functions and "reviewing" not in audit_by_order.functions,
          f"headline first {audit.functions}; vocabulary order only {audit_by_order.functions}")

    # The words the sample dropped no longer tag: "apply" is not acting, a planning pipeline is not
    # operating, creating a document is not building, and a pull request for approval is not reviewing.
    dropped = {"acting": "Apply the discount to the order.", "operating": "Planning pipeline for the feature.",
               "building": "Create a persona document.", "reviewing": "Open a pull request for approval."}
    now = {function: tagger.scores(StepFunctionMaterial("skill", "skill", "x", purpose, PLAIN, ()))[function][0]
           for function, purpose in dropped.items()}
    with _without(_PATTERNS=_patterns_with(DROPPED_WORDS)):
        before = {function: tagger.scores(StepFunctionMaterial("skill", "skill", "x", purpose, PLAIN, ()))[function][0]
                  for function, purpose in dropped.items()}
    check("dropped_words_no_longer_score_their_function", all(score == 0 for score in now.values()), now)
    check("removed_word_drops_score_apply_pipeline_create_and_pull_request_again",
          all(score == 0 for score in now.values()) and all(score >= 2 for score in before.values()),
          f"now {now}; with the dropped words back {before}")

    # The "-ing" forms the sample found missing tag their function from the purpose alone.
    added = {"building": "Use when implementing multiplayer.", "analysis": "Diagnosing why memories decay.",
             "verification": "Verifying a breach claim.", "reasoning": "Deciding between the two designs."}
    tagged = {function: tagger.tag(StepFunctionMaterial("skill", "skill", "x", purpose, PLAIN, ())).functions
              for function, purpose in added.items()}
    with _without(_PATTERNS=_patterns_without(ADDED_WORDS)):
        untagged = {function: tagger.tag(StepFunctionMaterial("skill", "skill", "x", purpose, PLAIN, ())).functions
                    for function, purpose in added.items()}
    check("added_ing_forms_tag_their_function_from_the_purpose",
          all(tagged[function] == (function,) for function in added), tagged)
    check("removed_added_words_leave_implementing_and_diagnosing_untagged",
          all(tagged[function] == (function,) for function in added) and all(functions == () for functions in untagged.values()),
          f"with the words {tagged}; without {untagged}")

    # The vocabulary is closed, the count bounded, the order fixed and the record round-trips.
    everything = " ".join(("deploy", "analyze", "build", "plan", "reason", "research", "review", "verify",
                           "draft", "execute")) * 2
    crowded = tagger.tag(StepFunctionMaterial("skill", "skill", "everything", everything, everything, ()))
    again = StepFunctionTags(crowded.functions, crowded.engine_id, crowded.engine_version, crowded.evidence)
    check("tags_are_a_closed_bounded_vocabulary_in_a_fixed_order",
          0 < len(crowded.functions) <= MAXIMUM_FUNCTIONS
          and all(function in STEP_FUNCTIONS for function in crowded.functions)
          and crowded.functions == tagger.tag(StepFunctionMaterial("skill", "skill", "everything", everything,
                                                                   everything, ())).functions
          and again.to_dict() == crowded.to_dict()
          and crowded.to_dict()["engine"] == {"engine_id": "step_function_rules", "engine_version": "1.1.0"}
          and _refused(lambda: StepFunctionTags(("acting", "dancing"), "x", "1"))
          and _refused(lambda: StepFunctionTags(tuple(STEP_FUNCTIONS[:MAXIMUM_FUNCTIONS + 1]), "x", "1"))
          and _refused(lambda: StepFunctionTags(("acting", "acting"), "x", "1"))
          and _refused(lambda: StepFunctionTags(("acting",), "", "1")),
          crowded.functions)

    # The attribute declaration is the served contract: a filterable, shown keyword list under the tag's name.
    check("the_attribute_declaration_names_the_tag_as_a_shown_filterable_keyword_list",
          STEP_FUNCTIONS_ATTRIBUTE["name"] == ATTRIBUTE_NAME
          and STEP_FUNCTIONS_ATTRIBUTE["type"] == "keyword_list"
          and STEP_FUNCTIONS_ATTRIBUTE["filterable"] and STEP_FUNCTIONS_ATTRIBUTE["shown"]
          and STEP_FUNCTIONS_ATTRIBUTE["searchable"]
          and all(function in STEP_FUNCTIONS_ATTRIBUTE["description"] for function in STEP_FUNCTIONS)
          and len(STEP_FUNCTIONS_ATTRIBUTE["description"]) <= 400, STEP_FUNCTIONS_ATTRIBUTE)

    # Material is validated and bounded: a number for a name is refused, a long text is cut at the bound.
    long_text = "verify " * (TEXT_BOUND // 3)
    bounded = StepFunctionMaterial("skill", "skill", "long", "", long_text, ())
    check("material_is_validated_and_its_text_is_bounded",
          _refused(lambda: StepFunctionMaterial("skill", "skill", 3, "", "", ()))
          and _refused(lambda: StepFunctionMaterial("skill", "skill", "n", "", None, ()))
          and _refused(lambda: StepFunctionMaterial("skill", "skill", "n", "", "", (1,)))
          and _refused(lambda: tagger.tag({"kind": "skill"}))
          and len(bounded.text) == TEXT_BOUND and bounded.to_dict()["record_type"] == "step_function_material/v1",
          len(bounded.text))

    # The entry text of a package is its primary file, never its licence or attribution.
    files = [("LICENSE", "other", "text/plain", "MIT License"), ("ATTRIBUTION.md", "other", "text/markdown", "# From"),
             ("scripts/run.py", "skill_script", "text/x-python", "print(1)"),
             ("SKILL.md", "skill_definition", "text/markdown", TEST_SKILL), ("image.png", "skill_asset", "image/png", None)]
    check("the_entry_text_is_the_primary_file_never_the_licence_or_attribution",
          entry_text(files) == TEST_SKILL
          and entry_text([files[0], files[1], ("notes/README.md", "skill_reference", "text/markdown", PLAIN)]) == PLAIN
          and entry_text([files[0], files[1], files[4]]) == "",
          entry_text(files)[:40])

    passed = sum(item["passed"] for item in tests)
    return {"record_type": "step_function_checks/v1", "tests": tests, "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
