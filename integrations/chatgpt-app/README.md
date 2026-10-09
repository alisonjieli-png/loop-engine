# Baltor plugin package for ChatGPT and Codex

Kind: submission package. This folder is what the owner uploads to OpenAI's
plugin portal (<https://platform.openai.com/plugins>) to list Baltor in the
directory that ChatGPT and Codex share. The requirements it answers, with the
source and the date each was read, are in
[the ChatGPT app guide](../../docs/guides/chatgpt-app.md).

| File | What it holds |
|---|---|
| `plugin.json` | The Agent Plugins manifest. OpenAI's settings sit under `extensions.com.openai`: the listing (name, subtitle, description, category, capabilities, the four HTTPS addresses, three starter prompts, brand colours, icons and screenshots), five positive and three negative review cases, the commerce declaration (none) and the release notes. |
| `mcp.json` | The one remote server: `https://baltor.ai/mcp`, Streamable HTTP. |
| `assets/logo.png`, `assets/icon.png` | The Baltor mark, rendered from `src/loop_engine/core/service_runtime/web_assets/baltor-mark.svg` at 512 and 256 pixels. |
| `assets/screenshot-1.png` to `-3.png` | One screenshot for each starter prompt, 706 pixels wide, made by `tools/check_chatgpt_app_live.py --screens` from the live service's answers and the view it serves. |

## Check and build

```bash
PYTHONPATH=src:tools python tools/build_chatgpt_app_package.py --check
PYTHONPATH=src:tools python tools/build_chatgpt_app_package.py --zip baltor-plugin-1.0.0.zip
```

The check applies every final-submission rule OpenAI states for a remote MCP
plugin, the website's wording rules, and two cross-checks with the service:
each tool a review case names is a tool the server advertises, and the server
address is the service's own `/mcp`. The archive leaves this README out and
has fixed timestamps, so the same package always gives the same SHA-256.
`tools/test_build_chatgpt_app_package.py` holds every rule to a known-wrong
package.

## What the dashboard takes that the package does not

OpenAI refuses reviewer credentials in a package. These are entered in the
portal by the owner:

- **Reviewer credentials.** A dedicated Baltor account that signs in with an
  email address and a password, with no code by email or text message. Make
  it through Baltor's own sign-up at <https://baltor.ai/get-started> with an
  address the owner reads, choose its password on the page the link opens,
  then have a superadmin grant it free monthly Baltor Pro from Administration
  so that every review case can download. Enter the address, the password and
  the sign-in page <https://baltor.ai/login> in **Review details**. Keep the
  account for later reviews.
- **The demonstration video.** Record the five positive and three negative
  cases in ChatGPT on the web and on a phone, with the app connected, and give
  the recording's address. The cases are in `plugin.json`.
- **Domain verification.** The portal shows a token. Put it in the host file
  as `http.openai_apps_challenge` and restart; the service then answers
  `https://baltor.ai/.well-known/openai-apps-challenge` with exactly that
  token.
- **Annotation justifications**, if the portal asks for them: the table in
  [the guide](../../docs/guides/chatgpt-app.md#annotation-justifications).

## Prove it on the live service

After the release that serves the OpenAI presentation, with a fresh account
made by `node tools/check_live_account_journeys.mjs https://baltor.ai REPORT.json --fresh-only`:

```bash
PYTHONPATH=src:tools python tools/check_chatgpt_app_live.py https://baltor.ai REPORT.json \
  --account ~/baltor-private/<folder>/fresh-account-state.json \
  --evidence ~/baltor-private/<folder>/run --expect-presentation --screens integrations/chatgpt-app/assets
```

It signs in through OAuth in a real browser, searches, opens a package,
downloads its files and checks each SHA-256, downloads a Public Good file,
refreshes and then revokes its own delegation, and remakes the screenshots
from the view the service serves.
