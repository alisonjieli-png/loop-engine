"""Stateless customer exports of the existing per-agent reading-profile contract.

Only public registered source identities enter this operation. It returns exact
passive files, keeps no settings, performs no source reads and grants no effects.
The host supplies the date, and a pinned directory protects a changed selection.
"""
from datetime import datetime, timezone
from hashlib import sha256
from html import escape

from . import feed_profiles as profiles

PATH = "/api/v1/feeds/profile"
REQUEST = "agent_feed_profile_export_request/v1"
RESULT = "agent_feed_profile_export/v1"
MAXIMUM_REQUEST_BYTES = 8192
MAXIMUM_RESPONSE_BYTES = 131072
_FIELDS = frozenset(("record_type", "directory_digest", "agent_label", "collection_ids", "topics",
    "source_ids", "excluded_source_ids", "report_format", "requested_poll_interval_minutes"))


def export(fields, *, directory=None, today=None, origin=None):
    """Compile bounded files; date injection is for checks, never a request field."""
    if type(fields) is not dict or set(fields) != _FIELDS or fields.get("record_type") != REQUEST:
        raise profiles.FeedProfileError("feed_profile_export_contract")
    data = directory if directory is not None else profiles.current_directory()
    if fields["directory_digest"] != data.digest:
        raise profiles.FeedProfileError("feed_profile_directory_changed")
    day = today if today is not None else datetime.now(timezone.utc).date().isoformat()
    request = profiles.read_request({"record_type": profiles.REQUEST,
        **{key: fields[key] for key in _FIELDS - {"record_type", "directory_digest"}},
        "mode": "both", "max_items": 128, "max_bytes": profiles.MAXIMUM_BYTES,
        "max_age_days": 30, "on_stale": "hold", "on_partial": "refuse", "as_of": day})
    profile, bodies, native = profiles.compile_files(request, data, origin=origin)
    result = {"record_type": RESULT, "profile": profile, "native_package": native,
        "files": [{"path": path, "content": body.decode("utf-8"), "sha256": sha256(body).hexdigest(),
                   "size_bytes": len(body), "media_type": "application/json" if path.endswith(".json") else "text/markdown"}
                  for path, body in bodies.items()],
        "hosted_settings_saved": False, "scheduled": False, "upstream_requests": 0, "effects_granted": []}
    if len(profiles.canonical(result)) > MAXIMUM_RESPONSE_BYTES:
        raise profiles.FeedProfileError("feed_profile_export_byte_limit")
    return result


def page_section():
    """Render a compact accessible editor over the same packaged source directory."""
    data = profiles.current_directory()
    collection_options = "".join('<option value="' + escape(item.id, quote=True) + '">' + escape(item.title) + '</option>'
                                 for item in data.collections)
    source_options = "".join('<option value="' + escape(item.id, quote=True) + '">' + escape(item.name) + '</option>'
                             for item in data.sources)
    return ('<section class="md-band" id="feed-profile" aria-labelledby="feed-profile-title">'
        '<p class="eyebrow">Your agents, your sources</p><h2 id="feed-profile-title">Make a reading profile for each agent.</h2>'
        '<p class="md-reading">Choose sources for a coding assistant, a design researcher or any other agent. '
        'Download its JSON settings and reading guide, then add both files to that agent\'s working folder. '
        'Your harness owns scheduling and source access.</p>'
        '<details class="feed-profile-editor"><summary>Customize and download a profile</summary>'
        '<form id="feed-profile-form" data-directory-digest="' + data.digest + '">'
        '<div class="feed-profile-fields"><label>Agent label<input name="agent_label" required maxlength="64" '
        'pattern="[A-Za-z0-9][A-Za-z0-9 _.\\-]{0,63}" placeholder="Design researcher" autocomplete="off"></label>'
        '<label>Report format<select name="report_format"><option value="markdown">Markdown</option>'
        '<option value="json">JSON</option></select></label><label>Requested reading interval'
        '<select name="requested_poll_interval_minutes"><option value="1440">Every day</option>'
        '<option value="60">Every hour</option><option value="360">Every 6 hours</option>'
        '<option value="10080">Every week</option></select></label></div>'
        '<label>Collections<select name="collection_ids" multiple size="5">' + collection_options + '</select></label>'
        '<p class="md-reading">Choose several with Ctrl or Command. You can also choose individual sources below.</p>'
        '<details><summary>Choose individual sources</summary><div class="feed-profile-fields">'
        '<label>Additional sources<select name="source_ids" multiple size="5">' + source_options + '</select></label>'
        '<label>Sources to leave out<select name="excluded_source_ids" multiple size="5">' + source_options + '</select></label>'
        '</div></details><p class="md-reading">Only the selected source IDs enter the profile. The reading interval is a '
        'preference for your harness to configure. Baltor returns the files directly; settings stay in the files you save.</p>'
        '<div class="md-actions"><button class="button primary" type="submit">Build reading profile</button>'
        '<button class="button secondary" type="reset">Start another agent</button></div>'
        '<p id="feed-profile-status" role="status" aria-live="polite"></p>'
        '<div id="feed-profile-downloads" class="md-actions" hidden></div>'
        '<noscript><p>Turn on JavaScript to build a profile, or use the collection links below.</p></noscript>'
        '</form></details></section>')
