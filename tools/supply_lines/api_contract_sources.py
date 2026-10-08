"""Read existing curated or APIs.guru facts for the same offline atom extractor.

Uses the owning readers' source selection, licence decisions and notice rules.
No source registry, network fallback or generated client execution is added.
"""
from __future__ import annotations

import json
import re
from enum import Enum

from . import api_contract_atoms as atoms
from . import openapi_directory as directory
from .declared_licences import LicenceTexts
from .openapi_operations import plain, read_sources, read_specification
from .reading import repository_notice
from .records import fact_source


class ApiContractSourceMode(str, Enum):
    CURATED = "curated"
    APIS_GURU = "apis-guru"


def load(reader, mode, wanted, *, maximum_specifications, maximum_source_bytes):
    mode = ApiContractSourceMode(mode)
    if (type(maximum_specifications) is not int or not 1 <= maximum_specifications <= 1000
            or type(maximum_source_bytes) is not int or maximum_source_bytes < 1):
        raise ValueError("source_resource_bound_required")
    loaded, findings, total_bytes = [], [], 0

    def keep(source, spec):
        nonlocal total_bytes
        if len(loaded) >= maximum_specifications or total_bytes + spec["size_bytes"] > maximum_source_bytes:
            findings.append({"source_id": source["source_id"], "path": spec["path"], "finding": "declared_source_bound"})
            return
        spec.setdefault("normalized_view_sha256", atoms.digest(spec["document"]))
        loaded.append((source, spec))
        total_bytes += spec["size_bytes"]

    if mode is ApiContractSourceMode.CURATED:
        declarations = {row["source_id"]: row for row in read_sources()}
        if not wanted or set(wanted) - declarations.keys():
            raise ValueError("unknown_or_missing_source")
        for identity in wanted:
            source = declarations[identity]
            for path in sorted(source["paths"]):
                if len(loaded) >= maximum_specifications or total_bytes >= maximum_source_bytes:
                    findings.append({"source_id": identity, "path": path, "finding": "declared_source_bound"})
                    continue
                before = len(reader.misses)
                try:
                    spec = read_specification(reader, source, path, LicenceTexts(reader))
                    if len(reader.misses) != before:
                        raise LookupError("source_notice_or_provenance_cache_incomplete")
                    # The curated reader converts Swagger 2 before returning.
                    # Name that view explicitly instead of pointing into raw Swagger bytes.
                    if spec.get("converted_from_swagger2"):
                        spec.update(pointer_basis="normalized_openapi_view", conversion="supply_lines.swagger2.swagger2_to_openapi3")
                    keep(source, spec)
                except (ValueError, LookupError, KeyError, TypeError, RecursionError) as error:
                    findings.append({"source_id": identity, "path": path, "finding": type(error).__name__, "reason": str(error)[:180]})
        return loaded, findings
    if mode is not ApiContractSourceMode.APIS_GURU:
        raise ValueError("source_mode_unsupported")
    listing, observation = directory.read_directory(reader)
    names = directory.selected(listing, wanted)
    if (not wanted or not names or any(name not in listing and not any(
            existing.partition(":")[0] == name for existing in listing) for name in wanted)):
        raise ValueError("unknown_or_missing_source")
    covered, origins, notices, aws_cache = directory.curated_coverage(read_sources()), {}, {}, {}
    texts = LicenceTexts(reader)
    for name in names:
        before = len(reader.misses)
        try:
            covering, sibling = directory.covering_source(name, covered), directory.stable_sibling(name, listing)
            if covering or sibling:
                findings.append({"source_id": name, "finding": "covered_elsewhere", "covered_by": covering or sibling})
                continue
            if len(loaded) >= maximum_specifications or total_bytes >= maximum_source_bytes:
                findings.append({"source_id": name, "finding": "declared_source_bound"})
                continue
            api = listing[name]
            version = api.get("preferred")
            entry = api.get("versions", {}).get(version, {})
            info = entry.get("info", {})
            decision = directory.decide(name, info, reader, texts, origins)
            if decision["decision"] != "agreed":
                findings.append({"source_id": name, "finding": decision["decision"]})
                continue
            answer = reader.get(entry["swaggerUrl"])
            if answer.status != 200:
                raise ValueError("source_status_not_200")
            document = plain(json.loads(answer.body))
            conversion = "none"
            if str(document.get("swagger", "")).startswith("2"):
                document = directory.swagger2_to_openapi3(document)
                conversion = "supply_lines.swagger2.swagger2_to_openapi3"
            if not str(document.get("openapi", "")).startswith("3"):
                raise ValueError("source_dialect_unsupported")
            licence = decision["licence"]
            extra_facts = [fact_source(observation.url, observation.retrieved_at, observation.sha256, len(observation.body),
                "registry_entry", spdx=directory.DIRECTORY_LICENCE, basis="directory_list_of_apis_guru")]
            notice_sources = []
            if decision["basis"] in (directory.ORIGIN_BASIS, directory.LICENCE_FILE_BASIS):
                notice_sources.append((licence.repository, licence.commit, licence.spdx))
            if name.split(":")[0] == directory.AWS_PROVIDER:
                found = directory.aws_metadata(reader, info, aws_cache)
                if found is not None:
                    _metadata, pinned, sdk_licence = found
                    extra_facts.append(fact_source(pinned["url"], pinned["retrieved_at"], pinned["sha256"], len(pinned["bytes"]),
                        "repository_facts", spdx=sdk_licence.spdx, basis="aws_sdk_model_metadata_at_the_pinned_commit",
                        evidence_sha256=sdk_licence.sha256))
                    notice_sources.append((directory.AWS_SDK_REPOSITORY, aws_cache["commit"], sdk_licence.spdx))
            carried_notices = []
            for repository, commit, spdx in notice_sources:
                key = (repository, commit)
                if key not in notices:
                    notices[key] = repository_notice(reader, repository, commit, spdx)
                carried_notices.append(notices[key])
            if len(reader.misses) != before:
                raise LookupError("source_notice_or_provenance_cache_incomplete")
            spec = {"document": document, "origin": "apis_guru_directory", "repository": "apis.guru/" + name.replace(":", "/"),
                "commit": f"version:{version};updated:{entry.get('updated', '')}",
                "path": answer.url.split(directory.DIRECTORY_HOST + "/", 1)[-1], "url": answer.url,
                "bytes": answer.body, "sha256": answer.sha256, "size_bytes": len(answer.body), "retrieved_at": answer.retrieved_at,
                "licence": licence, "declared_licence": None, "licence_basis": decision["basis"],
                "licence_text_basis": ("licence_file_at_the_pinned_commit" if decision["basis"] in
                                       (directory.ORIGIN_BASIS, directory.LICENCE_FILE_BASIS)
                                       else "licence_text_from_choosealicense_at_the_pinned_commit"),
                "notices": carried_notices, "extra_facts": extra_facts,
                "title": re.sub(r"\s+", " ", str(info.get("title") or name))[:80], "version": str(version or "")[:40],
                "pointer_basis": "pinned_openapi_document" if conversion == "none" else "normalized_openapi_view",
                "conversion": conversion}
            keep({"source_id": name}, spec)
        except (ValueError, LookupError, KeyError, TypeError, AttributeError, RecursionError) as error:
            findings.append({"source_id": name, "finding": type(error).__name__, "reason": str(error)[:180],
                             "missing_cache_keys": sorted(set(reader.misses[before:]))})
    return loaded, findings
