"""Closed metadata-only Kaggle selections, bound to the observed official SDK contract.

Service POSTs here are documented reads. No caller supplies a host, RPC name,
private view, account filter, download, rule acceptance or execution operation.
"""
from dataclasses import asdict, dataclass
import re

REQUEST = "kaggle_metadata_request/v1"
RESULT = "kaggle_metadata_result/v1"
ENGINE = "kaggle_sdk_metadata"
HOST = "api.kaggle.com"
KEY_VARIABLE = "KAGGLE_API_TOKEN"
COMPETITIONS, COMPETITION, PAGES, NOTEBOOKS, AUTH = "competitions", "competition", "pages", "notebooks", "check_auth"
OPERATIONS = (COMPETITIONS, COMPETITION, PAGES, NOTEBOOKS, AUTH)
PATHS = {COMPETITIONS: "/v1/competitions.CompetitionApiService/ListCompetitions",
         COMPETITION: "/v1/competitions.CompetitionApiService/GetCompetition",
         PAGES: "/v1/competitions.CompetitionApiService/ListCompetitionPages",
         NOTEBOOKS: "/v1/kernels.KernelsApiService/ListKernels",
         AUTH: "/v1/security.OAuthService/IntrospectToken"}
SORTS = {"votes": "VOTE_COUNT", "recent": "DATE_CREATED", "relevance": "RELEVANCE"}
MAXIMUM_BYTES = 1024 * 1024
MAXIMUM_REQUESTS = 20
RIGHTS = {"delivery": "private_metadata_only", "content_is_untrusted": True, "licence_verified": False,
          "raw_republication_allowed": False, "code_reuse_approved": False, "publication_approved": False,
          "execution_approved": False, "account_mutation_approved": False}
_SLUG = re.compile(r"[a-z0-9][a-z0-9-]{1,119}\Z")
_SECRET = re.compile(r"(?i)(kgat_|api[_ -]?token|api[_ -]?key|authorization|bearer|password|secret[=:])")


class KaggleError(ValueError):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def safe_query(value):
    return (type(value) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 ._+-]{0,159}", value)
            and not _SECRET.search(value))


def safe_cursor(value):
    return (type(value) is str and re.fullmatch(r"[A-Za-z0-9+/=_-]{1,512}", value)
            and not _SECRET.search(value))


@dataclass(frozen=True)
class KaggleRequest:
    operation: str
    competition: str | None = None
    query: str | None = None
    page: int = 1
    page_size: int = 10
    cursor: str | None = None
    sort: str = "votes"
    page_name: str | None = None

    def __post_init__(self):
        if self.operation not in OPERATIONS:raise KaggleError("kaggle_operation_refused")
        if self.competition is not None and (type(self.competition) is not str or not _SLUG.fullmatch(self.competition)):
            raise KaggleError("kaggle_competition_invalid")
        if self.query is not None and not safe_query(self.query):raise KaggleError("kaggle_public_query_invalid")
        if type(self.page) is not int or not 1 <= self.page <= 100:raise KaggleError("kaggle_page_bound")
        if type(self.page_size) is not int or not 1 <= self.page_size <= 20:raise KaggleError("kaggle_page_size_bound")
        if self.cursor is not None and (not safe_cursor(self.cursor) or self.page != 1):raise KaggleError("kaggle_cursor_invalid")
        if self.sort not in SORTS:raise KaggleError("kaggle_sort_invalid")
        if self.page_name is not None and (type(self.page_name) is not str or not re.fullmatch(r"[A-Za-z][A-Za-z0-9 -]{0,79}", self.page_name)):
            raise KaggleError("kaggle_page_name_invalid")
        if self.operation in (COMPETITION, PAGES) and not self.competition:raise KaggleError("kaggle_competition_required")
        if self.operation == COMPETITIONS and (self.competition is not None or not self.query):raise KaggleError("kaggle_search_required")
        if self.operation == NOTEBOOKS and not (self.competition or self.query):raise KaggleError("kaggle_notebook_scope_required")
        if self.operation not in (COMPETITIONS, NOTEBOOKS) and (self.query is not None or self.page != 1 or self.page_size != 10 or self.cursor is not None):
            raise KaggleError("kaggle_unused_selection_fields")
        if self.operation != NOTEBOOKS and self.sort != "votes":raise KaggleError("kaggle_unused_selection_fields")
        if self.operation != PAGES and self.page_name is not None:raise KaggleError("kaggle_unused_selection_fields")
        if self.operation == AUTH and self.competition is not None:raise KaggleError("kaggle_unused_selection_fields")
        if self.operation == NOTEBOOKS and self.sort == "relevance" and not self.query:raise KaggleError("kaggle_search_required")

    def to_record(self):
        return {"record_type": REQUEST, **asdict(self)}

    def body(self):
        if self.operation == AUTH:return {}
        if self.operation == COMPETITION:return {"competitionName": self.competition}
        if self.operation == PAGES:
            return {"competitionName": self.competition, **({"pageName": self.page_name} if self.page_name else {})}
        page = {"pageToken": self.cursor} if self.cursor else {"page": self.page}
        if self.operation == COMPETITIONS:
            return {"group": "COMPETITION_LIST_TAB_EVERYTHING", "category": "HOST_SEGMENT_UNSPECIFIED",
                    "sortBy": "COMPETITION_SORT_BY_RELEVANCE", "search": self.query, "pageSize": self.page_size, **page}
        return {"group": "EVERYONE", "kernelType": "all", "language": "all", "outputType": "all",
                "sortBy": SORTS[self.sort], "pageSize": self.page_size, **page,
                **({"competition": self.competition} if self.competition else {}), **({"search": self.query} if self.query else {})}


def read_request(value):
    if type(value) is not dict or value.get("record_type") != REQUEST:raise KaggleError("kaggle_request_version")
    if set(value) - set(KaggleRequest.__dataclass_fields__) - {"record_type"}:raise KaggleError("kaggle_request_fields")
    try:return KaggleRequest(**{key: item for key, item in value.items() if key != "record_type"})
    except TypeError:raise KaggleError("kaggle_request_fields") from None
