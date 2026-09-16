"""Run the FY26 legacy-only linked model; default Tega launcher retains Molycop."""

import sys
from pathlib import Path


def main():
    root = Path(__file__).resolve().parent
    sys.path.insert(0, str(root / "src"))
    from equity_analytics.forecasting.__main__ import main as run

    run(default_root=root, default_base_year=2026)


if __name__ == "__main__":
    main()
