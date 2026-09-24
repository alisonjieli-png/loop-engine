"""Plain wording for every refusal the hosted service returns.

The transport in `http.py` owns the code and the status. This module owns the
two sentences that travel with them: what happened, and what to do next. It
holds no policy and makes no decision, so a refusal cannot become more or less
permissive by passing through here.

`guidance` answers for any code. A code with wording of its own gets that
wording. Any other code falls back to wording chosen by the HTTP status, so a
refusal nobody anticipated still tells a reader whether to fix the request,
fetch a credential, wait, or report the problem. Nothing here repeats a field
from the request, so a refusal cannot reflect a caller's text back to them.
"""
from __future__ import annotations

#: What a status class means to the person or agent that received it. This is
#: the general answer. It is used for every code without its own wording,
#: which is most of them: most codes name a host configuration fault that a
#: customer cannot reach or repair.
STATUS_GUIDANCE = {
    400: ("The service could not accept this request as written.",
          "Compare the request with the setup guide, correct the field it names, and send it again."),
    401: ("The service did not accept the credential on this request.",
          "Sign in again, or set a current service token in your client, then retry."),
    403: ("This account is not permitted to perform that operation.",
          "Ask the person who runs this service to grant the operation, then retry."),
    404: ("The service has nothing at that address or under that identity.",
          "Check the address or the item identity against the setup guide, then retry."),
    405: ("The service does not answer that address with this request method.",
          "Use the method the setup guide names for that address."),
    408: ("The service stopped waiting for the rest of the request.",
          "Send the request again over a working connection."),
    409: ("The stored state changed before this request was applied, so nothing was changed.",
          "Reload the current state, decide again from what you see, then send a new request."),
    413: ("The request or its answer was larger than this service accepts.",
          "Ask for less in one request, then repeat for the rest."),
    415: ("The service reads JSON on this address and the request was not JSON.",
          "Send the request with the header Content-Type: application/json."),
    421: ("This service does not answer for the host name in the request.",
          "Use the service address the setup guide names."),
    429: ("Too many failed attempts came from this caller, so the service paused them.",
          "Wait for the period the Retry-After header names, fix the cause, then retry."),
    500: ("The service failed while handling this request and did not finish it.",
          "Retry once. If it fails again, report the time and the code to the person who runs this service."),
    501: ("This release does not carry the part of the service that request needs.",
          "Ask the person who runs this service which release offers it."),
    503: ("A part of the service this request needs is not available right now.",
          "Wait and retry. If it stays unavailable, report the code to the person who runs this service."),
    504: ("The service ran out of its allowed time before it finished this request.",
          "Retry the same request. Keep the same request identity so nothing is counted twice."),
}
#: Wording for the refusals a customer actually meets. The set is deliberately
#: small: a refusal earns an entry here when a person using the website, a
#: client connected to the service or an agent calling the interface can
#: produce it, because for those the general status wording is not enough to
#: act on. A host configuration fault keeps the status wording.
CODE_GUIDANCE = {
    "unauthorized": ("The service did not accept the credential on this request.",
                     "Check that the Authorization header carries a current Baltor service token. "
                     "Create or replace one on your account page, then retry."),
    "key_expired": ("The service token on this request has passed its expiry time.",
                    "Create a new token on your account page, put it in your client's secret settings, then retry."),
    "key_revoked": ("The service token on this request was revoked.",
                    "Create a new token on your account page, put it in your client's secret settings, then retry."),
    "tenant_disabled": ("The account this token belongs to is switched off.",
                        "Ask the person who runs this service to enable the account."),
    "subject_unbound": ("This sign-in is not yet bound to a service account.",
                        "Ask the person who runs this service to bind your account, then sign in again."),
    "browser_session_required": ("This operation needs a signed-in browser session, not a service token.",
                                 "Sign in on the website and repeat the operation there."),
    "verified_email_required": ("This account has not confirmed its email address yet.",
                                "Open the confirmation link that was emailed to you, then sign in again."),
    "account_origin_unverified": ("This sign-in was not created through Baltor's sign-up, so the service does "
                                  "not open it.",
                                  "Create your account on the Get started page with the same email address. "
                                  "The service replaces the earlier sign-in and emails you a link."),
    "staff_role_required": ("Only Baltor staff can open the administration pages.",
                            "Sign in with a staff account, or use the account page for your own account."),
    "account_administration_forbidden": ("Your staff role does not include that operation.",
                                         "Ask a superadmin to make the change."),
    # The staff tools, September 24, 2026. A staff member's protocol client, or
    # an operator agent, reads these to choose its next call.
    "staff_credential_required": ("This address answers staff keys only, and the request carried none.",
                                  "Create a staff key on the Administration page, set it in your client, then retry."),
    "staff_key_expired": ("The staff key on this request has passed its expiry time.",
                          "Create a new staff key on the Administration page and put it in your client."),
    "staff_key_revoked": ("A superadmin revoked the staff key on this request.",
                          "Create a new staff key on the Administration page and put it in your client."),
    "staff_key_role_changed": ("The staff list no longer gives this key's staff member the same role.",
                               "Ask a superadmin to create a new key for your current role."),
    "staff_tool_forbidden": ("Your staff role does not include this tool or this operation.",
                             "Ask a superadmin to run it, or use a tool your role includes."),
    "plan_changed": ("The state or the arguments moved after the plan, so nothing was applied.",
                     "Call the tool again with step plan, read the new plan, then apply that one."),
    "plan_digest_required": ("An apply must name the digest of the plan it carries out.",
                             "Call the tool with step plan first, then apply with the digest it returned."),
    "staff_mail_daily_cap_reached": ("Staff messages today have used the daily allowance, so nothing was sent.",
                                     "Send the rest after midnight UTC, or ask the host to raise the allowance."),
    "marketing_needs_recorded_consent": ("Baltor records no marketing consent, so it sends no marketing message.",
                                         "Send a service message with a service purpose, or send nothing."),
    "message_service_purpose_required": ("A staff message needs one of the service purposes, and this one had none.",
                                         "Name an account, service, security or support reply purpose, then plan again."),
    "address_search_forbidden": ("Your role reads counts only, and an address filter would reveal an account.",
                                 "Search without the text filter, or ask a superadmin to search."),
    "staff_account_protected": ("A staff tool never switches off the account of a staff member.",
                                "Change the staff list in the host file first if that is intended."),
    "insufficient_scope": ("This token is not allowed to perform that operation.",
                           "Create a token that includes the operation you need, then retry with it."),
    "scope_required": ("This token is not allowed to perform that operation.",
                       "Create a token that includes the operation you need, then retry with it."),
    "scope_denied": ("This token is not allowed to perform that operation.",
                     "Create a token that includes the operation you need, then retry with it."),
    "body_forbidden": ("This account may search for that item but may not download its body.",
                       "Ask the person who runs this service for download access to that item."),
    "download_requires_read": ("Downloading a body needs the download operation, and this token does not have it.",
                               "Create a token that includes downloading permitted material, then retry."),
    "entitlement_required": ("This account has no current subscription or beta entitlement.",
                             "Open your account page and start a subscription, or ask for a beta invitation."),
    "item_unavailable": ("No item with that identity is available to this account.",
                         "Search again and take the identity from the result, then retry."),
    "route_unavailable": ("This service has no page or interface at that address.",
                          "Check the address against the setup guide, or start again from the home page."),
    "invalid_query": ("The search text was empty, too long, or not a string.",
                      "Send a search text of at least one character and within the published length limit."),
    "invalid_search_limit": ("The requested number of results is outside what this service returns.",
                             "Ask for a whole number of results within the limit the capabilities record names."),
    "unsupported_retrieval_mode": ("That retrieval method is not one this service offers.",
                                   "Use a method the capabilities record lists under retrieval modes."),
    "unsupported_operation": ("That operation is not one this address performs.",
                              "Use an operation the setup guide names for this address."),
    "unsupported_version": ("The record version in this request is not one this release accepts.",
                            "Send the record version the setup guide names. Do not reuse an older version."),
    "unknown_request_field": ("The request carried a field this service does not know.",
                              "Remove the field the refusal names and send only the documented fields."),
    "invalid_json": ("The request body was not valid JSON.",
                     "Send a single JSON object with no trailing text and no repeated field."),
    "object_required": ("The request body was valid JSON but not a JSON object.",
                        "Send a JSON object at the top level, not a list, number or string."),
    "invalid_request": ("One field in this request did not match the documented shape.",
                        "Compare the request with the schema in the setup guide, correct it, then send it again."),
    "unsupported_media_type": ("The service reads JSON on this address and the request was not JSON.",
                               "Send the request with the header Content-Type: application/json."),
    "request_identity_required": ("This operation needs a request identity so a retry is not counted twice.",
                                  "Add a request_id you generate, and reuse exactly that value if you retry."),
    "download_required": ("A body this large is not returned inline.",
                          "Ask for the body at the download address instead, using the same selected digest."),
    "download_limit_exceeded": ("This item is larger than the download size this service serves.",
                                "Ask the person who runs this service whether a smaller form of the item exists."),
    "response_limit_exceeded": ("The answer to this request was larger than this service sends.",
                                "Ask for fewer results or a smaller item, then repeat for the rest."),
    "selected_body_digest_mismatch": ("The stored item no longer matches the version this request selected.",
                                      "Search again, take the current digest from the result, then download that."),
    "request_limit_exceeded": ("Too many failed attempts came from this caller, so the service paused them.",
                               "Wait for the period the Retry-After header names, correct the credential, then retry."),
    "failed_attempt_limit_reached": ("Too many requests with a credential this service refused came from this "
                                     "caller, so it paused them.",
                                     "Wait for the period the Retry-After header names, put a current token in "
                                     "your client, then retry."),
    "service_busy": ("Every worker in this service is busy, so the request was not started.",
                     "Retry in a few seconds. Nothing was changed and nothing was counted."),
    "deadline_exceeded": ("The service ran out of its allowed time before it finished this request.",
                          "Retry the same request with the same request identity so nothing is counted twice."),
    "request_body_deadline": ("The service stopped waiting for the rest of the request body.",
                              "Send the request again over a working connection."),
    "invalid_host": ("This service does not answer for the host name in the request.",
                     "Use the service address the setup guide names."),
    "invalid_origin": ("A browser sent this request from a page this service does not serve.",
                       "Use the website at this service's own address."),
    "unsupported_protocol_version": ("The client asked for a protocol version this release does not speak.",
                                     "Use a version the capabilities record lists, then reconnect."),
    "external_authorization_not_configured": ("This service does not offer a browser authorization flow for "
                                              "native clients.",
                                              "Connect with a service token from your account page instead."),
    "account_registration_unavailable": ("Public account creation is not open on this service.",
                                         "Ask the person who runs this service for an invitation."),
    "identity_provider_unavailable": ("The sign-in provider did not answer, so the request was not completed.",
                                      "Wait and try to sign in again. Your account was not changed."),
    "identity_key_set_unavailable": ("The sign-in provider's signing keys could not be read, so no sign-in "
                                     "could be checked.",
                                     "Wait and try to sign in again. Your account was not changed."),
    "client_access_unavailable": ("Managing your own client tokens is not switched on for this service.",
                                  "Ask the person who runs this service to issue a token for you."),
    "access_administration_unavailable": ("Token administration is not switched on for this service.",
                                          "Ask the person who runs this service to perform the change."),
    "access_token_limit_reached": ("This account already holds as many active tokens as it may.",
                                   "Revoke a token you no longer use on your account page, then create the new one."),
    "access_token_history_limit_reached": ("This account has kept as many token records as it may.",
                                           "Ask the person who runs this service to clear older token records."),
    "access_token_already_revoked": ("That token was already revoked, so nothing changed.",
                                     "Reload your token list to see the current state."),
    "access_request_identity_conflict": ("That request identity was already used for a different request.",
                                         "Reload your token list. Use a new request identity for a new request."),
    "concurrent_update": ("Another change to the same record was applied first, so this one was not.",
                          "Reload the current state, decide again from what you see, then send a new request."),
    "billing_sessions_not_installed": ("Subscription checkout is not switched on for this service.",
                                       "Nothing charges you today. Ask the person who runs this service about payment."),
    "billing_webhook_unavailable": ("The payment provider's notifications are not switched on for this service.",
                                    "Ask the person who runs this service to finish the payment configuration."),
    "billing_commit_unknown": ("The payment provider did not confirm the outcome, so it is unknown.",
                               "Do not repeat the payment. Check your account page, then ask for reconciliation."),
    "commit_unknown": ("The service could not confirm whether this change was stored.",
                       "Do not repeat it. Reload the current state first, then decide."),
    "meter_commit_unknown": ("The service could not confirm whether this usage record was stored.",
                             "Do not repeat the request. Check your usage record before trying again."),
    "billing_reconciliation_pending": ("A payment change is still being reconciled, so this request was refused.",
                                       "Wait, reload your account page, then decide from the state you see."),
    "billing_customer_not_bound": ("This account is not yet bound to a payment customer.",
                                   "Start a subscription from your account page first."),
    "billing_signature_required": ("This notification carried no provider signature, so it was refused.",
                                   "Send provider notifications through the configured signed webhook only."),
    "invalid_account_activation": ("This activation link is not valid, or it was already used.",
                                   "Request a new confirmation email, then open the newest link."),
    # The waiting list is the one form a stranger can send without signing in,
    # so each of its refusals says what happened in the words of that form.
    "waitlist_address_invalid": ("That email address is not one this service can write to.",
                                 "Check the address for a typing mistake, then send the request again."),
    "waitlist_note_invalid": ("The note was too long or held characters this service does not keep.",
                              "Shorten the note to plain text within the length the form allows, then send it again."),
    "waitlist_address_already_listed": ("This email address is on the waiting list already, so nothing was added.",
                                        "Wait for a person to read the request you already sent."),
    "waitlist_address_has_account": ("This email address already belongs to an account on this service.",
                                     "Sign in with that address instead of joining the waiting list."),
    "waitlist_source_flooded": ("Too many requests to join the list came from this connection in a short time.",
                                "Wait a while, then send the request again. Requests already accepted are kept."),
    "waitlist_unavailable": ("This service does not keep a waiting list, so nothing was recorded.",
                             "Ask the person who runs this service for an invitation instead."),
    # The flood guard could not key its count, so the request was refused
    # rather than counted in a weaker way. Nothing about the caller caused it.
    "waitlist_source_secret_unavailable": ("This service cannot take requests to join the list right now, "
                                           "so nothing was recorded.",
                                           "Try again later. If it keeps happening, tell the person who runs "
                                           "this service."),
    "waitlist_source_secret_unusable": ("This service cannot take requests to join the list right now, "
                                        "so nothing was recorded.",
                                        "Try again later. If it keeps happening, tell the person who runs "
                                        "this service."),
    "unsupported_waitlist_request": ("The request to join the list did not carry the documented fields.",
                                     "Send the record version, the email address and an optional note, and nothing else."),
    # Catalogue releases. A customer meets these when an item leaves the
    # library, when a search names a detail it may not filter on, and when a
    # download names a file its package does not hold.
    "item_withdrawn": ("This version of the item was taken out of the library, so it is no longer delivered.",
                       "Search again and choose a current item, or ask the person who runs this service why."),
    "search_filter_not_allowed": ("The search named a detail that this catalogue does not offer for filtering.",
                                  "Filter only on the details the search results show, or search without a filter."),
    "search_filter_invalid": ("The search filter was not written in a form this service reads.",
                              "Use equals, any_of, or at_least and at_most with values of the detail's own type."),
    "package_file_not_found": ("The item's package holds no file at the path this download named.",
                               "Read the item's package list first, then download one of the paths it names."),
    "package_file_requires_download": ("A single file of a package is delivered through the download address.",
                                       "Send the same request to the download address instead of this one."),
}


def guidance(code, status):
    """Return the two sentences that travel with one refusal.

    `code` is the exact refusal code. `status` is the HTTP status the
    transport chose for it. Wording for the code wins; otherwise the status
    decides, and an unrecognised status is treated as a service fault, which
    is the safe reading when the transport itself produced something
    unexpected.
    """
    if code in CODE_GUIDANCE:
        return CODE_GUIDANCE[code]
    return STATUS_GUIDANCE.get(int(status), STATUS_GUIDANCE[500])


def self_test():
    """Check that the wording is usable, and that it never names a secret."""
    tests = []

    def check(name, passed):
        tests.append({"test": name, "passed": bool(passed),
                      "detail": "refusal wording table; no transport and no provider"})

    pairs = [*CODE_GUIDANCE.items(), *[(str(k), v) for k, v in STATUS_GUIDANCE.items()]]
    # A sentence that only repeats the code, or stops before naming an action,
    # is the defect this module exists to remove.
    check("every_refusal_states_what_happened_and_what_to_do_next",
          bool(pairs) and all(
              isinstance(message, str) and isinstance(action, str)
              and message.endswith(".") and action.endswith(".")
              and len(message.split()) >= 5 and len(action.split()) >= 5
              and key.replace("_", " ") not in message.lower()
              for key, (message, action) in pairs))
    # A refusal is read by someone who is already confused. Wording that names
    # a credential value, or tells a reader to send one somewhere, would be
    # read as an instruction to expose it.
    forbidden = ("password", "secret key", "api key", "bearer ", "sk_", "le_", "authorization: ")
    check("no_refusal_wording_names_or_asks_for_a_secret_value",
          not any(word in (message + " " + action).lower()
                  for _key, (message, action) in pairs for word in forbidden))
    # The general answer must cover every status the transport chooses, or a
    # refusal falls through to wording written for a different situation.
    from .http import _status_classes_in_use
    check("the_general_wording_covers_every_status_the_transport_chooses",
          set(_status_classes_in_use()) <= set(STATUS_GUIDANCE))
    return {"tests": tests}
