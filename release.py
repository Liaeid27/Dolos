"""Publish a tested pair of independently signed Dolos APKs with GitHub CLI."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

REPO = "Liaeid27/Dolos"
CERT = "a31f32afb5bed3a16f0f889b35241152d2525c04e3a77c93210f1e2c5d11eee6"

def output(*args):
    return subprocess.check_output(args, text=True, encoding="utf8")

def main():
    if len(sys.argv) != 5:
        sys.exit("release.py BUILD TV.apk REMOTE.apk PC.zip")
    build = int(sys.argv[1])
    sdk = Path(os.environ["ANDROID_HOME"]) / "build-tools" / "34.0.0"
    suffix = ".exe" if os.name == "nt" else ""
    signer = sdk / ("apksigner.bat" if os.name == "nt" else "apksigner")
    commit = output("git", "rev-parse", "HEAD").strip()
    if output("git", "status", "--porcelain").strip():
        sys.exit("Änderungen zuerst einchecken.")
    if output("gh","api",f"repos/{REPO}/commits/{commit}","--jq",".sha").strip()!=commit:
        sys.exit("Commit zuerst nach GitHub pushen.")
    with tempfile.TemporaryDirectory() as tmp:
        assets=[]
        for platform,package,source in [("TV","dev.aster.console.debug",sys.argv[2]),("Remote","dev.aster.remote.debug",sys.argv[3])]:
            first=output(sdk/("aapt"+suffix),"dump","badging",source).splitlines()[0]
            if f"name='{package}'" not in first or f"versionCode='{build}'" not in first:
                sys.exit("Unerwartetes Paket oder Buildnummer: "+platform)
            certs=re.findall(r"^Signer #\d+ certificate SHA-256 digest: (\w+)$",output(signer,"verify","--print-certs",source),re.M)
            if certs != [CERT]:
                sys.exit("Signatur prüfen: "+platform)
            apk=Path(tmp)/f"Dolos-{platform}.apk";shutil.copyfile(source,apk);assets.append(apk)
        pc=Path(tmp)/"Dolos-PC.zip";shutil.copyfile(sys.argv[4],pc);assets.append(pc)
        tag=f"build-{build}"
        subprocess.run(["gh","release","create",tag,*assets,"--repo",REPO,"--target",commit,"--draft","--title",f"Dolos · Build {build}","--generate-notes"],check=True)
        subprocess.run(["gh","release","edit",tag,"--repo",REPO,"--draft=false","--latest"],check=True)

if __name__=="__main__":
    main()
