"""One bounded Hugging Face benchmark leaderboard through knowledge_radar_source/v1.

The documented upstream leaderboard endpoint is reused; no benchmark or
ranking engine is invented. Keep reported scores and verification flags
distinct from local execution. Dataset/result reuse rights remain separate,
so the source contract permits live lookup rather than feed republication.
"""
from __future__ import annotations

import math
import re
from urllib.parse import quote, urlunsplit

from loop_engine.core.library_ingestion.request_log import RequestCeilingReached
from loop_engine.core.library_ingestion.https_transport import HTTPS_SCHEME
from loop_engine.core.record_operations_records import parse_json

from .engines import (FAILED, OK, PARTIAL, EngineAnswer, RadarEngineError, ReadContext,
                      clean_title, limit_of, observation, parameter)
from .engines_network import _status_answer

HOST = "huggingface.co"
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,95}/[A-Za-z0-9][A-Za-z0-9._-]{0,95}\Z")
RESULT_FILE = re.compile(r"\.eval_results/[A-Za-z0-9][A-Za-z0-9._/-]{0,180}\.ya?ml\Z")


def identifier(value):
    return isinstance(value, str) and bool(IDENTIFIER.fullmatch(value)) and ".." not in value


def result_filename(value):
    return (isinstance(value, str) and bool(RESULT_FILE.fullmatch(value))
            and all(part not in (".", "..", "") for part in value.split("/")[1:]))


def finite_score(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


class HuggingFaceBenchmarkLeaderboard:
    engine_id, engine_version = "huggingface_benchmark_leaderboard", "1.0.0"
    material_facts = ("benchmark_dataset", "model_id", "reported_score", "reported_rank", "source_verified",
                      "lower_is_better", "evaluation_filename", "evaluation_pull_request")

    def read(self, context: ReadContext) -> EngineAnswer:
        dataset = parameter(context, "dataset", kind=str)
        if not identifier(dataset):
            raise RadarEngineError("radar_parameter_invalid", "dataset must be one Hugging Face owner/repository identity")
        limit = limit_of(context, 60)
        if type(limit) is not int:
            raise RadarEngineError("radar_parameter_invalid", "limit must be an integer, not a boolean")
        if set(context.binding.parameters) - {"dataset", "limit"}:
            raise RadarEngineError("radar_parameter_invalid", "leaderboard parameters are dataset and limit")
        path = "/api/datasets/" + dataset + "/leaderboard"
        address = urlunsplit((HTTPS_SCHEME, HOST, path, "", ""))
        try:
            response = context.network.get(self.engine_id, HOST, path)
        except (RadarEngineError, RequestCeilingReached, OSError) as error:
            return EngineAnswer(FAILED, str(error), complete=False)
        if response.status != 200:
            result = _status_answer(response.status, "the Hugging Face benchmark leaderboard")
            return EngineAnswer(result.status, result.reason, requests=1, complete=False)
        try:
            data = parse_json(response.body)
        except ValueError:
            data = None
        if not isinstance(data, list):
            return EngineAnswer(FAILED, "the leaderboard response is not an entry list", requests=1, complete=False)
        rows, excluded, seen = [], [], set()
        # The transport bounds response bytes. This output bound is explicit,
        # and no unseen cursor/page is assumed to have been read.
        for item in data[:limit]:
            if not isinstance(item, dict) or not identifier(item.get("modelId")):
                excluded.append(("redacted leaderboard row", "model identity missing or invalid"))
                continue
            score, rank = item.get("value"), item.get("rank")
            if (not finite_score(score)
                    or type(rank) is not int or rank < 1):
                excluded.append((item["modelId"], "finite numeric score and positive integer rank required"))
                continue
            filename, pull = item.get("filename"), item.get("pullRequest")
            if filename is not None and not result_filename(filename):
                excluded.append((item["modelId"], "evaluation result filename is invalid"))
                continue
            if pull is not None and (type(pull) is not int or pull < 1):
                excluded.append((item["modelId"], "evaluation pull request is invalid"))
                continue
            identity = (item["modelId"], filename, pull)
            if identity in seen:
                excluded.append((item["modelId"], "repeated result identity in the same response"))
                continue
            seen.add(identity)
            verified = item.get("verified") if type(item.get("verified")) is bool else None
            direction = item.get("lower_is_better") if type(item.get("lower_is_better")) is bool else None
            key = "hf-benchmark:" + dataset + ":" + item["modelId"] + ":" + str(filename or "") + ":" + str(pull or "")
            title, _reason = clean_title(item["modelId"] + " on " + dataset)
            rows.append(observation(context, self, key=key, origin="hf:" + item["modelId"],
                title=title,
                url=urlunsplit((HTTPS_SCHEME, HOST, "/datasets/" + quote(dataset, safe="/"), "", "")),
                source_address=address, licence=None,
                licence_basis="result and benchmark reuse rights have not been qualified",
                facts={"benchmark_dataset": dataset, "model_id": item["modelId"],
                       "reported_score": score, "reported_rank": rank, "source_verified": verified,
                       "lower_is_better": direction,
                       "evaluation_filename": filename, "evaluation_pull_request": pull,
                       "local_execution_verified": False,
                       "comparison_limit": "benchmark revision, harness, metric definition and measurement date are unreported"}))
        if len(data) > limit:
            excluded.append(("remaining leaderboard rows", "declared output limit reached"))
        complete = not excluded
        return EngineAnswer(OK if complete else PARTIAL,
                            "Public reported results; no local benchmark or cross-protocol comparison established",
                            tuple(rows), 1, (), tuple(excluded), complete=complete)


ENGINES = (HuggingFaceBenchmarkLeaderboard(),)
