# AI SDR Dashboard — Campaign Form Layout Update

This update changes the Create Campaign and Edit Campaign forms to match the approved gray visual layout.

## Included changes

- Campaign Details appears first, with Campaign Name and Campaign Owner. Description is not included.
- Companies appears as its own full-width section and retains the existing company filters.
- Companies and Contacts country fields now offer a country dropdown list, support multiple selections, and display selected values as tags.
- Contacts appears after Companies. Languages is not included. Existing Job Title, Seniority, Job Level, Department, and Contact Country fields are retained.
- Clay Details appears last and retains the existing workbook link, Companies and Contacts webhook URLs, and webhook authentication token fields.
- Section headers, selected-value tags, and campaign dialog primary action use neutral gray styling.
- The same layout is applied to both Create Campaign and Edit Campaign.

## Upload to GitHub

1. Download and extract the ZIP, or download `app.py` separately.
2. In your `pathikpanchal/ai-sdr-dashboard` repository, open the branch connected to your live Streamlit app.
3. Replace the existing root-level `app.py` with this updated file and commit the change.
4. Do not replace `requirements.txt`; this update does not add Python dependencies.
5. Streamlit Cloud should redeploy after the commit. Test by creating and editing a small test campaign before using the form for a live campaign.

## Important

- Make a copy of the current GitHub `app.py` before replacing it so you can roll back if needed.
- This file passed Python syntax compilation, but it has not been tested against your live Streamlit environment, local SQLite database, or Clay account.
- Existing campaign data is stored in the dashboard database; replacing `app.py` does not intentionally delete or migrate it.
