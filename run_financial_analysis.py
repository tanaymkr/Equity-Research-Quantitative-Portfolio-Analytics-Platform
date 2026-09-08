"""Convenience launcher that also works without an editable package install."""

import sys
from pathlib import Path


def main() -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
    from equity_analytics.financials.__main__ import main as analyze

    analyze()


if __name__ == "__main__":
    main()
