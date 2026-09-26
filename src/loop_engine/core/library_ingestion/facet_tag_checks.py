"""Known-wrong checks for the facet tagger, run offline with no model and no network.

Each check names the input that must be tagged, refused or left untagged.
The controls whose names start with ``removed_`` run a check with one rule
taken away and confirm that the check would then fail: without the body
phrase minimum one word said twice in a body is tagged, without the
shared-phrase rule the phrase "purchasing agents" tags the first of the two
titles that claim it, without the script rule a Chinese text has no
language, without the Latin-majority guard a Ukrainian text is called
English, without the letters that mark Persian and Ukrainian a Persian text
is called Arabic and a Ukrainian text Russian, and with the words the three
hand checks removed put back, a
security auditor is tagged as an accountant, a rendering step as analytics,
manufacturing and media, and a scaffolding step as construction and
healthcare.
"""
from __future__ import annotations

from .record_rules import LibraryRecordError
from .facet_tags import (
    FACET_ATTRIBUTES, FACETS, GEOGRAPHIES, INDUSTRIES, JOB_TITLES, LANGUAGES, LEVELS, MAXIMUM_VALUES,
    PHRASE_FACETS, TEXT_BOUND, FacetMaterial, FacetTags, RulesFacetTagger, facet_vocabulary, read_vocabulary,
    title_phrases, vocabulary_record)

CLINICAL_SKILL = ("# Clinical notes\n\nUse this skill in a hospital. Software developers who maintain the EHR "
                  "integration run it. Ship to the USA and the EU.\n")
PLAIN = "# Notes\n\nThe colour of the header is navy. The footer repeats the address.\n"
AGENTS_FILE = ("# Agents\n\nAgents read records. The agents write records and the judges score them. The test "
               "runners and the installers run first. Cooks and cooks and cooks.\n")
SPANISH = ("Este archivo explica cómo usar el sistema. Los archivos se guardan aquí y también en el servidor. "
           "Cuando hay un error, puede revisar los registros y hacer una copia. Los usuarios pueden pedir ayuda "
           "si tienen dudas, pero deben leer esto primero.\n")
CHINESE = "这是一个用于代码审查的技能。请在提交之前运行测试，并记录每一个失败的检查。该技能不会调用网络。\n"
JAPANESE = "これはコードレビューのためのスキルです。提出する前にテストを実行し、失敗したチェックをすべて記録してください。\n"
KOREAN = "이것은 코드 리뷰를 위한 스킬입니다. 제출하기 전에 테스트를 실행하고 실패한 검사를 모두 기록하십시오.\n"
RUSSIAN = ("Это навык для проверки кода. Запустите тесты перед отправкой и запишите каждую неудачную проверку. "
           "Его можно использовать каждый день.\n")
UKRAINIAN = ("Це навичка для перевірки коду. Запустіть тести перед надсиланням і запишіть кожну невдалу перевірку. "
             "Її можна використовувати щодня.\n")
ARABIC = "هذه مهارة لمراجعة الشيفرة. شغّل الاختبارات قبل الإرسال وسجّل كل فحص فاشل. لا تستدعي هذه المهارة الشبكة.\n"
PERSIAN = "این یک مهارت برای بازبینی کد است. پیش از ارسال آزمون‌ها را اجرا کنید و هر بررسی ناموفق را ثبت کنید.\n"
HINDI = "यह कोड समीक्षा के लिए एक कौशल है। भेजने से पहले परीक्षण चलाएँ और हर असफल जाँच को दर्ज करें।\n"


def _refused(build) -> bool:
    try:
        build()
    except LibraryRecordError:
        return True
    return False


def _material(name: str, purpose: str, text: str, roles=()) -> FacetMaterial:
    return FacetMaterial("skill", "skill", name, purpose, text, roles)


class _without:
    """Run one check with a rule of the tagger module replaced, then put the rule back whatever happens.

    The rules are the module globals the tagger's own functions read; they are reached through the tagger's
    function rather than by importing the module object, which keeps this check's imports within the boundary."""

    def __init__(self, **replacements):
        self.replacements = replacements
        self.rules = RulesFacetTagger.scores.__globals__
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

    tagger = RulesFacetTagger()
    vocabulary = facet_vocabulary()
    clinical = tagger.tag(_material("clinical-notes-summarizer", "Summarize clinical notes for physicians in "
                                    "United States hospitals, written for senior software developers.",
                                    CLINICAL_SKILL, ("skill_definition",)))
    check("a_skill_for_developers_in_hospitals_is_tagged_by_title_industry_level_place_and_language",
          clinical.values[JOB_TITLES] == ("Software Developers",) and clinical.values[INDUSTRIES] == ("healthcare",)
          and clinical.values[LEVELS] == ("senior",) and clinical.values[GEOGRAPHIES] == ("United States",)
          and clinical.values[LANGUAGES] == ("english",)
          and (JOB_TITLES, "Software Developers", "name or purpose: software developers") in clinical.evidence
          and all(basis for _facet, _value, basis in clinical.evidence)
          and clinical.to_dict()["engine"] == {"engine_id": "facet_rules", "engine_version": "1.0.0"},
          clinical.values)

    # Silence is the honest answer: an item whose words name nothing gets no value, and only the language
    # facet answers, with the default.
    plain = tagger.tag(_material("notes", "", PLAIN))
    check("an_item_whose_words_name_nothing_gets_no_value_but_the_default_language",
          all(plain.values[facet] == () for facet in PHRASE_FACETS) and plain.values[LANGUAGES] == ("english",)
          and plain.attribute_values() == {LANGUAGES: ["english"]}
          and plain.evidence == ((LANGUAGES, "english", "default: no other language reached its threshold"),)
          and clinical.attribute_values().get(JOB_TITLES) == ["Software Developers"],
          plain.to_dict())

    # One mention in the name or purpose is enough. The body alone needs two distinct phrases: a word said
    # once, or said twice ("lawyer", "lawyers" count once), names nothing; "lawyer" and "attorney" do. A hand
    # check of 100 tags found body-only tags wrong 19 of 49 times, mostly one word said twice in a long body.
    once = tagger.tag(_material("sign", "", "Ask a lawyer before you sign.\n"))
    twice = tagger.tag(_material("sign", "", "Ask a lawyer before you sign. Two lawyers read the terms.\n"))
    distinct = tagger.tag(_material("sign", "", "Ask a lawyer before you sign. An attorney reads the terms.\n"))
    headline = tagger.tag(_material("sign", "Ask a lawyer before you sign.", ""))
    one_phrase_body = _material("planner", "Review the quality of a plan.",
                                "The plan is the vehicle for the work. A weak vehicle fails. Check the vehicle.\n")
    with _without(MINIMUM_BODY_PHRASES=1):
        twice_without_rule = tagger.tag(_material("sign", "", "Ask a lawyer before you sign. Two lawyers read "
                                                  "the terms.\n")).values[JOB_TITLES]
        vehicle_without_rule = tagger.tag(one_phrase_body).values[INDUSTRIES]
    check("a_value_named_by_the_body_alone_needs_two_distinct_phrases",
          once.values[JOB_TITLES] == () and twice.values[JOB_TITLES] == ()
          and distinct.values[JOB_TITLES] == ("Lawyers",) and headline.values[JOB_TITLES] == ("Lawyers",)
          and tagger.tag(one_phrase_body).values[INDUSTRIES] == (),
          f"once {once.values[JOB_TITLES]}; twice {twice.values[JOB_TITLES]}; distinct {distinct.values[JOB_TITLES]}")
    check("removed_body_phrase_minimum_tags_one_word_said_twice_in_the_body",
          twice.values[JOB_TITLES] == () and twice_without_rule == ("Lawyers",)
          and tagger.tag(one_phrase_body).values[INDUSTRIES] == () and vehicle_without_rule == ("automotive",),
          f"with the rule (); without {twice_without_rule} and {vehicle_without_rule}")

    # "agents", "records", "judges", "runners" and "cooks" are cut from joined titles and are everywhere in
    # harness material, so they are never phrases; "purchasing agents" belongs to two titles, so it names none.
    # The words are in the purpose, where one mention is enough, so the check tests the phrase rule itself.
    agents = tagger.tag(_material("AGENTS", AGENTS_FILE, ""))
    joined = title_phrases("Agents and Business Managers of Artists, Performers, and Athletes")
    check("a_single_word_cut_from_a_joined_title_and_a_phrase_several_titles_share_name_none",
          agents.values[JOB_TITLES] == () and "agents" not in joined and "business managers of artists" in joined
          and "business manager of artists" in joined and "cooks" not in vocabulary.phrases[JOB_TITLES]
          and "purchasing agents" in vocabulary.shared_phrases[JOB_TITLES]
          and "purchasing agents" not in vocabulary.phrases[JOB_TITLES]
          and title_phrases("Software Developers", ("programmer",)) == ("software developers", "software developer",
                                                                        "programmer")
          and title_phrases("Lawyers") == ("lawyers", "lawyer")
          and title_phrases("Cooks, Fast Food") == ("cooks, fast food",),
          f"tags {agents.values[JOB_TITLES]}; joined phrases {joined}")
    without_rule = RulesFacetTagger(read_vocabulary(vocabulary_record(), drop_shared=False))
    buyers = without_rule.tag(_material("buying", "Purchasing agents order stock.", ""))
    check("removed_shared_phrase_rule_tags_one_title_from_a_phrase_two_titles_share",
          tagger.tag(_material("buying", "Purchasing agents order stock.", "")).values[JOB_TITLES] == ()
          and buyers.values[JOB_TITLES] == ("Buyers and Purchasing Agents, Farm Products",),
          f"with the rule (); without {buyers.values[JOB_TITLES]}")

    # The language comes from the script or the stopwords; English is the default for a Latin text only.
    languages = {name: tagger.tag(_material(name, "", text)).values[LANGUAGES]
                 for name, text in (("spanish", SPANISH), ("chinese", CHINESE), ("japanese", JAPANESE),
                                    ("korean", KOREAN), ("russian", RUSSIAN), ("ukrainian", UKRAINIAN))}
    bilingual = tagger.tag(_material("both", "", SPANISH + "\n" + PLAIN * 4))
    spanish_evidence = [basis for facet, value, basis in tagger.tag(_material("es", "", SPANISH)).evidence
                        if facet == LANGUAGES and value == "spanish"]
    check("the_language_comes_from_the_script_or_the_stopwords_and_english_is_the_default",
          languages == {"spanish": ("spanish",), "chinese": ("chinese",), "japanese": ("japanese",),
                        "korean": ("korean",), "russian": ("russian",), "ukrainian": ()}
          and set(bilingual.values[LANGUAGES]) == {"english", "spanish"}
          and spanish_evidence and spanish_evidence[0].startswith("stopwords: ")
          and tagger.tag(_material("", "", "")).values[LANGUAGES] == (),
          f"{languages}; bilingual {bilingual.values[LANGUAGES]}")
    with _without(MINIMUM_SCRIPT_SHARE=2.0):
        chinese_without_script = tagger.tag(_material("zh", "", CHINESE)).values[LANGUAGES]
    check("removed_script_rule_leaves_a_chinese_text_without_its_language",
          languages["chinese"] == ("chinese",) and chinese_without_script == (),
          f"with the rule {languages['chinese']}; without {chinese_without_script}")
    with _without(LATIN_MAJORITY=0.0):
        ukrainian_without_guard = tagger.tag(_material("uk", "", UKRAINIAN)).values[LANGUAGES]
    check("removed_latin_majority_guard_calls_a_ukrainian_text_english",
          languages["ukrainian"] == () and ukrainian_without_guard == ("english",),
          f"with the guard {languages['ukrainian']}; without {ukrainian_without_guard}")

    # Arabic script also writes Persian and Urdu, and Cyrillic also writes Ukrainian: the letters only those
    # languages use keep such a text out of arabic or russian, so it gets no language rather than a wrong one.
    # Devanagari is hindi. The mutant forgets the marking letters and shows the check would fail.
    scripts = {name: tagger.tag(_material(name, "", text)).values[LANGUAGES]
               for name, text in (("arabic", ARABIC), ("persian", PERSIAN), ("hindi", HINDI))}
    check("a_text_in_a_shared_script_gets_its_language_only_without_the_letters_of_another",
          scripts == {"arabic": ("arabic",), "persian": (), "hindi": ("hindi",)}, scripts)
    with _without(_NOT_ARABIC=frozenset(), _NOT_RUSSIAN=frozenset()):
        persian_without_letters = tagger.tag(_material("fa", "", PERSIAN)).values[LANGUAGES]
        ukrainian_without_letters = tagger.tag(_material("uk", "", UKRAINIAN)).values[LANGUAGES]
    check("removed_marking_letters_call_a_persian_text_arabic_and_a_ukrainian_text_russian",
          scripts["persian"] == () and languages["ukrainian"] == ()
          and persian_without_letters == ("arabic",) and ukrainian_without_letters == ("russian",),
          f"without the letters {persian_without_letters} and {ukrainian_without_letters}")

    # A word with a software meaning is not evidence of an industry, a title or a level. Tagging 6,877
    # candidate items on September 26, 2026 found "auditor" behind 119 of 137 job title tags, "expert"
    # behind 126 of 131 senior tags, and "claim", "dashboard", "engagement", "environment", "resume",
    # "lesson", "interview", "flight", "inventory", "dispatch" and "escalation" behind most wrong industry
    # tags in a hand check of 100, so the vocabulary lists only their longer forms (insurance claim, job
    # interview). The mutant puts "auditor" back on the accountants' title and shows the check would fail.
    software_words = _material("security-auditor", "A security auditor subagent. Resume the engagement from "
                               "the trace. Validate the .env environment.",
                               "A claim needs evidence. The dashboard shows the inventory of lessons and the "
                               "fleet of workers. Dispatch the escalation to an expert. Of course the interview "
                               "of the process supervisor and the director resumes after the flight.\n")
    record = vocabulary_record()
    titles = record["facets"][JOB_TITLES]
    auditor_back = {**record, "facets": {**record["facets"], JOB_TITLES: {**titles, "values": [
        {**entry, "also_known_as": [*entry.get("also_known_as", []), "auditor"]}
        if entry["value"] == "Accountants and Auditors" else entry for entry in titles["values"]]}}}
    with_auditor = RulesFacetTagger(read_vocabulary(auditor_back)).tag(software_words)
    check("words_with_a_software_meaning_name_no_industry_title_or_level",
          all(tagger.tag(software_words).values[facet] == () for facet in PHRASE_FACETS)
          and tagger.tag(_material("claims", "Process insurance claims for a claims adjuster.", "")).values[INDUSTRIES]
          == ("insurance",)
          and tagger.tag(_material("hiring", "Prepare job interview questions for the recruiter.", "")).values[INDUSTRIES]
          == ("human resources",),
          tagger.tag(software_words).values)
    check("removed_software_word_exclusion_tags_a_security_auditor_as_an_accountant",
          tagger.tag(software_words).values[JOB_TITLES] == ()
          and with_auditor.values[JOB_TITLES] == ("Accountants and Auditors",),
          f"with the rule (); without {with_auditor.values[JOB_TITLES]}")

    # A second hand check, of 100 tags drawn after that repair, still found bare words with a common software
    # or figurative sense behind wrong tags: analytics (four wrong, none correct), media (three wrong),
    # animation (two wrong, one arguable), single wrong tags from streaming, agency, regulations, nuclear,
    # ecosystems, plumbing, construction and factory, and project manager behind one wrong and one arguable
    # lead tag (a project manager is a job title, not a level). The vocabulary keeps only their industry
    # forms (nuclear power, construction site, factory floor, data analytics). The mutant puts analytics,
    # factory and media back and shows the check would fail.
    # Every word is in the purpose, where one mention is enough, so the check tests the vocabulary itself.
    senses = _material("stream-render", "Stream the API response, add web analytics and a CSS animation for the "
                       "media query, call the factory function during construction of the component, wire the "
                       "storage plumbing into the npm ecosystem, let the agency read the regulations, and keep the "
                       "nuclear option for the project manager.", "")
    industry_forms = {"energy": _material("plant", "Plan maintenance at a nuclear power plant.", ""),
                      "construction": _material("site", "Keep the safety log of a construction site.", ""),
                      "manufacturing": _material("floor", "Schedule shifts on the factory floor.", ""),
                      "data and analytics": _material("bi", "Build data analytics reports.", "")}
    kept_forms = {industry: tagger.tag(material).values[INDUSTRIES] for industry, material in industry_forms.items()}
    check("words_with_a_software_or_figurative_sense_name_no_industry_or_level",
          tagger.tag(senses).values[INDUSTRIES] == () and tagger.tag(senses).values[LEVELS] == ()
          and all(kept_forms[industry] == (industry,) for industry in industry_forms),
          {"senses": tagger.tag(senses).values, "industry forms": kept_forms})
    industries = record["facets"][INDUSTRIES]
    put_back = {"data and analytics": "analytics", "manufacturing": "factory", "media and entertainment": "media"}
    words_back = {**record, "facets": {**record["facets"], INDUSTRIES: {**industries, "values": [
        {**entry, "phrases": [*entry["phrases"], put_back[entry["value"]]]} if entry["value"] in put_back else entry
        for entry in industries["values"]]}}}
    with_words = RulesFacetTagger(read_vocabulary(words_back)).tag(senses)
    check("removed_second_software_word_exclusion_tags_a_render_step_as_analytics_manufacturing_and_media",
          tagger.tag(senses).values[INDUSTRIES] == () and set(with_words.values[INDUSTRIES]) == set(put_back),
          f"with the rule (); without {with_words.values[INDUSTRIES]}")

    # The third hand check, of 100 tags from the approved items of a reviewed folder, found scaffolding,
    # utility, utilities, advisory, doctor and dataset each behind at least two wrong tags and at most one
    # correct one (code scaffolding, test utilities, security advisories, a doctor command), and recipes and
    # battery behind a wrong tag each in their common software sense. The vocabulary keeps their industry forms.
    tooling = _material("scaffold-and-check", "Generate CRUD scaffolding and test utilities, run the doctor "
                        "command, read the security advisory, load the dataset, follow the build recipes and save "
                        "battery on the phone.", "")
    third_forms = {"energy": _material("grid", "Plan outages for an electric utility.", ""),
                   "consulting": _material("firm", "Staff the engagements of an advisory firm.", ""),
                   "healthcare": _material("rota", "Plan the rota of the doctors on a ward.", "")}
    third_kept = {industry: tagger.tag(material).values[INDUSTRIES] for industry, material in third_forms.items()}
    check("tooling_words_name_no_industry_but_their_industry_forms_do",
          tagger.tag(tooling).values[INDUSTRIES] == ()
          and all(third_kept[industry] == (industry,) for industry in third_forms),
          {"tooling": tagger.tag(tooling).values[INDUSTRIES], "industry forms": third_kept})
    doctor_back = {"healthcare": "doctor", "construction": "scaffolding"}
    third_back = {**record, "facets": {**record["facets"], INDUSTRIES: {**industries, "values": [
        {**entry, "phrases": [*entry["phrases"], doctor_back[entry["value"]]]} if entry["value"] in doctor_back
        else entry for entry in industries["values"]]}}}
    with_tooling = RulesFacetTagger(read_vocabulary(third_back)).tag(tooling).values[INDUSTRIES]
    check("removed_third_word_exclusion_tags_a_scaffolding_step_as_construction_and_healthcare",
          tagger.tag(tooling).values[INDUSTRIES] == () and set(with_tooling) == set(doctor_back),
          f"with the rule (); without {with_tooling}")

    # An upper-case abbreviation is matched exactly, and a longer name wins over a shorter name inside it.
    abbreviations = tagger.tag(_material("ship", "Ship to the USA and the EU.", "Lower-case usa and eu are words.\n"))
    korea = tagger.tag(_material("region", "Deploy for customers in North Korea.", ""))
    surveyor = tagger.tag(_material("survey", "A checklist for a geodetic surveyor.", ""))
    check("an_abbreviation_is_matched_exactly_and_a_longer_name_wins_over_a_shorter_one",
          abbreviations.values[GEOGRAPHIES] == ("United States", "European Union")
          and tagger.tag(_material("ship", "", "usa usa eu eu\n")).values[GEOGRAPHIES] == ()
          and korea.values[GEOGRAPHIES] == ("North Korea",)
          and surveyor.values[JOB_TITLES] == ("Geodetic Surveyors",),
          f"{abbreviations.values[GEOGRAPHIES]}; {korea.values[GEOGRAPHIES]}; {surveyor.values[JOB_TITLES]}")

    # The values are a closed, bounded vocabulary in a fixed order, and the record round-trips.
    # An item that names twelve titles keeps the six that score highest; the tagger cuts, so the record's own
    # refusal of a seventh value is never what stops it.
    crowded_titles = " ".join(f"{title.lower()} {title.lower()}" for title in vocabulary.values[JOB_TITLES][:12])
    try:
        crowded, crowded_refusal = tagger.tag(_material("everything", crowded_titles, crowded_titles)), ""
    except LibraryRecordError as error:
        crowded, crowded_refusal = FacetTags({}, "refused", "0"), str(error)
    again = FacetTags(crowded.values, crowded.engine_id, crowded.engine_version, crowded.evidence)
    check("tags_are_bounded_distinct_declared_values_that_name_their_engine",
          not crowded_refusal and 0 < len(crowded.values[JOB_TITLES]) <= MAXIMUM_VALUES[JOB_TITLES]
          and all(value in vocabulary.values[JOB_TITLES] for value in crowded.values[JOB_TITLES])
          and again.to_dict() == crowded.to_dict()
          and crowded.to_dict()["record_type"] == "facet_tags/v1"
          and _refused(lambda: FacetTags({JOB_TITLES: ("Dancers",)}, "x", "1"))
          and _refused(lambda: FacetTags({"moods": ("calm",)}, "x", "1"))
          and _refused(lambda: FacetTags({LEVELS: ("senior", "senior")}, "x", "1"))
          and _refused(lambda: FacetTags({LEVELS: ("student", "junior", "mid", "senior")}, "x", "1"))
          and _refused(lambda: FacetTags({LEVELS: ("senior",)}, "", "1"))
          and _refused(lambda: FacetTags({LEVELS: ("senior",)}, "x", "1", ((LEVELS, "junior", "text: junior"),)))
          and not _refused(lambda: FacetTags({}, "x", "1")),
          crowded_refusal or crowded.values[JOB_TITLES])

    # The attribute declarations are the served contract: five filterable, shown keyword lists named after
    # the facets; the language is not searched, because the default would enter every item's index.
    check("the_attribute_declarations_are_five_filterable_shown_keyword_lists_named_after_the_facets",
          tuple(attribute["name"] for attribute in FACET_ATTRIBUTES) == FACETS
          and all(attribute["type"] == "keyword_list" and attribute["filterable"] and attribute["shown"]
                  and 0 < len(attribute["description"]) <= 400 for attribute in FACET_ATTRIBUTES)
          and [attribute["searchable"] for attribute in FACET_ATTRIBUTES] == [True, True, True, False, True],
          [attribute["name"] for attribute in FACET_ATTRIBUTES])

    # The vocabulary is read exactly: its counts, its clean stopword lists, and the refusals of a bad record.
    record = vocabulary_record()
    bad_field = {**record, "owner": "x"}
    bad_script = {**record, "facets": {**record["facets"], LANGUAGES: {
        **record["facets"][LANGUAGES], "values": [*record["facets"][LANGUAGES]["values"],
                                                   {"value": "elvish", "description": "x", "script": "tengwar"}]}}}
    boolean_stopword = {**record, "facets": {**record["facets"], LANGUAGES: {
        **record["facets"][LANGUAGES], "values": [{"value": "english", "description": "x", "stopwords": ["the", False]},
                                                   *record["facets"][LANGUAGES]["values"][1:]]}}}
    twice_declared = {**record, "facets": {**record["facets"], LEVELS: {
        **record["facets"][LEVELS], "values": record["facets"][LEVELS]["values"] * 2}}}
    unknown_source = {**record, "facets": {**record["facets"], JOB_TITLES: {
        **record["facets"][JOB_TITLES], "values": [{"value": "Dancers", "source": "guess", "code": "0"}]}}}
    check("the_vocabulary_is_read_exactly_and_a_bad_record_is_refused",
          vocabulary.version and len(vocabulary.values[JOB_TITLES]) >= 150
          and "Software Developers" in vocabulary.values[JOB_TITLES] and "Data Engineer" in vocabulary.values[JOB_TITLES]
          and all(vocabulary.descriptions[JOB_TITLES][title].startswith(("grid ", "seed "))
                  for title in vocabulary.values[JOB_TITLES])
          and 30 <= len(vocabulary.values[INDUSTRIES]) <= 40
          and all(vocabulary.descriptions[INDUSTRIES][value] for value in vocabulary.values[INDUSTRIES])
          and vocabulary.values[LEVELS] == ("student", "junior", "mid", "senior", "lead", "executive")
          and len(vocabulary.values[LANGUAGES]) == 12 and vocabulary.values[LANGUAGES][0] == "english"
          and len(vocabulary.values[GEOGRAPHIES]) >= 80
          and vocabulary.shared_stopwords == () and all(vocabulary.stopwords[language] for language in vocabulary.stopwords)
          and all(_refused(lambda bad=bad: read_vocabulary(bad))
                  for bad in (bad_field, bad_script, boolean_stopword, twice_declared, unknown_source)),
          {facet: len(vocabulary.values[facet]) for facet in FACETS})

    # Material is validated and bounded: a number for a name is refused, a long text is cut at the bound.
    long_text = "lawyer " * (TEXT_BOUND // 3)
    bounded = _material("long", "", long_text)
    check("material_is_validated_and_its_text_is_bounded",
          _refused(lambda: FacetMaterial("skill", "skill", 3, "", "", ()))
          and _refused(lambda: FacetMaterial("skill", "skill", "n", "", None, ()))
          and _refused(lambda: FacetMaterial("skill", "skill", "n", "", "", (1,)))
          and _refused(lambda: tagger.tag({"kind": "skill"}))
          and len(bounded.text) == TEXT_BOUND and bounded.to_dict()["record_type"] == "facet_material/v1",
          len(bounded.text))

    passed = sum(item["passed"] for item in tests)
    return {"record_type": "facet_tag_checks/v1", "tests": tests, "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
