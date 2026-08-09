# Delivery milestones

The checklist workbook is the authoritative backlog. Milestones sequence work;
they do not override dependencies or acceptance criteria.

| Milestone | Exit condition |
| --- | --- |
| M1 — Foundation | Installable package, stage contracts, traceability, verifier, current-stage adapters, fixes 112–117 and passing CI |
| M2 — Linear core | Source-backed RAW front end producing a validated linear Bayer frame |
| M3 — Controls | Statistics, metadata history and stable AE/AWB/AF feedback loops |
| M4 — Image quality and product output | Demosaic, denoise, color, detail, geometry, output, tuning and objective-IQ workflows |
| M5 — HDR and sensors | Generic and sensor-native HDR plus required advanced sensor/CFA integrations |
| M6 — Drone and optional | IMU synchronization followed by drone/computational-imaging and optional capabilities |
| M7 — Release | Performance, memory, robustness, provenance, legal and release-qualification gates complete |

## Definition of Done

A checklist item is done only when all applicable evidence exists:

- typed configuration and declared input/output contract;
- source-backed implementation with provenance and license review;
- unit tests and numerical invariants;
- adjacent-stage and full-pipeline regression coverage;
- required image, IQ, performance, calibration or hardware artifacts;
- reproducible configuration and user-facing documentation;
- acceptance criteria reviewed before changing the workbook status to `Done`.

`N/A` is used only when the capability is demonstrably inapplicable. A missing
sensor-vendor or NDA artifact is a dependency block, not completion.
