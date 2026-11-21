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


BUILTIN_PROFILES={"105600","294100","1874880","1903340"}
def control_root():return Path(os.environ["LOCALAPPDATA"])/"Dolos"/"Control"
def folders():
    import json
    file=control_root()/"save-folders.json"
    return json.loads(file.read_text(encoding="utf8")) if file.is_file() else {}

def running(key):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,"Software\\Valve\\Steam\\Apps\\"+key) as reg:return bool(winreg.QueryValueEx(reg,"Running")[0])
    except OSError:return False

def validate_folder(path):
    raw=Path(path);path=raw.resolve()
    roots=[Path(os.environ["LOCALAPPDATA"]),Path(os.environ["APPDATA"]),Path.home()/"AppData/LocalLow",Path.home()/"Documents",Path.home()/"Saved Games"]
    if path!=raw.absolute() or not any(path.is_relative_to(root.resolve()) and len(path.relative_to(root.resolve()).parts)>=2 for root in roots):
        raise ValueError("Wähle den Unterordner mit den Spielständen dieses Spiels.")
    return path

def profile_path(key,slot):
    if not key.isdecimal() or slot not in (1,2,3):raise ValueError("Ungültiges Profil.")
    if key in BUILTIN_PROFILES:return Path(os.environ["LOCALAPPDATA"])/"Aster/Spieler"/str(slot)/("Terraria" if key=="105600" else key)
    normal=validate_folder(folders()[key])
    return normal.parent/(".dolos-saves-"+key)/str(slot)

from contextlib import contextmanager
@contextmanager
def save_lock(key):
    import msvcrt
    file=control_root()/("profile-"+key+".lock")
    with file.open("a+b") as lock:
        if lock.tell()==0:lock.write(b"0");lock.flush()
        lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_LOCK,1)
        try:yield
        finally:lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)

def restore_saved(key):
    import json
    marker=control_root()/("active-"+key+".json")
    if not marker.exists():return
    slot=json.loads(marker.read_text())["slot"];normal=validate_folder(folders()[key])
    other=profile_path(key,slot);standard=other.parent/"Standard"
    if standard.exists():
        if normal.exists():
            if other.exists():raise ValueError("Zwei Profilordner vorhanden. Speicherordner am PC prüfen.")
            normal.rename(other)
        standard.rename(normal)
    if not normal.is_dir():raise ValueError("Standard-Spielstandordner fehlt.")
    marker.unlink()

def switch_saves(key,slot):
    import json
    if key not in folders():return
    with save_lock(key):
        if running(key):raise ValueError("Spiel zuerst beenden.")
        restore_saved(key)
        if not slot:return
        normal=validate_folder(folders()[key]);other=profile_path(key,slot)
        if not normal.is_dir():raise ValueError("Spielstandordner fehlt.")
        other.mkdir(parents=True,exist_ok=True);standard=other.parent/"Standard"
        if standard.exists() or normal.is_junction() or normal.is_symlink() or other.is_symlink() or other.parent.is_symlink() or other.is_junction() or other.parent.is_junction():raise ValueError("Profilordner prüfen.")
        marker=control_root()/("active-"+key+".json");temp=marker.with_suffix(".tmp")
        temp.write_text(json.dumps(dict(slot=slot,start=time.time())));temp.replace(marker)
        normal.rename(standard)
        try:other.rename(normal)
        except OSError:restore_saved(key);raise

def restore_idle(seen):
    import json
    for marker in control_root().glob("active-*.json"):
        key=marker.stem[7:]
        with save_lock(key):
            if not marker.exists():continue
            now=time.time()
            if running(key):seen[key]=now;continue
            if now-seen.get(key,json.loads(marker.read_text())["start"]+170)>10:
                restore_saved(key);seen.pop(key,None)

def launch_game(steam,appid,profile,display_args=()):
    import subprocess
    if profile not in range(4) or not appid.isdecimal() or len(appid)>10:raise ValueError("Ungültiger Spielstart.")
    args=[]
    if appid in folders():switch_saves(appid,profile)
    elif profile:
        if appid not in BUILTIN_PROFILES:raise ValueError("Speicherordner für dieses Spiel einrichten.")
        path=profile_path(appid,profile);path.mkdir(parents=True,exist_ok=True)
        args={"1903340":["-UserDir="+str(path)],"105600":["-savedirectory",str(path)],"294100":["-savedatafolder="+str(path)],"1874880":["-profile",str(path),"-backendLocalStorage"]}[appid]
    subprocess.Popen([str(steam/"steam.exe"),"-applaunch",appid,*args,*display_args])

if __name__=="__main__":
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER,r"Software\Valve\Steam") as k:
        steam=Path(winreg.QueryValueEx(k,"SteamPath")[0])
    selected=sys.argv[1:]==["selected"]
    if not selected and len(sys.argv)==3 and sys.argv[2]=="open" and sys.argv[1] in folders():switch_saves(sys.argv[1],0)
    if selected:
        import json
        slot=Path(os.environ["LOCALAPPDATA"])/"Dolos"/"Control"/"start.json"
        claim=slot.with_suffix(".consume")
        os.replace(slot,claim)
        record=json.loads(claim.read_text(encoding="utf8"))
        claim.unlink(missing_ok=True)
        if not time.time()<=record["until"]<=time.time()+65:sys.exit(1)
        appid=str(record["id"]);profile=record.get("profile",0)
        launch_game(steam,appid,profile);sys.exit(0)
    uri=action_uri(sys.argv[1],sys.argv[2],steam)
    if sys.argv[2]=="open" and uri.startswith("steam://install/"):
        sys.exit(0)
    if not uri.startswith("steam://rungameid/"):
        os.startfile("steam://open/bigpicture")
        time.sleep(1)
    if uri.startswith("steam://rungameid/"):
        import subprocess
        subprocess.Popen([str(steam/"steam.exe"),"-applaunch",sys.argv[1]])
    else:os.startfile(uri)
