import json
import subprocess
import sys
from pathlib import Path


WORKBOOK = Path("docs/openISP_professional_ISP_checklist_UPDATED_v2.xlsx")
MANIFEST = Path("docs/checklist_mapping.json")


def test_manifest_maps_every_workbook_item():
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert payload["item_count"] == 151
    assert len(payload["items"]) == 151
    assert len({item["id"] for item in payload["items"]}) == 151


def test_manifest_and_workbook_verifier_pass():
    subprocess.run(
        [sys.executable, "tools/export_checklist_manifest.py", str(WORKBOOK), str(MANIFEST), "--check"],
        check=True,
    )
    subprocess.run(
        [sys.executable, "tools/verify_isp_checklist.py", str(WORKBOOK), "--manifest", str(MANIFEST)],
        check=True,
    )
