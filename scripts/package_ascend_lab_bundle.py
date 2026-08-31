from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORK_ROOT = PROJECT_ROOT.parent
MINDSPEED_MM_ROOT = WORK_ROOT / "attachments" / "attachment7_extracted" / "MindSpeed-MM"
ZIP_PATH = PROJECT_ROOT / "dist" / "kaoyan-ascend-lab-bundle.zip"

PROJECT_DIRS = ["src", "static", "data", "scripts", "ascend", "docs", "reports"]
PROJECT_FILES = ["README.md", "run.ps1", "run.sh"]
ARCHIVE_SUFFIXES = {".zip", ".rar", ".7z"}
EXCLUDED_PARTS = {
    ".git",
    "__pycache__",
    "dist",
    "logs",
    "npu_raw",
    "render_test",
    "runtime",
    "submissions",
}
EXCLUDED_SUFFIXES = ARCHIVE_SUFFIXES | {".pyc", ".pyo"}


def include(path: Path, root: Path) -> bool:
    relative = path.relative_to(root)
    return not (set(relative.parts) & EXCLUDED_PARTS) and path.suffix.lower() not in EXCLUDED_SUFFIXES


def add_tree(archive: zipfile.ZipFile, source: Path, archive_root: Path) -> None:
    for path in source.rglob("*"):
        if path.is_file() and include(path, source):
            archive.write(path, archive_root / path.relative_to(source))


def main() -> None:
    if not MINDSPEED_MM_ROOT.is_dir():
        raise FileNotFoundError(f"Attachment 7 source not found: {MINDSPEED_MM_ROOT}")

    ZIP_PATH.parent.mkdir(parents=True, exist_ok=True)
    ZIP_PATH.unlink(missing_ok=True)

    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in PROJECT_FILES:
            path = PROJECT_ROOT / name
            if path.is_file():
                archive.write(path, Path("kaoyan-knowledge-agent") / name)

        for name in PROJECT_DIRS:
            source = PROJECT_ROOT / name
            if source.is_dir():
                add_tree(archive, source, Path("kaoyan-knowledge-agent") / name)

        add_tree(archive, MINDSPEED_MM_ROOT, Path("MindSpeed-MM"))

    with zipfile.ZipFile(ZIP_PATH) as archive:
        names = archive.namelist()
        nested = [name for name in names if Path(name).suffix.lower() in ARCHIVE_SUFFIXES]
        required = [
            "kaoyan-knowledge-agent/ascend/check_hidevlab_compatibility.sh",
            "kaoyan-knowledge-agent/ascend/annotations_slim.json",
            "MindSpeed-MM/pyproject.toml",
            "MindSpeed-MM/mindspeed_mm/fsdp/train/trainer.py",
            "MindSpeed-MM/examples/qwen3_5/qwen3_5_0.8B_config.yaml",
        ]
        missing = [name for name in required if name not in names]
        if nested or missing:
            raise RuntimeError(f"Invalid Ascend lab bundle: nested={nested}, missing={missing}")

    digest = hashlib.sha256(ZIP_PATH.read_bytes()).hexdigest().upper()
    print(f"Wrote {ZIP_PATH}")
    print(f"Files: {len(names)}")
    print(f"SHA-256: {digest}")


if __name__ == "__main__":
    main()
