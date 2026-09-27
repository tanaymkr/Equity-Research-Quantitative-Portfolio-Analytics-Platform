"""Import histories, export Wabag and Tega, and compare their common latest year."""
from pathlib import Path

from run_data_pipeline import main as load_pipeline


def main():
    root = Path(__file__).resolve().parent
    # The existing loader retains its standalone CLI and earlier-cutoff behaviour.
    load_pipeline([])
    from equity_analytics.data import FinancialStore
    from equity_analytics.data.__main__ import export_analysis
    from equity_analytics.data.comparison import comparison_html

    output = root / "outputs/data"
    store = FinancialStore(output / "research.sqlite")
    export_analysis(store, "WABAG", "2026-09-11", output / "wabag")
    target = output / "company_comparison.html"
    target.write_text(comparison_html(store, ["TEGA", "WABAG"], "2026-09-11"), encoding="utf-8")
    print(f"Wabag: {output / 'wabag/analysis.html'}")
    print(f"Comparison: {target}")


if __name__ == "__main__":
    main()
