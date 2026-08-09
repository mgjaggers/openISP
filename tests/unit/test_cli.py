import json

import numpy as np

from openisp.cli import main


def test_cli_lists_stages_and_validates_reference_config(capsys):
    assert main(["list-stages"]) == 0
    output = capsys.readouterr().out
    assert "dead-pixel-correction" in output
    assert "white-balance-gain" in output
    assert main(["validate-config", "config/pipeline.json", "--input-domain", "bayer"]) == 0
    assert "valid: bayer -> yuv" in capsys.readouterr().out


def test_cli_writes_snapshot_and_runs_npy_pipeline(tmp_path):
    config = tmp_path / "pipeline.json"
    config.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "profile": "cli-test",
                "stages": [{"name": "brightness-contrast", "parameters": {"brightness": 1, "contrast": 0}}],
            }
        ),
        encoding="utf-8",
    )
    snapshot = tmp_path / "snapshot.json"
    assert main(["snapshot", str(config), str(snapshot)]) == 0
    assert "sha256" in snapshot.read_text(encoding="utf-8")

    input_path = tmp_path / "input.npy"
    output_path = tmp_path / "output.npy"
    np.save(input_path, np.full((2, 2, 3), 128, dtype=np.uint8), allow_pickle=False)
    assert main(
        [
            "run", str(config), str(input_path), str(output_path),
            "--input-domain", "yuv", "--minimum", "0", "--maximum", "255", "--bit-depth", "8",
        ]
    ) == 0
    result = np.load(output_path, allow_pickle=False)
    assert np.all(result[:, :, 0] == 129)
    assert np.all(result[:, :, 1:3] == 128)
    assert output_path.with_suffix(".npy.json").exists()
