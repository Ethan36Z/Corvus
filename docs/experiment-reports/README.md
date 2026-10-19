# Corvus experiment report archive

Public, reviewed experiment reports live on `reports/web-validation`, separately
from the Lab development branch. Archiving a report does not publish its source
baseline, deploy a change, accept an untested capability, or authorize another run.

| Area | Chronological report index |
| --- | --- |
| Web reliability and grounded synthesis | [Web experiments](web/README.md) |

## Adding a report

1. Create a minimally sanitized Markdown copy under its experiment area.
2. Name it `YYYY-MM-DD-<experiment-id>-<short-description>.md`, using lowercase
   identifiers and hyphens for punctuation: `W1.1` becomes `w1-1`.
3. Include experiment ID, experiment date, objective, exact verdict, related
   baseline commit, observed evidence, failures, limitations and acceptance scope.
4. Append a row to the area's chronological index, ordered by date then experiment
   sequence. Use relative Markdown links within this archive.
5. Review the complete copy before staging. Exclude credentials, tokens/cookies,
   keys, private conversations, personal memory, database contents and unnecessary
   host/account details. Do not include raw terminal transcripts or unreviewed
   metrics JSON. Explain any sanitization; preserve measurements and uncertainty.
6. Validate links, scope and staged whitespace. Commit documentation only on the
   reporting branch. Publication requires separate authorization; never push the
   Lab branch as part of report publication.

Local artifact paths mentioned in historical reports are provenance references,
not downloadable archive assets. Baseline hashes may identify unpublished local
commits; their appearance here does not make those commits available on GitHub.
