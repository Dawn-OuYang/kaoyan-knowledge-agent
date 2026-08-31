from __future__ import annotations

import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ZIP_PATH = ROOT / "dist" / "kaoyan-knowledge-agent-ascend-ide.zip"

INCLUDE_DIRS = ["src", "static", "data", "scripts", "ascend", "docs", "reports"]
INCLUDE_FILES = ["README.md", "run.ps1", "run.sh"]
EXCLUDE_SUFFIXES = {".pyc", ".zip", ".rar", ".7z"}
EXCLUDE_PARTS = {"__pycache__", "dist", "render_test", "npu_raw", "runtime"}


def should_include(path: Path) -> bool:
    relative_parts = set(path.relative_to(ROOT).parts)
    return not (relative_parts & EXCLUDE_PARTS) and path.suffix.lower() not in EXCLUDE_SUFFIXES


def main() -> None:
    ZIP_PATH.parent.mkdir(parents=True, exist_ok=True)
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()

    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in INCLUDE_FILES:
            path = ROOT / name
            if path.is_file():
                archive.write(path, path.relative_to(ROOT))

        for name in INCLUDE_DIRS:
            directory = ROOT / name
            if not directory.exists():
                continue
            for path in directory.rglob("*"):
                if path.is_file() and should_include(path):
                    archive.write(path, path.relative_to(ROOT))

    with zipfile.ZipFile(ZIP_PATH) as archive:
        names = archive.namelist()
        nested = [name for name in names if Path(name).suffix.lower() in {".zip", ".rar", ".7z"}]
        required = ["src/", "data/", "scripts/", "ascend/"]
        missing = [prefix for prefix in required if not any(name.startswith(prefix) for name in names)]
        if nested or missing:
            raise RuntimeError(f"Invalid IDE bundle: nested={nested}, missing={missing}")

    print(f"Wrote {ZIP_PATH}")
    print(f"Files: {len(names)}")


if __name__ == "__main__":
    main()
