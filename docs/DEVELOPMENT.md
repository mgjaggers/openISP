# Development

Use Python 3.10 or newer. A local editable environment is:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev]'
```

Run the gates with:

```bash
.venv/bin/python -m pytest
.venv/bin/python tools/export_checklist_manifest.py \
  docs/openISP_professional_ISP_checklist_UPDATED_v2.xlsx \
  docs/checklist_mapping.json --check
.venv/bin/python tools/verify_isp_checklist.py \
  docs/openISP_professional_ISP_checklist_UPDATED_v2.xlsx \
  --manifest docs/checklist_mapping.json
```

Inspect or run a configuration with:

```bash
.venv/bin/openisp list-stages
.venv/bin/openisp validate-config config/pipeline.json --input-domain bayer
.venv/bin/openisp run config/pipeline.json input.npy output.npy --cfa rggb
```

Every change to a processing stage needs focused unit coverage, at least one
adjacent-stage integration assertion and an update to the applicable evidence
index. Numerical behavior must follow `NUMERICAL_POLICY.md`.
