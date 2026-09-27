"""Package the project as dist/Letterboxd_Thesis_Dataset_Project.zip.

Excludes caches, virtual environments and the dist/ folder itself. Raw and
processed review data ARE included when present, so do not share the ZIP
publicly if it contains review data you are not allowed to redistribute.
"""
import sys
import zipfile
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import config

EXCLUDE_DIRS = {"__pycache__", ".venv", "dist", ".pytest_cache", ".git"}


def make_zip() -> Path:
    root = config.PROJECT_ROOT
    out = root / "dist" / "Letterboxd_Thesis_Dataset_Project.zip"
    out.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(root.rglob("*")):
            rel = path.relative_to(root)
            if any(part in EXCLUDE_DIRS for part in rel.parts) or path.is_dir():
                continue
            zf.write(path, Path("letterboxd_thesis") / rel)
    return out


if __name__ == "__main__":
    print(make_zip())
