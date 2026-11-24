# AI SDR Dashboard – Campaign Form Layout Update

This update changes only the Create Campaign and Edit Campaign form presentation in `app.py`.

## Included changes

- Light-blue section heading bars with blue heading text.
- Black filter labels and descriptions; selected multi-select values remain gray tags.
- Consistent additional vertical space between each section heading and its first input row, including Campaign Details, Companies, Contacts, and Clay Details.
- Companies filter order: Industry, Company Size, Company Country, City, State / Region, Current CMS.
- Contacts filter order: Job Title, Department, Seniority, Job Level, Contact Country.
- Updated helper descriptions for Contacts and Clay Details.
- Applied the same layout to both Create Campaign and Edit Campaign.
- Existing Clay workbook, webhook URL, and authentication-token fields and behavior are retained.

## GitHub upload

1. Download and unzip the package, or download `app.py` separately.
2. Before replacing anything, download a backup copy of the current root-level `app.py` from GitHub.
3. Replace only the root-level `app.py` with this updated file.
4. Commit the change to the branch connected to your live Streamlit app.
5. Wait for Streamlit Cloud to finish redeploying, then test Create Campaign and Edit Campaign.

`requirements.txt` does not need to change for this update.

## Validation

The updated file passed `python -m py_compile`. This is a syntax check only; the live Streamlit app and Clay workflows have not been integration-tested as part of this package.
