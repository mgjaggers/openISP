# Checklist traceability

`openISP_professional_ISP_checklist_UPDATED_v2.xlsx` is read-only input to the
project controls. `checklist_mapping.json` is a deterministic generated view
that assigns every workbook ID a target module, test target, evidence index and
milestone. It intentionally stores the workbook status separately from code
implementation state.

Regenerate and verify it with:

```bash
python tools/export_checklist_manifest.py \
  docs/openISP_professional_ISP_checklist_UPDATED_v2.xlsx \
  docs/checklist_mapping.json
python tools/verify_isp_checklist.py \
  docs/openISP_professional_ISP_checklist_UPDATED_v2.xlsx \
  --manifest docs/checklist_mapping.json
```

Add `--check` to the export command in CI to reject a stale mapping. Add
`--libreoffice` to the verifier for a non-destructive temporary open/save
round-trip when LibreOffice is available.

Evidence indexes live at `artifacts/checklist/<ID>.json`. Large fixtures remain
outside Git and are referenced by immutable identifier and hash.
