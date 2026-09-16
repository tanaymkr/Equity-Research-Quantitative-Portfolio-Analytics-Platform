"""Convenience launcher: uses this repository's src and example inputs."""

import sys
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parent
    sys.path.insert(0, str(root / "src"))
    if "--historical-fy2025" in sys.argv:
        sys.argv.remove("--historical-fy2025")
        from equity_analytics.forecasting.__main__ import main as run
    else:
        from equity_analytics.acquisition.__main__ import main as run

    run(default_root=root)


if __name__ == "__main__":
    main()
