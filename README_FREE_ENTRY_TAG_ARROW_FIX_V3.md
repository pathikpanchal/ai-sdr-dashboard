# AI SDR Dashboard – Free-entry tag arrow fix (v3)

This update is based on the latest `app.py` uploaded in this conversation.

## Intended change
Hide the native dropdown indicator inside only these free-entry multi-select fields, in both Create Campaign and Edit Campaign:
- Industry
- City
- State / Region
- Current CMS
- Job Title
- Department

The CSS is scoped to each widget key and the `aria-hidden` indicator element. It does not target tag remove buttons. Predefined-option dropdowns (Company Size, Company Country, Seniority, Job Level, and Contact Country) are not changed.

## Validation
- Python syntax compilation passed.
- The selector list was checked for all 12 create/edit widget keys.
- A live Streamlit browser render was not available here, so confirm the appearance after deployment. If the arrow still appears, send a browser Inspect screenshot of the field's HTML element so the selector can be matched to the exact Streamlit DOM.

## Deploy
Replace the repository's root `app.py` with this file (rename it to `app.py`) and commit it to the Streamlit-connected branch. No other files are required for this CSS-only change.
