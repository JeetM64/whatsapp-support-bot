# Internship Studio WhatsApp Support Bot

## Maintaining the KB

\`kb/knowledge_base.csv\` is the editable source of truth. Update it in Excel or Google Sheets, then export it as UTF-8 CSV. Keep the header names and \` | \` separators in \`hinglish_variants\`; variants are used for retrieval and are never shown as replies.

Company facts must only be entered in \`kb/verified_facts.yaml\` after checking an authoritative company source. Unverified values belong in \`kb/mock_defaults.yaml\` and must stay visibly marked \`[MOCK]\`; the build adds a \`SAMPLE DATA\` label to every rendered answer that uses a mock fact. Do not replace sample values with guesses.

With PowerShell 7, run these commands from the project root:

\`\`\`powershell
$env:PYTHONUTF8 = "1"
.\\.venv\\Scripts\\python.exe -m src.kb validate
.\\.venv\\Scripts\\python.exe -m src.kb build
.\\.venv\\Scripts\\python.exe -m src.kb report
\`\`\`

\`validate\` checks the source without writing generated data. \`build\` validates and deterministically writes \`kb/build/knowledge_base.json\`, including a SHA-256 content hash. \`report\` prints the category totals and the mock-fact go-live list, then saves it to \`docs/kb_report.md\`. Never edit the generated JSON by hand; edit the CSV or verified facts and rebuild.

\`kb/verified_facts.yaml\` is intentionally empty until company facts are verified. \`kb/mock_learners.json\` and all values in \`kb/mock_defaults.yaml\` are fictional test data, not company policy or learner records.
