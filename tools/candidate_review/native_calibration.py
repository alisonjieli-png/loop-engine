"""Frozen complete-package controls behind the existing calibration and review-panel edges."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from .calibration import CalibrationItem
from .native import NativeCatalogue, json_document, regular_bytes
from .records import (
    SHA256,
    digest,
    read_part,
    read_record,
    refuse,
    sha256_hex,
    text_field,
)
from .verdicts import APPROVE, DECISIONS, REJECT

NATIVE_CALIBRATION_SET = "candidate_native_review_calibration_set/v1"
NATIVE_CALIBRATION_ITEM = "candidate_native_review_calibration_item/v1"
DEFAULT_SET = Path(__file__).resolve().parent / "resources/native-calibration/calibration-set.json"
ITEM_FIELDS = ("identity", "base_identity", "package_digest", "expected_decision", "criterion_id", "defect")


@dataclass(frozen=True)
class NativeCalibrationItem(CalibrationItem):
    package_digest: str

    def to_dict(self):
        return {**super().to_dict(), "record_type": NATIVE_CALIBRATION_ITEM, "package_digest": self.package_digest}


@dataclass(frozen=True)
class NativeCalibrationSet:
    purpose: str
    items: tuple
    sha256: str
    catalogue: NativeCatalogue
    package_digests: MappingProxyType
    source_package_identity: str
    source_package_digest: str

    @classmethod
    def load(cls, path: Path, repository: Path, criteria):
        repository = Path(repository).resolve()
        try:
            relative = Path(path).absolute().relative_to(repository).as_posix()
        except ValueError:
            refuse("native_calibration_path_invalid", "a calibration set is a repository-bound reviewed resource")
        value = read_record(json_document(regular_bytes(repository, relative, 1024 * 1024)), NATIVE_CALIBRATION_SET,
            ("purpose", "catalogue_path", "catalogue_items_sha256", "source_package_identity", "source_package_digest", "items"))
        # regular_bytes owns traversal and symlink refusal, including every parent.
        catalogue_path = text_field(value["catalogue_path"], "control catalogue path", limit=200)
        inventory = regular_bytes(repository, catalogue_path + "/items.json", 1024 * 1024)
        if sha256_hex(inventory) != value["catalogue_items_sha256"]:
            refuse("native_calibration_inventory_changed", "the frozen control inventory changed")
        catalogue = NativeCatalogue.load(repository / catalogue_path, repository)
        raw_items = value["items"]
        if type(raw_items) is not list or not 2 <= len(raw_items) <= 32:
            refuse("native_calibration_population_invalid", "a calibration set needs two to 32 declared controls")
        source_identity = text_field(value["source_package_identity"], "source package identity", limit=96)
        if type(value["source_package_digest"]) is not str or not SHA256.fullmatch(value["source_package_digest"]):
            refuse("native_calibration_source_invalid", "a source package needs its exact digest")
        items, digests = [], {}
        for raw in raw_items:
            row = read_part(raw, "native calibration item", ITEM_FIELDS)
            identity = row["identity"]
            if (type(identity) is not str or identity in digests or identity not in catalogue.identities()
                    or row["base_identity"] != source_identity or identity == source_identity):
                refuse("native_calibration_identity_invalid", "each control has one neutral identity and a bound source")
            if (row["package_digest"] != catalogue.item(identity)["reference"]["digest"]
                    or row["expected_decision"] not in DECISIONS or type(row["criterion_id"]) is not str
                    or row["criterion_id"] not in criteria.ids):
                refuse("native_calibration_binding_invalid", "a control needs its exact package digest, label and native criterion")
            defect = text_field(row["defect"], "control explanation", limit=2000)
            items.append(NativeCalibrationItem(identity, source_identity, row["expected_decision"], row["criterion_id"],
                                               defect, (), {}, row["package_digest"]))
            digests[identity] = row["package_digest"]
        if set(digests) != set(catalogue.identities()) or {item.expected_decision for item in items} != {APPROVE, REJECT}:
            refuse("native_calibration_population_invalid", "the exact population must include benign and known-wrong controls")
        return cls(text_field(value["purpose"], "calibration purpose", limit=2000), tuple(items), digest(value), catalogue,
                   MappingProxyType(digests), source_identity, value["source_package_digest"])

    def requests(self, catalogue, producers, criteria, instructions_sha256):
        """Labels stay on CalibrationItem; only the ordinary immutable native request reaches the model."""
        if (catalogue is not None and self.source_package_identity in catalogue.identities()
                and catalogue.item(self.source_package_identity)["reference"]["digest"] != self.source_package_digest):
            refuse("native_calibration_source_changed", "the calibration source identity now names another package")
        return tuple((item, self.catalogue.request(item.identity, self.catalogue.producer_for(item.identity), criteria,
                                                   instructions_sha256)) for item in self.items)

    def population(self, population):
        """Exclude the deliberately related controls and their exact declared base, never unrelated items."""
        excluded = {item.identity for item in self.items} | {self.source_package_identity}
        return {identity: body for identity, body in population.items() if identity not in excluded}
