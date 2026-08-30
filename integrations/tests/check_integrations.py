"""Deterministic structure checks for thin host adapters."""
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def main():
    manifests=[ROOT/"codex/plugins/loop-engine/.codex-plugin/plugin.json",
               ROOT/"codex/.agents/plugins/marketplace.json",
               ROOT/"claude-code/.claude-plugin/plugin.json",
               ROOT/"claude-code/.claude-plugin/marketplace.json"]
    for path in manifests: json.loads(path.read_text())
    skills=list(ROOT.glob("*/**/skills/*/SKILL.md"))
    assert len(skills)>=6
    forbidden=("class Loop(","class Practitioner","OPENAI_API_KEY=",
               "OLLAMA_API_KEY=")
    for path in skills:
        text=path.read_text()
        assert "[TODO:" not in text
        assert not any(item in text for item in forbidden)
    print(json.dumps({"record_type":"integration_check/v1",
                      "manifests":len(manifests),"skills":len(skills),
                      "all_passed":True}))
if __name__=="__main__": main()
