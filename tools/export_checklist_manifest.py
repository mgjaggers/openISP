#!/usr/bin/env python3
"""Generate or verify the deterministic checklist-to-code traceability manifest."""

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Dict

from checklist_lib import checklist_records

CATEGORY_AREA = {
    "1. RAW front end": ("raw", "M2-linear-core"),
    "2. Image statistics": ("statistics", "M3-controls"),
    "3. Automatic control": ("controls", "M3-controls"),
    "4. HDR and dynamic range": ("hdr", "M5-hdr-sensors"),
    "5. Noise reduction": ("denoise", "M4-image-quality"),
    "6. Demosaic and artifacts": ("demosaic", "M4-image-quality"),
    "7. Color": ("color", "M4-image-quality"),
    "8. Detail and appearance": ("detail", "M4-image-quality"),
    "9. Geometry and output": ("geometry", "M4-product-output"),
    "10. Drone-specific": ("drone", "M6-drone-optional"),
    "11. Tuning and calibration": ("calibration", "M4-product-output"),
    "12. Package/control architecture": ("core", "M1-foundation"),
    "13. Specific openISP fixes": ("stages", "M1-foundation"),
}

IMPLEMENTED = {
    "112": ["src/openisp/stages/legacy.py", "model/awb.py"],
    "113": ["src/openisp/stages/legacy.py", "isp_pipeline.py"],
    "114": ["src/openisp/stages/legacy.py", "model/hsc.py"],
    "115": ["src/openisp/stages/legacy.py", "model/cnf.py"],
    "116": ["tests/unit/test_bayer_patterns.py"],
    "117": ["tests/unit", "tests/integration", "tests/regression", "tests/performance"],
}

TEST_TARGETS = {
    "112": ["tests/unit/test_stabilization_fixes.py", "tests/integration/test_reference_pipeline.py"],
    "113": ["tests/unit/test_stabilization_fixes.py", "tests/integration/test_reference_pipeline.py"],
    "114": ["tests/unit/test_stabilization_fixes.py", "tests/regression/test_image_regression.py"],
    "115": ["tests/unit/test_bayer_patterns.py", "tests/integration/test_reference_pipeline.py"],
    "116": ["tests/unit/test_bayer_patterns.py", "tests/integration/test_reference_pipeline.py"],
    "117": ["tests/unit", "tests/integration", "tests/regression", "tests/performance"],
}


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def milestone(record: Dict[str, str], default: str) -> str:
    identifier = record["ID"]
    if identifier in IMPLEMENTED:
        return "M1-foundation"
    if record["Scope"].startswith("5."):
        return "M7-release"
    if record["Scope"].startswith("2."):
        return "M5-hdr-sensors"
    if record["Scope"].startswith("4."):
        return "M6-drone-optional"
    return default


def build_manifest(workbook: Path) -> Dict[str, object]:
    _, rows = checklist_records(workbook)
    digest = hashlib.sha256(workbook.read_bytes()).hexdigest()
    items = []
    for record in rows:
        area, default_milestone = CATEGORY_AREA[record["Category"]]
        capability_slug = slug(record["Capability"])
        identifier = record["ID"]
        target_module = "src/openisp/{}/{}.py".format(area, capability_slug)
        implementation_files = IMPLEMENTED.get(identifier, [target_module])
        test_targets = TEST_TARGETS.get(
            identifier, ["tests/{}/test_{}.py".format(area, capability_slug)]
        )
        items.append(
            {
                "id": identifier,
                "capability": record["Capability"],
                "category": record["Category"],
                "scope": record["Scope"],
                "requirement_level": record["Requirement level"],
                "priority": record["Priority"],
                "workbook_status": record["Status"],
                "implementation_state": "implemented" if identifier in IMPLEMENTED else "planned",
                "target_module": target_module,
                "implementation_files": implementation_files,
                "test_target": test_targets[0],
                "test_targets": test_targets,
                "evidence": "artifacts/checklist/{}.json".format(identifier),
                "milestone": milestone(record, default_milestone),
                "dependencies": [part.strip() for part in record["Dependencies"].split(",") if part.strip()],
            }
        )
    return {
        "schema_version": 1,
        "source": str(workbook),
        "source_sha256": digest,
        "item_count": len(items),
        "status_authority": "The XLSX Status column is authoritative; implementation_state is code evidence only.",
        "definition_of_done": [
            "typed configuration and declared input/output contract",
            "source-backed implementation and license/provenance record",
            "unit and numerical invariant tests",
            "pipeline integration and adjacent-stage regression tests",
            "required image, IQ, performance or hardware evidence",
            "user-facing documentation and reproducible configuration",
            "acceptance criteria satisfied before workbook status changes to Done",
        ],
        "items": items,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("workbook", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rendered = json.dumps(build_manifest(args.workbook), indent=2, sort_keys=True) + "\n"
    if args.check:
        if not args.output.exists() or args.output.read_text(encoding="utf-8") != rendered:
            print("traceability manifest is missing or stale: {}".format(args.output))
            return 1
        print("traceability manifest is current: {}".format(args.output))
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print("wrote {} checklist mappings to {}".format(len(json.loads(rendered)["items"]), args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
