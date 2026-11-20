"""Open one Steam action in the interactive Windows session."""
import os
import re
import sys
import time
import winreg
from pathlib import Path

def action_uri(appid,mode,steam):
    if not re.fullmatch(r"[0-9]{1,10}",appid) or int(appid)>0xffffffff:
        raise ValueError("Ungültige Steam-ID")
    if mode=="remove":return "steam://uninstall/"+appid
    if mode!="open":raise ValueError("Unbekannte Aktion")
    data=(steam/"steamapps/libraryfolders.vdf").read_text(encoding="utf-8-sig")
    roots=[steam]+[Path(p.replace("\\\\","\\")) for p in re.findall(r'"path"\s*"([^"]+)"',data)]
    for root in roots:
        manifest=root/"steamapps"/("appmanifest_"+appid+".acf")
        if manifest.exists():
            flags=re.search(r'"StateFlags"\s*"(\d+)"',manifest.read_text(encoding="utf-8-sig"))
            if flags and int(flags[1]) & 4:return "steam://rungameid/"+appid
    return "steam://install/"+appid

if __name__=="__main__":
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER,r"Software\Valve\Steam") as k:
        steam=Path(winreg.QueryValueEx(k,"SteamPath")[0])
    if sys.argv[1:]==["selected"]:
        import json
        slot=Path(os.environ["LOCALAPPDATA"])/"Dolos"/"Control"/"start.json"
        claim=slot.with_suffix(".consume")
        os.replace(slot,claim)
        record=json.loads(claim.read_text(encoding="utf8"))
        claim.unlink(missing_ok=True)
        if not time.time()<=record["until"]<=time.time()+65:sys.exit(1)
        appid=str(record["id"]);profile=record.get("profile",0)
        if profile:
            if profile not in (1,2,3) or appid not in ("105600","294100","1874880"):sys.exit(1)
            import subprocess
            path=Path(os.environ["LOCALAPPDATA"])/"Aster"/"Spieler"/str(profile)/("Terraria" if appid=="105600" else appid)
            path.mkdir(parents=True,exist_ok=True)
            flags={"105600":["-savedirectory",str(path)],"294100":["-savedatafolder="+str(path)],"1874880":["-profile",str(path),"-backendLocalStorage"]}
            subprocess.Popen([str(steam/"steam.exe"),"-applaunch",appid,*flags[appid]])
            sys.exit(0)
        sys.argv=[sys.argv[0],appid,"open"]
    uri=action_uri(sys.argv[1],sys.argv[2],steam)
    if sys.argv[2]=="open" and uri.startswith("steam://install/"):
        sys.exit(0)
    if not uri.startswith("steam://rungameid/"):
        os.startfile("steam://open/bigpicture")
        time.sleep(1)
    os.startfile(uri)
