"""Command-line interface for inspecting and running modular pipelines."""

import argparse
import json
from pathlib import Path
from typing import Optional, Sequence

import numpy as np

from openisp import stages as _builtin_stages  # noqa: F401
from openisp.core.config import PipelineConfig
from openisp.core.frame import Frame, FrameMetadata, PixelRange
from openisp.core.pipeline import Pipeline
from openisp.core.registry import registry
from openisp.core.types import CfaPattern, PixelDomain


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="openisp", description="Modular openISP reference pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list-stages", help="list registered stage names")

    validate = subparsers.add_parser("validate-config", help="validate a pipeline configuration")
    validate.add_argument("config", type=Path)
    validate.add_argument("--input-domain", choices=[item.value for item in PixelDomain], default="bayer")

    snapshot = subparsers.add_parser("snapshot", help="write a canonical configuration snapshot")
    snapshot.add_argument("config", type=Path)
    snapshot.add_argument("output", type=Path)

    run = subparsers.add_parser("run", help="run a pipeline on a NumPy .npy image")
    run.add_argument("config", type=Path)
    run.add_argument("input", type=Path)
    run.add_argument("output", type=Path)
    run.add_argument("--input-domain", choices=[item.value for item in PixelDomain], default="bayer")
    run.add_argument("--cfa", choices=[item.value for item in CfaPattern], default="rggb")
    run.add_argument("--minimum", type=float, default=0.0)
    run.add_argument("--maximum", type=float, default=1023.0)
    run.add_argument("--bit-depth", type=int, default=10)
    run.add_argument("--frame-id", type=int, default=0)
    run.add_argument("--export-intermediates", type=Path)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "list-stages":
        for name in registry.names():
            print(name)
        return 0

    config = PipelineConfig.load(args.config)
    if args.command == "snapshot":
        config.write_snapshot(args.output)
        print("{} {}".format(config.digest(), args.output))
        return 0

    domain = PixelDomain(args.input_domain)
    pipeline = Pipeline.from_config(
        config,
        export_directory=getattr(args, "export_intermediates", None),
    )
    output_domain = pipeline.validate(domain)
    if args.command == "validate-config":
        print("valid: {} -> {} ({} stages)".format(domain.value, output_domain.value, len(pipeline.stages)))
        return 0

    data = np.load(str(args.input), allow_pickle=False)
    cfa = CfaPattern(args.cfa) if domain == PixelDomain.BAYER else None
    frame = Frame(
        data=data,
        domain=domain,
        pixel_range=PixelRange(args.minimum, args.maximum, args.bit_depth),
        cfa=cfa,
        metadata=FrameMetadata(frame_id=args.frame_id),
    )
    result = pipeline.run(frame)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.save(str(args.output), result.frame.data, allow_pickle=False)
    report_path = args.output.with_suffix(args.output.suffix + ".json")
    report_path.write_text(
        json.dumps(
            {
                "domain": result.frame.domain.value,
                "dtype": str(result.frame.data.dtype),
                "shape": list(result.frame.data.shape),
                "executed_stages": list(result.executed_stages),
                "bypassed_stages": list(result.bypassed_stages),
                "configuration_sha256": config.digest(),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print("wrote {} ({})".format(args.output, result.frame.domain.value))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
