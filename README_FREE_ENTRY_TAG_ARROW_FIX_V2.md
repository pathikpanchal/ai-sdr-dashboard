# AI SDR Dashboard – Free-entry tag arrow fix (v2)

Based on the exact `app.py` uploaded for review.

## Native dropdown arrows removed
- Companies: Industry, City, State / Region, Current CMS
- Contacts: Job Title, Department

The CSS targets the nested BaseWeb multi-select end-indicator container instead of an SVG at the wrong DOM level. Selected tag remove controls are not targeted.

## Dropdowns retained
Company Size, Company Country, Seniority, Job Level, and Contact Country remain unchanged.

## Upload
1. Back up the current GitHub `app.py`.
2. Replace the root-level `app.py` with this file (rename it to `app.py`).
3. Commit to the branch connected to Streamlit.
4. After redeployment, check all six fields in both Create Campaign and Edit Campaign.

No `requirements.txt`, database, or other files need to change.

Python syntax compilation passed. Visual confirmation is still required in the deployed app.
