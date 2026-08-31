from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "ascend" / "qwen3_5_kaoyan_config.yaml"


EXPERIMENTS = {
    "baseline": {"recompute": "false", "profile": "false", "memory_profile": "false"},
    "runtime-optimized": {"recompute": "false", "profile": "false", "memory_profile": "false"},
    "memory-optimized": {"recompute": "true", "profile": "true", "memory_profile": "true"},
}


def render(template: str, values: dict[str, str]) -> str:
    result = template
    for key, value in values.items():
        result = result.replace(f"__{key}__", value)
    unresolved = sorted(part for part in result.split() if part.startswith("__") and part.endswith("__"))
    if unresolved:
        raise ValueError(f"Unresolved template values: {unresolved}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Render portable MindSpeed-MM configs for an Ascend server.")
    parser.add_argument("--hf-model-dir", required=True)
    parser.add_argument("--dcp-model-dir", required=True)
    parser.add_argument("--output-root", default=str(ROOT / "ascend" / "runtime"))
    args = parser.parse_args()

    output_root = Path(args.output_root).expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    template = TEMPLATE.read_text(encoding="utf-8")
    dataset_path = ROOT / "ascend" / "annotations_slim.json"
    dataset_samples = len(json.loads(dataset_path.read_text(encoding="utf-8")))
    generated = []

    for name, options in EXPERIMENTS.items():
        experiment_root = output_root / name
        experiment_root.mkdir(parents=True, exist_ok=True)
        values = {
            "HF_MODEL_DIR": str(Path(args.hf_model_dir).expanduser().resolve()),
            "DCP_MODEL_DIR": str(Path(args.dcp_model_dir).expanduser().resolve()),
            "DATASET_DIR": str((ROOT / "ascend").resolve()),
            "CACHE_DIR": str((experiment_root / "cache").resolve()),
            "SAVE_DIR": str((experiment_root / "checkpoints").resolve()),
            "PROFILE_DIR": str((experiment_root / "profiling").resolve()),
            "MEMORY_PROFILE_DIR": str((experiment_root / "memory_snapshot").resolve()),
            "RECOMPUTE": options["recompute"],
            "PROFILE_ENABLE": options["profile"],
            "MEMORY_PROFILE_ENABLE": options["memory_profile"],
            "MAX_SAMPLES": str(dataset_samples),
        }
        output_path = output_root / f"{name}.yaml"
        output_path.write_text(render(template, values), encoding="utf-8")
        generated.append(str(output_path))

    manifest = {
        "project_root": str(ROOT),
        "hf_model_dir": str(Path(args.hf_model_dir).expanduser().resolve()),
        "dcp_model_dir": str(Path(args.dcp_model_dir).expanduser().resolve()),
        "dataset": str(dataset_path.resolve()),
        "dataset_samples": dataset_samples,
        "generated_configs": generated,
        "experiments": EXPERIMENTS,
    }
    (output_root / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
