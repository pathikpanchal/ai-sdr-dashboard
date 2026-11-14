# AI SDR Dashboard — Updated Phase I Mock MVP

## What's updated
- Campaign Name
- Industry (free-text input)
- Company Country (free-text input)
- Contact Country (free-text input)
- Current CMS (free-text input; comma-separated alternatives supported)
- Department (free-text input; comma-separated alternatives supported)
- Seniority dropdown: Manager, Head, Director, VP, C-Suite, Owner / Founder
- Job Level dropdown: Above, Any, Below, Exact
- `Above` includes the selected seniority and all higher levels.
- `Below` includes the selected seniority and all lower levels.
- `Exact` includes only the selected seniority.
- Campaign duplication and confirmed campaign deletion
- Mock research applies the selected filters to fictional sample records.

## Important: Mock Mode only
This build does **not** connect to Clay, call Clay APIs, create Clay tables, enrich real records, or send emails. It uses fictional sample records and consumes zero Clay credits.

## Update the existing Streamlit deployment
1. Download and extract the ZIP, or download `app.py` separately.
2. Open your GitHub repository.
3. Replace the existing root-level `app.py` with this updated file.
4. Commit the change to the deployed branch (use the exact branch name, e.g. `Main`).
5. Streamlit Community Cloud should detect the commit and redeploy the app.

## Run locally
1. Install Python 3.10 or newer.
2. Run `pip install -r requirements.txt`.
3. Run `streamlit run app.py`.

The app creates `ai_sdr.db` locally. Do not upload this database file to GitHub.
