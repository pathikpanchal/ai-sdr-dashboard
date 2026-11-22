# AI SDR Dashboard – Campaign Action Row Update

## Change
- Moved the `Selected Campaign: ...` heading above the action buttons.
- Put `Approve Criteria`, `Build Campaign Data`, `Edit Campaign`, `Duplicate Campaign`, and `Delete Campaign` into one dedicated horizontal Streamlit columns row.
- Moved Build Campaign Data prerequisite guidance below its button so the guidance no longer pushes that button down relative to the other actions.
- Existing search, approval, permissions, webhook delivery and status logic are unchanged.

## Files
- `app.py`: updated dashboard application
- `requirements.txt`: unchanged dependencies

## Validation performed
- `python -m py_compile app.py`
- `python test_form_logic.py`

These checks validate Python syntax and the included form/filter logic. A live Streamlit browser rendering test was not performed.
