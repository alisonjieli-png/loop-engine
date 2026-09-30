"""Copy the exact reviewed worker launch configuration to its download route."""
from pathlib import Path


def build(root):
    root = Path(root)
    source = root / "containers/worker/compose.yaml"
    target = root / "src/loop_engine/core/service_runtime/web_assets/worker-compose.yaml"
    target.write_bytes(source.read_bytes())


if __name__ == "__main__":
    build(Path(__file__).resolve().parents[1])
