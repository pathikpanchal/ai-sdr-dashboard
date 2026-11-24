# AI SDR Dashboard — Live UI and filter updates

This package contains an updated `app.py` based on the current `main` branch version of the live SQLite dashboard.

## Included changes
- Wider Create Campaign and Edit Campaign dialogs on desktop.
- Company filters for Country, State / Region, and City.
- Tag/chip-style multi-select fields in Companies and Contacts instead of comma-separated text areas.
- Job Level comparison selector: Below, Above, Equal. The selected comparison is applied to the selected Seniority level(s); Equal means exact match.
- Existing campaigns are preserved. On startup, the app adds the two new SQLite columns (`company_state`, `company_city`) if they do not already exist.

## Upload
1. Download `app.py` from this package.
2. Replace the existing `app.py` in `pathikpanchal/ai-sdr-dashboard` on the branch connected to the live Streamlit app (currently `main`, if unchanged).
3. Commit and push. Streamlit Cloud should redeploy automatically.
4. Open Create Campaign and test one company search with country + state + city before using it for a large search.

No `requirements.txt` change is needed; the repository already requires Streamlit 1.42 or newer, which supports `st.multiselect(accept_new_options=True)`.

## Important testing note
- Python syntax compilation passed.
- This package was not run against the live Streamlit app, the user's SQLite database, or a live Clay API key. Test with a small search first.
- State and city are sent to Clay using its company location filters (`location_states_include` and `location_cities_include`). These are headquarters-location filters when the API exposes `location_headquarters_only`.
- If the app reports that the live Clay schema does not expose a state or city filter, do not proceed with a large search; share the exact error so the field mapping can be checked against the account's live schema.
