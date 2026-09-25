# Sources of the MCP server and agent API directory

This page records where the public directory at `/directory` reads its
listings, what each source's terms allow, and the decisions taken on
September 24, 2026. The build command is `tools/build_mcp_directory.py`.

## Sources, in order of trust

When several sources list the same offering, the directory shows one row that
names every source. The most trusted source speaks for the row, and a less
trusted source fills only a fact the others leave unknown.

| Order | Source | How it is read | Terms observed on September 24, 2026 | Decision |
| --- | --- | --- | --- | --- |
| 1 | Official MCP Registry, `registry.modelcontextprotocol.io` | The public list interface, `GET /v0.1/servers?version=latest`, paged by cursor; later runs add `updated_since` | The aggregator guide asks downstream aggregators to read on a regular but infrequent basis, for example hourly. The terms dedicate listing metadata to the public domain under CC0 1.0 and allow the sentence "This data comes from the Official MCP Registry" without implying affiliation. The registry states that namespace verification is not a security review. | Read once a day. The page names the registry with the allowed sentence and says that a listing is not a security review. |
| 2 | Baltor research of September 23, 2026 | The committed extract `tools/resources/mcp-directory-codex-research.json` of the research list (1,000 integrations selected from 35,293 registry rows) | Baltor's own research | Reused for package licences as npm and PyPI reported them. Its 353 recorded registry pages can also start a new state folder (`seed`). |
| 3 | Publisher documentation | A reviewed file, `tools/resources/mcp-directory-publisher-documentation.json`, when present | Each publisher's own page | The file holds no offering yet on September 24, 2026: each one needs a reviewer to open the publisher's page first. An offering added here names the page that documents it. |
| 3 | GitHub MCP directory, `api.mcp.github.com` | The public list interface, three pages | GitHub's interface terms forbid using an interface for spam or to sell users' personal information, and limit excessive requests. | Read for server names, places to get them, code repositories and the licence GitHub reports. Its README copies, pictures and star counts are not read or shown. |
| 4 | Docker MCP Catalog, `github.com/docker/mcp-registry` | The source archive at the commit its main branch names | The repository is under the MIT License. | Read for images, remote endpoints, code repositories, categories and declared sign-in. |

The licence GitHub reports for a code repository is read through GitHub's
GraphQL interface with the gh login, at most once in thirty days for each
repository. The page shows it as "as the code host reports it". No licence was
verified against the files of a repository.

## Directories that are linked, never copied

| Directory | What its terms say | Decision |
| --- | --- | --- |
| Smithery, `smithery.ai` | No terms of service page was found at the usual addresses on September 24, 2026. Its robots file disallows `/api/`. | Linked only. Smithery's own listings in the official registry reach the directory through the registry. |
| PulseMCP, `pulsemcp.com` | The terms forbid automated collection of data from the website other than through its REST interface without written consent, and call the compilation PulseMCP's exclusive property. | Linked only. |
| Glama, `glama.ai` | The terms forbid using its interface data to build a product that competes with the Glama directory, and forbid scraping the website for data the interface gates. | Linked only. |

## How a row is built

- A listing whose status is not active is left out, and so is a listing that
  is not the latest version.
- A listing with no package, no remote endpoint and no code repository is left
  out. So is a remote endpoint that is not a public https address.
- Two listings are one row when they share a server name, their whole
  installation surface, or a remote endpoint. A GitHub or Docker listing joins
  the one row whose registry listing names the same code repository and folder.
- A row with a field shaped like a credential is held back.
- Categories come from the keyword rules in
  `tools/resources/mcp-directory-categories.json`.
- The commercial relationship of every row is `none`. The record and its rules
  are in `src/loop_engine/core/service_runtime/commercial_relationship.py`.
  Ranking, ordering, filtering and inclusion never read it. The labels and
  sentences are the ones the owner approved on September 24, 2026: a paid
  link is labelled Paid link, an ad Ad in a band headed Ads, and Baltor's own
  service is labelled as such.
- Every outbound link of a row goes through the service's counted redirect,
  `/out/directory/<link>/<row>`, which answers with the address the link
  table `src/loop_engine/core/service_runtime/public_lists/directory.json`
  holds and keeps one count per link per day, read from the path alone
  (`public_links.py`). The owner approved aggregate link counting in the
  privacy notice changes of September 24, 2026.

## Refresh the data

The workflow `.github/workflows/mcp-directory.yml` runs once a day. By hand:

```bash
PYTHONPATH=src:tools python tools/build_mcp_directory.py refresh --state STATE_FOLDER --licences 3000
PYTHONPATH=src:tools python tools/build_mcp_directory.py build --state STATE_FOLDER
PYTHONPATH=src:tools python tools/build_mcp_directory.py check
PYTHONPATH=src:tools python -m unittest tools/test_build_mcp_directory.py
```

The state folder lives outside the repository. A stopped refresh resumes from
its saved cursor.
