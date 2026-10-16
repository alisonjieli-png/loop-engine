# Stage and verify the bootstrap before creating the installed skill.
(
  set -eu
  umask 077
  target="$PWD/.opencode/skills/baltor-library"
  for parent in .opencode .opencode/skills; do
    if [ -L "$parent" ] || { [ -e "$parent" ] && [ ! -d "$parent" ]; }; then
      printf '%s\n' "Refusing non-directory or symbolic-link parent: $parent" >&2
      exit 1
    fi
  done
  if [ -e "$target" ] || [ -L "$target" ]; then
    printf '%s\n' "Existing skill retained: $target. Inspect it before installing another copy." >&2
    exit 1
  fi
  mkdir -p .opencode/skills
  staging=$(mktemp -d "$PWD/.opencode/skills/.baltor-library-stage.XXXXXXXX")
  printf 'Staging directory retained for inspection: %s\n' "$staging"
  cd "$staging"
  for file in SKILL.md LICENSE scripts/baltor.py references/client.md assets/client.example.json verification/test_client.py SHA256SUMS; do
    curl -fsS --proto '=https' --max-time 30 --create-dirs \
      "https://baltor.ai/assets/baltor-library/$file" -o "$file"
  done
  python3 - <<'PY'
import re
from pathlib import Path
expected = {"SKILL.md", "LICENSE", "scripts/baltor.py", "references/client.md",
            "assets/client.example.json", "verification/test_client.py"}
lines = Path("SHA256SUMS").read_text(encoding="utf-8").splitlines()
matches = [re.fullmatch(r"[0-9a-f]{64}  (.+)", line) for line in lines]
if len(lines) != len(expected) or any(match is None for match in matches):
    raise SystemExit("Checksum manifest shape refused")
if {match.group(1) for match in matches} != expected:
    raise SystemExit("Checksum manifest must name exactly the six bootstrap files")
PY
  sha256sum --strict -c SHA256SUMS
  mkdir "$target"
  cp -R -n "$staging/." "$target/"
  cd "$target"
  sha256sum --strict -c SHA256SUMS
  python3 - "$HOME/.config/baltor" <<'PY'
import os
from pathlib import Path
import sys
folder = Path(sys.argv[1])
if any(parent.is_symlink() for parent in (folder.parent, folder)):
    raise SystemExit("Existing symbolic-link configuration directory retained; inspect it manually")
folder.mkdir(parents=True, exist_ok=True, mode=0o700)
try:
    descriptor = os.open(folder / "client.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
except FileExistsError:
    print("Existing client.json retained. Check its origin, token variable and declared effects before use.")
else:
    with os.fdopen(descriptor, "wb") as output:
        output.write(Path("assets/client.example.json").read_bytes())
    print("Created client.json without replacing existing configuration.")
PY
)