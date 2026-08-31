from __future__ import annotations

import shutil
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "submissions" / "initial_round"
PACKAGE_DIR = ROOT / "dist"
ZIP_PATH = PACKAGE_DIR / "kaoyan-knowledge-agent-initial-round.zip"

INCLUDE_DIRS = [
    "src",
    "static",
    "data",
    "scripts",
    "ascend",
    "docs",
    "reports",
    "submissions/initial_round",
]

INCLUDE_FILES = ["README.md", "run.ps1", "run.sh"]
EXCLUDE_SUFFIXES = {".pyc", ".zip", ".rar", ".7z"}
EXCLUDE_PARTS = {"__pycache__", "dist", "render_test", "npu_raw"}
EXCLUDE_NAMES = {
    "initial_creative_book_a11y.json",
    "initial_creative_book_style.json",
}


def should_include(path: Path) -> bool:
    rel_parts = set(path.relative_to(ROOT).parts)
    if rel_parts & EXCLUDE_PARTS:
        return False
    if path.suffix in EXCLUDE_SUFFIXES:
        return False
    if path.name in EXCLUDE_NAMES:
        return False
    return True


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PACKAGE_DIR.mkdir(parents=True, exist_ok=True)
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()

    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file_name in INCLUDE_FILES:
            path = ROOT / file_name
            if path.exists():
                zf.write(path, path.relative_to(ROOT))
        for dir_name in INCLUDE_DIRS:
            base = ROOT / dir_name
            if not base.exists():
                continue
            for path in base.rglob("*"):
                if path.is_file() and should_include(path):
                    zf.write(path, path.relative_to(ROOT))

    with zipfile.ZipFile(ZIP_PATH) as zf:
        nested_archives = [
            name for name in zf.namelist() if Path(name).suffix.lower() in {".zip", ".rar", ".7z"}
        ]
        if nested_archives:
            raise RuntimeError(f"Nested archives found in submission package: {nested_archives}")

    shutil.copy2(ZIP_PATH, OUT_DIR / ZIP_PATH.name)
    print(f"Wrote {ZIP_PATH}")
    print(f"Copied to {OUT_DIR / ZIP_PATH.name}")


if __name__ == "__main__":
    main()
