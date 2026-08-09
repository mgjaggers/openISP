# Modular architecture

The public processing boundary is `Stage.process(Frame, PipelineContext) ->
Frame`. A `Frame` carries the pixel array together with its semantic domain,
declared numerical range, Bayer pattern, per-frame metadata and named artifacts.
Mutable statistics, control state and history live in `PipelineContext`.

The pipeline validates stage order before processing. An enabled stage may run
only when the current pixel domain is accepted and its declared dependencies
have already been provided. Disabled stages are true bypasses: they do not
change the frame domain or satisfy dependencies.

The initial package adapts all 15 historical `model.*` algorithms through
`openisp.stages`. This retains their import paths for compatibility while
isolating mutation and implicit-domain behavior behind the new contract.
Algorithms can now be replaced independently without changing the pipeline or
configuration interface.

## Package ownership

| Area | Responsibility |
| --- | --- |
| `openisp.core` | Frames, domains, numerical policy, registry, configuration and execution |
| `openisp.stages` | Stabilized adapters for the current reference algorithms |
| `model` | Compatibility-only historical implementation paths |
| `tools` | Workbook verification and traceability generation |
| `tests/unit` | Stage contracts and numerical invariants |
| `tests/integration` | Stage ordering and end-to-end pipeline behavior |
| `tests/regression` | Fixed numerical/image outputs |
| `tests/performance` | Bounded timing and peak-memory checks |

As checklist work proceeds, new algorithms are placed in the target package
recorded in `docs/checklist_mapping.json`; `openisp.stages` remains the assembly
and compatibility layer until every historical implementation is retired.
