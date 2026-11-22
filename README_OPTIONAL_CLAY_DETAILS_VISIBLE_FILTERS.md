# AI SDR Dashboard – Visible Filters and Optional Clay Details

## UX changes
- Multi-select chips (Company Size and Seniority) are styled to wrap to additional lines in the campaign dialogs rather than being clipped in a single row.
- Multi-value text filters (Industry, Company Country, Current CMS, Job Title, Department, and Contact Country) use multi-line fields so multiple entered values remain visible.
- Multiple values can be separated with commas, semicolons, or new lines. Existing parsing supports all three.

## Clay Details are optional
- Clay Workbook Link, Companies Table Webhook URL, Contacts Table Webhook URL, and both auth tokens can be left empty when creating or editing a campaign.
- The campaign can be saved without Clay configuration.
- Build Campaign Data remains unavailable until a valid HTTPS workbook URL and both valid HTTPS webhook URLs are configured. This prevents the dashboard from reporting a successful Clay publication without destinations.
- Webhook authentication tokens are optional.

## Validation performed
- `python -m py_compile app.py` passed.
- Existing `test_form_logic.py` passed: seniority mapping, company-size mapping, Clay API size codes, and form/persistence checks.
- Additional static checks confirmed that Create and Edit no longer require Clay destination fields and that Build Campaign Data still requires a complete destination.
- No live Streamlit browser render or live Clay API/webhook test was performed for this form UX update.

## Deployment
Replace the deployed `app.py` with this file. Keep `requirements.txt` and existing Streamlit Secrets unchanged. Clay API keys, workbook links, webhook URLs, and webhook auth tokens do not need to be regenerated.
