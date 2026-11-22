# AI SDR Dashboard – Final Create/Edit Campaign Form

This update implements the approved Create Campaign visual and applies the same structure to Edit Campaign.

## Form layout

- **Campaign Details:** Campaign Name and Campaign Owner.
- **Companies:** Industry, Company Size, Company Country, and Current CMS.
- **Contacts:** Job Title, Department, Seniority, and Contact Country.
- **Clay Details:** One expandable section containing:
  - Clay Workbook Link
  - Companies Table Webhook URL
  - Companies Webhook Auth Token (optional)
  - Contacts Table Webhook URL
  - Contacts Webhook Auth Token (optional)

The Companies and Contacts sections use the building and people/group icons from the approved reference.

## Removed from Create/Edit forms

- Minimum ICP Score
- Email Sequence Instructions

The existing database columns remain in place for backwards compatibility; these fields are no longer presented or overwritten by the Edit Campaign form.

## Validation

- `python -m py_compile app.py` passed.
- Existing company-size and seniority mapping tests passed.
- AST structure checks passed for Create and Edit forms, including a single Clay Details expander, required workbook/webhook fields, Department inside Contacts, and absence of the removed inputs.

A live Streamlit rendering and live Clay request were not run in this environment. Existing Clay API/webhook integration functions were preserved.

## Deployment

Replace the deployed `app.py` with the one in this package. Keep `requirements.txt` and Streamlit Secrets unchanged. No Clay API key or webhook URLs need to be regenerated for this form-only change.
