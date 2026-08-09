# Checklist evidence

Each checklist item reserves `artifacts/checklist/<ID>.json` as its evidence
index. An index records the implementation revision, configuration snapshot,
test commands, metrics and artifact paths used to justify a workbook status
change. Binary captures and large generated images belong in managed external
storage; their immutable identifiers and hashes belong in the JSON index.

The workbook remains the status authority. A source file or passing unit test
alone is not sufficient to mark an item `Done`.
