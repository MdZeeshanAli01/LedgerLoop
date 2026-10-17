# LedgerLoop

LedgerLoop is a synthetic-data B2B receivables follow-up desk for the C28
Fynd × NMIMS Hyderabad engineering case.

## Project requirements

See [`PROJECT_REQUIREMENTS.md`](./PROJECT_REQUIREMENTS.md) for the consolidated
requirements, acceptance criteria, and phased development checklist derived from
the supplied C28 documents.

## Run the application

Use Python 3.10 or later:

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

The default input is [`data/fixture.json`](./data/fixture.json). The sidebar also
accepts a JSON or CSV upload with the documented fields.

## Run tests

```powershell
python -m pytest -q
```

The suite covers loader validation, balances, ageing, disputes, promises,
priority scoring, drafts, exports, UI delegation, and an end-to-end synthetic
fixture. The starter C28 regression verifies ₹46,000 outstanding, ₹36,000
collectible, ₹10,000 under review, one paid invoice, and the expected priority
order.

## Workflow

1. Load the fixture or upload a compatible file.
2. Select an `as_of` date and optionally filter customers.
3. Review priority, dispute, promise, paid, not-due, and unapplied-receipt views.
4. Open invoice detail to edit dispute or promise fields in session state.
5. Review and edit the template-only customer drafts.
6. Export `output/result.json`, `output/result.csv`, and
   `output/evidence_log.md`.

Every draft is labelled `DRAFT - not sent`. There is no send action or external
service integration.

## Evidence and limitations

- [`CONTEXT.md`](./CONTEXT.md) records the engineering scope and business rules.
- [`docs/assumptions.md`](./docs/assumptions.md) separates observed fixture facts
  from design assumptions and known gaps.
- [`data/extra_synthetic.json`](./data/extra_synthetic.json) demonstrates partial
  payment, an unapplied receipt, a detailed dispute, a broken promise, a future
  receipt, and invalid input.
- Output files are generated locally and are ignored as runtime artifacts.
- All data is synthetic. No cash recovery, live revenue, market demand, or
  production readiness is claimed.
- MBA pricing, growth, customer research, and pitch work are outside the
  engineering scope. An MBA-entry snapshot should be added only when the MBA
  team actually joins.
