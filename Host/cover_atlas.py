"""Generate immutable TV thumbnail sheets once per change to the PC artwork."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import shutil

def prepare(folder,files):
    covers=sorted((key,path) for (key,kind),path in files.items() if kind=="cover")
    if not covers:return {}
    signature=json.dumps([(key,path.stat().st_mtime_ns,path.stat().st_size) for key,path in covers]).encode()
    revision=str(int.from_bytes(hashlib.sha256(signature).digest()[:5],"big"))
    parent=folder/"cover-atlas";parent.mkdir(parents=True,exist_ok=True)
    destination=parent/revision
    if not destination.is_dir():
        with tempfile.TemporaryDirectory(dir=parent) as temp:
            temp=Path(temp);manifest=temp/"files.json"
            manifest.write_text(json.dumps([str(path) for _,path in covers]),encoding="utf8")
            output=temp/"pages";output.mkdir()
            subprocess.run(["powershell.exe","-NoProfile","-NonInteractive","-File",str(Path(__file__).with_name("CoverAtlas.ps1")),str(manifest),str(output)],creationflags=subprocess.CREATE_NO_WINDOW,check=True,timeout=150,capture_output=True)
            if not (output/f"{(len(covers)-1)//64}.jpg").is_file():return {}
            output.rename(destination)
        older=sorted((p for p in parent.iterdir() if p.name.isdecimal() and p!=destination),key=lambda p:p.stat().st_mtime,reverse=True)
        for p in older[1:]:shutil.rmtree(p,ignore_errors=True)
    return {"rev":revision,"ids":[key for key,_ in covers]}
