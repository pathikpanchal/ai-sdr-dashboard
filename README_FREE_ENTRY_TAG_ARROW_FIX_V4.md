# AI SDR Dashboard – Free-entry tag arrow fix (v4)

## Change
This version replaces the v3 `aria-hidden` selector, which did not remove the visible arrows in the supplied browser screenshot.

It hides SVGs inside the six free-entry multi-select widgets in both Create Campaign and Edit Campaign:
- Industry
- City
- State / Region
- Current CMS
- Job Title
- Department

It explicitly restores SVG icons inside selected-value tags so the tag remove icons remain available. It does not target the other predefined-option dropdown widgets.

## Validation
- Python syntax compilation passed.
- All 12 Create/Edit widget keys are covered.
- This environment cannot run the deployed Streamlit browser UI, so visual confirmation still requires deployment.

## Deploy
Replace the repository root `app.py` with this file (rename it to `app.py`) and deploy. No other application logic is changed by this patch.
