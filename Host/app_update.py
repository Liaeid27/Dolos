"""Publish a versioned APK atomically for paired Dolos devices."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import tempfile
import zipfile

def apk_version(path):
    with zipfile.ZipFile(path) as archive:
        entry = archive.getinfo("AndroidManifest.xml")
        if entry.file_size > 4_000_000:
            raise ValueError("Ungültiges APK-Manifest")
        data = archive.read(entry)
    pos = 8
    resources = []
    while pos + 8 <= len(data):
        kind, header, length = struct.unpack_from("<HHI", data, pos)
        if length < header or header < 8 or pos + length > len(data):
            break
        if kind == 0x180:
            resources = list(struct.unpack_from("<" + "I" * ((length-header)//4), data, pos+header))
        if kind == 0x102:
            ext = pos + header
            start, stride, count = struct.unpack_from("<HHH", data, ext+8)
            for i in range(count):
                a = ext + start + i*stride
                name = struct.unpack_from("<I", data, a+4)[0]
                if name < len(resources) and resources[name] == 0x0101021b:
                    return struct.unpack_from("<I", data, a+16)[0]
            break
        pos += length
    raise ValueError("APK enthält keinen lesbaren Android-Versionscode.")

def publish(source, folder):
    from dolos_pc import save
    folder.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=folder,delete=False) as temp:
        staging = Path(temp.name)
    try:
        with open(source,"rb") as src, staging.open("wb") as dst:
            shutil.copyfileobj(src,dst)
        size = staging.stat().st_size
        if not 0 < size <= 256*1024**2:
            raise ValueError("APK zu groß oder leer.")
        version = apk_version(staging)
        with staging.open("rb") as stream:
            digest = hashlib.file_digest(stream,"sha256").hexdigest() if hasattr(hashlib,"file_digest") else hashlib.sha256(stream.read()).hexdigest()
        os.replace(staging,folder/(digest+".apk"))
        doc = dict(version=version,sha256=digest,size=size)
        save(folder/"release.json",doc)
        return doc
    finally:
        staging.unlink(missing_ok=True)
