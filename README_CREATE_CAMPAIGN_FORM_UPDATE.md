# AI SDR Dashboard — Create Campaign Form Update

## What's changed
- Updated Create Campaign and Edit Campaign to a wide, horizontal two-panel layout.
- Added separate **Companies** and **Contacts** filter sections.
- Added Company Size multi-select options:
  - 2–10 employees
  - 11–50 employees
  - 51–200 employees
  - 201–500 employees
  - 501–1,000 employees
  - 1,001–5,000 employees
  - 5,001–10,000 employees
  - 10,001+ employees
- Expanded Seniority selections to Founder, Owner, Board Member, Partner, C-suite, VP, Director, Head, Manager, Senior, Mid-level, Entry, Intern / in-training, and Unknown.
- Company Size is persisted and passed to Clay's company search through its `sizes` filter, validated against the live Clay filter schema. The UI labels are translated to Clay's API bucket codes (`2`, `10`, `50`, `200`, `500`, `1000`, `5000`, `10000`) rather than sending display labels directly.
- Seniority selections are mapped to Clay's seniority enum values and sent as exact selected levels.
- Current CMS remains a note/target for the sales team to enrich manually in Clay after reviewing the sourced company list. It is not used as an API search filter in this phase.
- Existing Clay workbook and webhook destination fields remain available under the campaign delivery settings expander.
- Department remains available as an additional contact filter under an expander to preserve the existing workflow.
- Editing company size or contact criteria invalidates the old campaign criteria approval and requires re-approval.

## Setup
1. Replace the deployed `app.py` with the included `app.py`.
2. Keep the current `requirements.txt` unchanged.
3. Commit and push to the configured GitHub branch, then allow Streamlit Community Cloud to redeploy.

## Validation
- Python syntax compilation passed.
- Pure-function tests passed for the expanded Clay seniority mapping and Company Size filter vocabulary mapping.
- Static checks confirmed the form structure, campaign persistence field, Clay company `sizes` filter, and existing webhook configuration fields.
- SQLite migration smoke test confirmed `company_size` and existing webhook destination columns are present on a fresh database; an insert test confirmed the new values persist.
- Clay's API `sizes` numeric bucket mapping was cross-checked against Clay's developer example. See [Clay's verified API size mapping example](https://agent-docs.clay.com/blog/code-example/which-software-can-find-lookalike-companies-with-typescript).
- A live Streamlit UI / live Clay API test was not run in this environment because Streamlit is not installed here and no Clay secrets/webhook URLs are available to the test runtime.
