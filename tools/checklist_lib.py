"""Small, dependency-free reader for the project's XLSX checklist."""

import re
from pathlib import PurePosixPath
from typing import Dict, Iterable, List, Mapping, Tuple
from xml.etree import ElementTree as ET
from zipfile import ZipFile

MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
OFFICE_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE_REL = "http://schemas.openxmlformats.org/package/2006/relationships"


def column_number(reference: str) -> int:
    match = re.match(r"[A-Z]+", reference)
    if match is None:
        raise ValueError("invalid cell reference: {!r}".format(reference))
    value = 0
    for character in match.group(0):
        value = value * 26 + ord(character) - 64
    return value


class WorkbookReader:
    def __init__(self, path):
        self.path = path
        self.archive = ZipFile(path)
        self.shared_strings = self._read_shared_strings()
        self.sheets = self._read_sheets()

    def close(self) -> None:
        self.archive.close()

    def __enter__(self) -> "WorkbookReader":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def _read_shared_strings(self) -> List[str]:
        if "xl/sharedStrings.xml" not in self.archive.namelist():
            return []
        root = ET.fromstring(self.archive.read("xl/sharedStrings.xml"))
        return [
            "".join(node.text or "" for node in item.iter("{{{}}}t".format(MAIN)))
            for item in root.findall("{{{}}}si".format(MAIN))
        ]

    def _read_sheets(self) -> Dict[str, str]:
        workbook = ET.fromstring(self.archive.read("xl/workbook.xml"))
        relationships = ET.fromstring(self.archive.read("xl/_rels/workbook.xml.rels"))
        targets = {item.attrib["Id"]: item.attrib["Target"] for item in relationships}
        sheets = {}
        for sheet in workbook.find("{{{}}}sheets".format(MAIN)):
            target = targets[sheet.attrib["{{{}}}id".format(OFFICE_REL)]].lstrip("/")
            if not target.startswith("xl/"):
                target = str(PurePosixPath("xl") / target)
            sheets[sheet.attrib["name"]] = target
        return sheets

    def document(self, sheet_name: str):
        return ET.fromstring(self.archive.read(self.sheets[sheet_name]))

    def rows(self, sheet_name: str) -> Iterable[Tuple[int, Dict[int, str]]]:
        root = self.document(sheet_name)
        for row in root.findall(".//{{{}}}sheetData/{{{}}}row".format(MAIN, MAIN)):
            values = {}
            for cell in row.findall("{{{}}}c".format(MAIN)):
                index = column_number(cell.attrib["r"])
                value = cell.find("{{{}}}v".format(MAIN))
                cell_type = cell.attrib.get("t")
                if cell_type == "s" and value is not None:
                    text = self.shared_strings[int(value.text)]
                elif cell_type == "inlineStr":
                    text = "".join(
                        node.text or "" for node in cell.iter("{{{}}}t".format(MAIN))
                    )
                elif value is not None:
                    text = value.text or ""
                else:
                    text = ""
                values[index] = text.replace("\n", " ")
            yield int(row.attrib["r"]), values

    def formulas(self, sheet_name: str) -> Mapping[str, str]:
        result = {}
        for cell in self.document(sheet_name).iter("{{{}}}c".format(MAIN)):
            formula = cell.find("{{{}}}f".format(MAIN))
            if formula is not None:
                result[cell.attrib["r"]] = formula.text or ""
        return result


def table(reader: WorkbookReader, sheet_name: str, header_row: int = 3) -> Tuple[List[str], List[Dict[str, str]]]:
    indexed_rows = dict(reader.rows(sheet_name))
    header_values = indexed_rows[header_row]
    maximum_column = max(header_values)
    headers = [header_values.get(index, "") for index in range(1, maximum_column + 1)]
    records = []
    for row_number in sorted(indexed_rows):
        if row_number <= header_row:
            continue
        values = indexed_rows[row_number]
        record = {header: values.get(index, "") for index, header in enumerate(headers, start=1)}
        record["_row"] = str(row_number)
        records.append(record)
    return headers, records


def checklist_records(path) -> Tuple[List[str], List[Dict[str, str]]]:
    with WorkbookReader(path) as reader:
        headers, rows = table(reader, "Checklist")
    return headers, [row for row in rows if row.get("ID")]
