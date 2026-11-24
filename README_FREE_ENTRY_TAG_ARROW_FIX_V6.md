# Free-entry tag arrow fix — v6

Replace the repository's `app.py` with `app_free_entry_tag_arrow_fix_v6.py` (rename it to `app.py`).

This revision hides the SVG chevron itself, scoped only to the six free-entry fields in Create and Edit Campaign:
- Industry
- City
- State / Region
- Current CMS
- Job Title
- Department

The tag remove (×) icons are explicitly kept visible. Predefined-value filters are not targeted.

Validation: Python source compiled successfully. This environment does not have the deployed Streamlit browser session, so live visual rendering cannot be truthfully certified here.
