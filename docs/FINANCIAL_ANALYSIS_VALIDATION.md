# Validation record

Verified locally on 2026-09-07 using Python 3.12.13, pytest 9.1.1 and Ruff 0.16.6.

- Full test suite: **27 tests passed** (the six original DCF tests plus 21 new
  historical-analysis tests; pytest also reported six passing subtests).
- Ruff checks: passed for the combined original project and new files.
- Notebook: all six code cells executed; syntax also checked against Python 3.11.
- Both synthetic and Tega example inputs loaded and generated JSON and Markdown
  reports successfully.
- Original DCF demo: enterprise value INR 23,647.04 crore and implied value INR
  190.81 per share, matching the original example.
- The new runtime module uses only the Python standard library.

The test fixture includes literal, hand-calculated expectations for growth,
average-balance returns, cash flow and leverage. Other tests cover missing data,
negative earnings/equity, non-positive denominators, skipped years, duplicate
years/keys, unsupported units, invalid dates, source references and JSON export.

These are local checks against the original Milestone 1 ZIP. They do not establish
the current contents or GitHub Actions status of the live repository. Live
inspection and any repository write require the GitHub connection and the user's
authorization. Tega source notes document the limited presentation-based inputs;
the tests verify calculations, not the issuer's accounting or source authenticity.
