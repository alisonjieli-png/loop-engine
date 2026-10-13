"""Closed selection of passive website renderers behind the shared HTTP owner.

The HTTP boundary chooses a profile after exact Host and Origin admission.
This module selects packaged pages and explicit shared assets only; it does
not create accounts, call providers or configure customer execution.
"""


def renderer_for(brand):
    """Return only a packaged presentation, never import a caller-supplied module."""
    if brand == "agentfeeds":
        from . import agentfeeds_pages
        return agentfeeds_pages
    if brand == "agentfoundry":
        from . import agentfoundry_pages
        return agentfoundry_pages
    if brand == "agentafk":
        from . import agentafk_pages
        return agentafk_pages
    if brand == "meatproxy":
        from . import meatproxy_pages
        return meatproxy_pages
    raise ValueError("unsupported service brand presentation")


COMMON_ASSETS = frozenset(("/assets/geist.woff2", "/assets/geist-mono.woff2",
                          "/assets/third-party-notices.txt"))
AGENTFEEDS_ASSETS = frozenset(("/assets/supabase-client.js", "/assets/oauth-consent.js",
                             "/assets/feed-profile.js"))


def shared_assets(renderer):
    """Additional shared assets are explicit packaged paths, not prefix grants."""
    declared = getattr(renderer, "SHARED_ASSETS", frozenset())
    if not isinstance(declared, frozenset) or any(
            not isinstance(path, str) or not path.startswith("/assets/")
            or any(piece in ("", ".", "..") for piece in path[1:].split("/"))
            or any(character in path for character in ("?", "#", "\\", "%"))
            for path in declared):
        raise ValueError("brand shared assets require exact packaged paths")
    from . import agentfeeds_pages
    return COMMON_ASSETS | declared | (AGENTFEEDS_ASSETS if renderer is agentfeeds_pages else frozenset())
