# Register a Brave Web Search plugin

This example discovers a Core Architecture capability from a local handshake
card, selects its Code Intelligence `LoopRef`, and invokes one capability loop.

Install and run the offline fixture:

```bash
python -m pip install "https://github.com/alisonjieli-png/loop-engine/archive/refs/heads/main.zip"
python3 examples/13_brave_search_plugin/run.py
```

- Network or model: none in the default run
- External effects: none in the default run
- Shows: manual plugin registration, effect-free discovery, handshake digest
  verification, one capability loop, rate-limit metadata, and ephemeral
  untrusted source candidates
- The injected recording transport checks the local discovery contract. It
  does not establish live Brave integration or search quality.

An explicit live run makes one metered external request:

```bash
BRAVE_SEARCH_API_KEY="..." \
python3 examples/13_brave_search_plugin/run.py --live
```

The live command requires network permission and a working Brave Search API
key. Brave plan terms control cost and storage rights. The adapter marks every
result `persistable: false` and does not save result text.

Search is not browsing. Fetching or extracting a selected result page should
use a separate registered capability with its own permissions and event
history.

Read the [Brave plugin contract](../../docs/components/core-architecture/BRAVE-SEARCH-PLUGIN.md)
for request limits, failure behavior, secret handling, and official API links.
