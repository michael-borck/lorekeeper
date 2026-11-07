# Pack backlog

Last reviewed: 2026-11-07.

All book repositories in `books/` now have a Lorekeeper pack. The remaining
candidates are source collections, not missing books.

## Candidate packs

### Local AI Field Notes

- Source: `/Volumes/Crucial X9/Projects/local-ai-field-notes`
- Shape: method notes, governance checklist, hardware notes, benchmarks and decision records.
- Candidate title: **Local First, Evidence First**
- Why: practical, privacy-first AI delivery for regulated small firms and education.
- Status: not built.

### Individual lab companions

The security lab series already has broad packs:

- **Assume Breach** covers defensive security.
- **Break with Permission** covers the ethical hacking lab series.
- **Follow the Trace** covers the forensics lab.
- **Build the Network, Watch It Run** covers NetSim.
- **Test the Claim, Rate the Control** covers the Tessera audit lab.

A separate pack per lab module is possible but would overlap. Only build one if
a single lab needs a dedicated workbook.

## Not worth converting

- Application repositories and tool documentation.
- Generated sites and build output.
- Marking, private staff material and answer keys.

## Maintenance backlog

- Update packs when source books or labs change.
- Re-run `python3 -m lorekeeper store --key ~/.lorekeeper/lorekeeper-signing.pem`.
- Re-run `./scripts/deploy-site.sh`.
