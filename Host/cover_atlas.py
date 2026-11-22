"""Build versioned, immutable 8 × 8 TV thumbnail sheets."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile


def prepare(folder, files):
    covers = []
    for (key, kind), path in sorted(files.items()):
        if kind != "cover":
            continue
        try:
            stat = path.stat()
        except FileNotFoundError:
            continue
        covers.append((key, str(path), stat.st_mtime_ns, stat.st_size))
    if not covers:
        return {}
    # Version the layout as well as the source files so 340 clients discard stretched thumbnails.
    signature = json.dumps(["proportional-q68", covers]).encode()
    revision = str(int.from_bytes(hashlib.sha256(signature).digest()[:5], "big"))
    parent = folder / "cover-atlas"
    parent.mkdir(parents=True, exist_ok=True)
    destination = parent / revision
    if not destination.is_dir():
        with tempfile.TemporaryDirectory(dir=parent) as temp:
            manifest = Path(temp) / "files.json"
            manifest.write_text(json.dumps([row[1] for row in covers]), encoding="utf8")
            output = Path(temp) / "pages"
            output.mkdir()
            subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-File",
                            str(Path(__file__).with_name("CoverAtlas.ps1")), str(manifest), str(output)],
                           creationflags=subprocess.CREATE_NO_WINDOW, check=True, timeout=150, capture_output=True)
            indices = (output / "indices.txt").read_text(encoding="utf-8-sig").splitlines()
            ids = [covers[int(index)][0] for index in indices]
            if any(not (output / f"{n}.jpg").is_file() for n in range((len(ids) + 63) // 64)):
                raise ValueError("Unvollständiger Cover-Atlas")
            (output / "indices.txt").unlink()
            (output / "ids.json").write_text(json.dumps(ids), encoding="utf8")
            try:
                output.rename(destination)
            except OSError:
                if not destination.is_dir():
                    raise
        older = sorted((p for p in parent.iterdir() if p.name.isdecimal() and p != destination),
                       key=lambda p: p.stat().st_mtime, reverse=True)
        for path in older[1:]:
            shutil.rmtree(path, ignore_errors=True)
    ids = json.loads((destination / "ids.json").read_text(encoding="utf8"))
    return {"rev": revision, "ids": ids} if ids else {}
