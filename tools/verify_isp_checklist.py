#!/usr/bin/env python3
"""Verify the structural and traceability invariants of the ISP workbook."""

import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
from collections import Counter
from pathlib import Path
from typing import List
from xml.etree import ElementTree as ET

from checklist_lib import MAIN, WorkbookReader, table

EXPECTED_HEADERS = [
    "Status", "ID", "Category", "Scope", "Requirement level", "Applicability",
    "Priority", "Effort", "Capability", "Source fit", "Primary source", "Page / section",
    "Implementation checklist", "Acceptance criteria", "Verification method", "Dependencies",
    "Deliverable / module", "Primary URL", "Supplemental source", "Supp. page / section",
    "Supplemental URL", "Required artifact", "IP / license status", "Owner",
    "Target milestone", "Notes",
]
ALLOWED_STATUS = {"Not started", "In progress", "Done", "N/A"}


def verify(workbook: Path, manifest: Path, expected_items: int) -> List[str]:
    errors = []
    with WorkbookReader(workbook) as reader:
        expected_sheets = {"Checklist", "Coverage Summary", "Source Library", "Read Me"}
        if set(reader.sheets) != expected_sheets:
            errors.append("sheet set differs: {}".format(sorted(reader.sheets)))
        headers, all_rows = table(reader, "Checklist")
        rows = [row for row in all_rows if row.get("ID")]
        if headers != EXPECTED_HEADERS:
            errors.append("Checklist headers differ from the canonical 26-column schema")
        if len(rows) != expected_items:
            errors.append("expected {} checklist items, found {}".format(expected_items, len(rows)))
        identifiers = [row["ID"] for row in rows]
        duplicates = [key for key, count in Counter(identifiers).items() if count > 1]
        if duplicates:
            errors.append("duplicate checklist IDs: {}".format(", ".join(duplicates)))
        known = set(identifiers)
        for row in rows:
            if row["Status"] not in ALLOWED_STATUS:
                errors.append("row {} has invalid status {!r}".format(row["_row"], row["Status"]))
            for field in ("Category", "Scope", "Requirement level", "Priority", "Capability",
                          "Acceptance criteria", "Verification method", "Deliverable / module"):
                if not row[field]:
                    errors.append("item {} has blank {}".format(row["ID"], field))
            for dependency in [part.strip() for part in row["Dependencies"].split(",") if part.strip()]:
                if dependency not in known:
                    errors.append("item {} refers to unknown dependency {}".format(row["ID"], dependency))
            if row["Primary URL"] and not re.match(r"^https?://", row["Primary URL"]):
                errors.append("item {} has a non-HTTP primary URL".format(row["ID"]))

        checklist_doc = reader.document("Checklist")
        panes = list(checklist_doc.iter("{{{}}}pane".format(MAIN)))
        if not any(pane.attrib.get("state") == "frozen" for pane in panes):
            errors.append("Checklist does not have frozen panes")
        validations = [item.attrib.get("sqref", "") for item in checklist_doc.iter("{{{}}}dataValidation".format(MAIN))]
        if len(validations) < 6 or any(not value.endswith("300") for value in validations):
            errors.append("Checklist validations do not consistently reserve through row 300")
        conditional = [item.attrib.get("sqref", "") for item in checklist_doc.iter("{{{}}}conditionalFormatting".format(MAIN))]
        if not conditional or any(not value.endswith("300") for value in conditional):
            errors.append("Checklist conditional formatting does not consistently reserve through row 300")

        table_refs = []
        for name in reader.archive.namelist():
            if name.startswith("xl/tables/") and name.endswith(".xml"):
                table_refs.append(ET.fromstring(reader.archive.read(name)).attrib.get("ref"))
        if "A3:Z300" not in table_refs or "A3:Q63" not in table_refs:
            errors.append("canonical checklist/source-library table ranges are missing")

        formulas = reader.formulas("Coverage Summary")
        if not formulas:
            errors.append("Coverage Summary has no formulas")
        for cell, formula in formulas.items():
            if "Checklist!" in formula and "$300" not in formula:
                errors.append("summary formula {} does not cover row 300".format(cell))

        source_headers, source_rows = table(reader, "Source Library")
        source_rows = [row for row in source_rows if row.get("ID")]
        source_ids = [row["ID"] for row in source_rows]
        if len(source_ids) != len(set(source_ids)):
            errors.append("Source Library contains duplicate IDs")
        if not source_headers or len(source_headers) != 17:
            errors.append("Source Library does not have the canonical 17-column schema")

    if not manifest.exists():
        errors.append("traceability manifest is missing: {}".format(manifest))
    else:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        mapped = payload.get("items", [])
        mapped_ids = [str(item.get("id", "")) for item in mapped]
        if mapped_ids != identifiers:
            errors.append("traceability manifest IDs/order do not match the workbook")
        for item, row in zip(mapped, rows):
            for manifest_key, workbook_key in (
                ("capability", "Capability"), ("category", "Category"), ("workbook_status", "Status")
            ):
                if item.get(manifest_key) != row.get(workbook_key):
                    errors.append("manifest item {} has stale {}".format(row["ID"], manifest_key))
            for key in ("target_module", "test_target", "evidence", "milestone"):
                if not item.get(key):
                    errors.append("manifest item {} is missing {}".format(row["ID"], key))
    return errors


def libreoffice_roundtrip(workbook: Path) -> str:
    executable = shutil.which("libreoffice")
    if executable is None:
        raise RuntimeError("libreoffice is not installed")
    with tempfile.TemporaryDirectory(prefix="openisp-checklist-") as temporary:
        source = Path(temporary) / "source" / workbook.name
        output = Path(temporary) / "output"
        profile = Path(temporary) / "profile"
        temporary_home = Path(temporary) / "home"
        source.parent.mkdir()
        output.mkdir()
        profile.mkdir()
        temporary_home.mkdir()
        shutil.copy2(str(workbook), str(source))
        environment = dict(os.environ)
        environment.update(
            {
                "HOME": str(temporary_home),
                "XDG_CACHE_HOME": str(temporary_home / ".cache"),
                "SAL_USE_VCLPLUGIN": "svp",
            }
        )
        completed = subprocess.run(
            [
                executable,
                "-env:UserInstallation={}".format(profile.as_uri()),
                "--headless",
                "--convert-to",
                "xlsx",
                "--outdir",
                str(output),
                str(source),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=90,
            env=environment,
        )
        converted = output / workbook.name
        if completed.returncode != 0 or not converted.exists():
            raise RuntimeError("LibreOffice round-trip failed: {}".format(completed.stdout.strip()))
        with WorkbookReader(converted) as reader:
            _, rows = table(reader, "Checklist")
            if len(rows) < 297:
                raise RuntimeError("LibreOffice truncated reserved checklist rows")
        return completed.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--manifest", type=Path, default=Path("docs/checklist_mapping.json"))
    parser.add_argument("--expected-items", type=int, default=151)
    parser.add_argument("--libreoffice", action="store_true")
    args = parser.parse_args()
    errors = verify(args.workbook, args.manifest, args.expected_items)
    if errors:
        for error in errors:
            print("ERROR: {}".format(error))
        return 1
    if args.libreoffice:
        print(libreoffice_roundtrip(args.workbook))
    print("verified {} checklist items and traceability mappings".format(args.expected_items))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
