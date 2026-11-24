# AI SDR Dashboard – Remove arrows from free-entry tag fields

This update removes the dropdown chevron from exactly these fields in both Create Campaign and Edit Campaign:

- Companies: Industry, City, State / Region, Current CMS
- Contacts: Job Title, Department

Dropdown arrows remain on fields with predefined choices, including Company Size, Company Country, Seniority, Job Level, and Contact Country.

The previous CSS was scoped only to `role=dialog`, but this campaign form can render in the main page. This version removes that restrictive scope so the targeted selectors apply in either layout.

## Upload
Replace the root-level `app.py` in GitHub with this file. No requirements, database, or other files need to change.

Python source compilation passed. Confirm the appearance after Streamlit redeploys.
