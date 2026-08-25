"""Watch a real run through console, polling, and server-sent events."""

import argparse

from loop_engine.code_nodes.live_run_demo import run_live_demo


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8770)
    parser.add_argument("--runs-dir", default="example-output/runs")
    args = parser.parse_args()
    print(f"Open http://127.0.0.1:{args.port}")
    print(f"Completed runs will be saved under {args.runs_dir}")
    run_live_demo(port=args.port, pace_seconds=0.6, serve_forever=True,
                  runs_dir=args.runs_dir)


if __name__ == "__main__":
    main()
