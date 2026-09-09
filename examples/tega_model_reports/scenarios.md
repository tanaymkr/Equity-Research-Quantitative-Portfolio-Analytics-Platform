# Tega historical FY2025 case: illustrative scenarios

These are assumption experiments, not company guidance or a current valuation. All historical inputs remain the audited FY2024/FY2025 figures; modeled FY2026–FY2030 values are forecasts.

All scenarios retain base capex, financing, tax, asset-life and DCF assumptions. Their growth, EBITDA margin and working-capital inputs differ; the complete JSON files are the source of each scenario. No probabilities are assigned.

| Scenario | First-year growth | EBITDA margin | Collection days | FY2030 revenue (INR million) | Illustrative INR/share |
| --- | --- | --- | --- | --- | --- |
| base | 10.0% | 20.5% | 110 | 24,066.84 | 320.11 |
| downside | 4.0% | 17.0% | 120 | 19,461.13 | 196.44 |
| upside | 14.0% | 22.0% | 104 | 27,092.70 | 412.82 |

## Base-case WACC and terminal growth sensitivity

Values are illustrative INR/share. Terminal ROIC remains 15%; changing growth also changes required terminal reinvestment.

| WACC | g = 3% | g = 4% | g = 5% |
| --- | --- | --- | --- |
| 10% | 406.95 | 432.17 | 466.76 |
| 12% | 310.84 | 320.11 | 331.56 |
| 14% | 250.12 | 253.16 | 256.56 |

## Read the full model

- [Base forecast and supporting schedules](base/forecast.md)
- [Downside forecast and supporting schedules](downside/forecast.md)
- [Upside forecast and supporting schedules](upside/forecast.md)
- [Audited historical statements](base/historical_statements.md)

Reproduce this report with `python run_tega_scenarios.py`. It writes fresh outputs under `outputs/tega_scenarios`.
