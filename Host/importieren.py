"""Import installed Steam titles into the local Apollo application list."""
import argparse
import datetime
import json
import os
from pathlib import Path
import shutil
import sys
import subprocess
import tempfile
import uuid
import winreg

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).parent / "vendor"))
import vdf
from katalog import expand, grid_art, steam_covers

NAMESPACE = uuid.UUID("fd8d54e6-ddf4-4356-9bb8-b319c2ca0b8f")
POWER = "Dolos • Ausschalten"


def steam_path():
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as key:
        return Path(winreg.QueryValueEx(key, "SteamPath")[0])


def read_vdf(path):
    with path.open(encoding="utf-8-sig", errors="replace") as stream:
        return vdf.load(stream)


def collect(steam):
    roots = read_vdf(steam / "steamapps/libraryfolders.vdf")["libraryfolders"]
    games = {}
    for library in roots.values():
        folder = Path(library["path"]) / "steamapps"
        for manifest in folder.glob("appmanifest_*.acf"):
            g = read_vdf(manifest)["AppState"]
            appid = g["appid"]
            if not appid.isdecimal() or not int(g["StateFlags"]) & 4:
                continue
            if appid in {"228980","250820","1070560","1628350","1391110"}:
                continue
            cover = steam / "appcache/librarycache" / appid / "library_600x900.jpg"
            games[appid] = (g["name"], cover)
    for file in (steam / "userdata").glob("*/config/shortcuts.vdf"):
        with file.open("rb") as stream:
            shortcuts = vdf.binary_load(stream, alt_format=False)["shortcuts"]
        for shortcut in shortcuts.values():
            g = {k.lower(): value for k, value in shortcut.items()}
            if not g.get("appid") or not g.get("appname"):
                continue
            sid = g["appid"] & 0xffffffff
            gameid = str((sid << 32) | 0x02000000)
            covers = file.parent / "grid"
            cover = next((p for key in (str(sid), gameid) for ext in ("png","jpg")
                          if (p := covers / (key + "p." + ext)).exists()), None)
            games[gameid] = (g["appname"], cover)
    return games


def prepare_covers(games, folder):
    folder.mkdir(parents=True,exist_ok=True)
    jobs = []
    converted = {}
    for appid,(name,cover) in games.items():
        target = folder / (appid+".png")
        jobs.append(dict(id=appid,name=name,source=str(cover) if cover and cover.is_file() else "",target=str(target)))
        converted[appid] = (name,target)
    with tempfile.TemporaryDirectory() as temp:
        manifest = Path(temp)/"covers.json"
        manifest.write_text(json.dumps(jobs,ensure_ascii=False),encoding="utf-8")
        subprocess.run(["powershell.exe","-NoProfile","-File",str(Path(__file__).with_name("Cover.ps1")),
                        "-Manifest",str(manifest)],check=True)
    return converted


def entry(key, name, **options):
    return {"uuid":str(uuid.uuid5(NAMESPACE,key)).upper(), "name":name,
            "aster-managed":True, "virtual-display":True, **options}


def merge(config, games, power, states=None, helper=None):
    states=states or {}
    helper=helper or Path(__file__).with_name("steam_aktion.py").resolve()
    interpreter=Path(sys.executable).with_name("pythonw.exe")
    def command(key,action):
        return subprocess.list2cmdline([str(interpreter),str(helper),key,action])
    apps = [a for a in config["apps"] if not a.get("aster-managed")]
    names = {a["name"].casefold() for a in apps}
    for appid, (name,cover) in sorted(games.items(),key=lambda item:item[1][0].casefold()):
        if name.casefold() in names:
            name=f"{name} ({appid})"
        options = {"detached":["steam://rungameid/"+appid], "image-path":"steam.png"}
        if states.get(appid)!="shortcut" and int(appid)<=0xffffffff:
            options["detached"]=[command(appid,"open")]
        if cover and cover.is_file():
            options["image-path"] = str(cover)
        apps.append(entry("steam/"+appid,name+" [AC:"+appid+":"+states.get(appid,"installed")+"]",**options))
        names.add(name.casefold())
        if states.get(appid)=="installed":
            apps.append(entry("remove/"+appid,"[AC-REMOVE:"+appid+"]",detached=[command(appid,"remove")]))
    if states.get("105600","installed")=="installed" and "105600" in games:
        # Terraria exposes a dedicated local save directory on its command line.
        # Other games require their own verified mechanism before appearing here.
        for slot in (1,2,3):
            saves = Path(os.environ["LOCALAPPDATA"])/"Aster"/"Spieler"/str(slot)/"Terraria"
            steam = steam_path()/"steam.exe"
            command = subprocess.list2cmdline([str(steam),"-applaunch","105600","-savedirectory",str(saves)])
            name, cover = games["105600"]
            apps.append(entry("profile/"+str(slot)+"/105600",f"[Aster P{slot}] {name}",
                              detached=[command], **{"image-path":str(cover) if cover and cover.exists() else "steam.png"}))
    if power and POWER.casefold() not in names:
        # Windows gets time to acknowledge the new stream before shutting down.
        # A zero-second shutdown preserves the normal application veto mechanism.
        apps.append(entry("power",POWER,detached=[
            'powershell.exe -NoProfile -NonInteractive -WindowStyle Hidden -Command "Start-Sleep -Seconds 10; shutdown.exe /s /t 0"']))
    apps.append(entry("live-steam","[Dolos Live]",detached=[subprocess.list2cmdline([str(interpreter),str(helper),"selected"])]))
    from dolos_pc import host_entries
    apps.extend(host_entries())
    return dict(config,apps=apps)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--apply",action="store_true")
    parser.add_argument("--power",action="store_true")
    parser.add_argument("--config",type=Path,default=Path(os.environ["ProgramFiles"])/"Apollo/config/apps.json")
    parser.add_argument("--owned",type=Path,help="Steam-Kontoexport mit rgOwnedApps oder GetOwnedGames")
    args=parser.parse_args()
    default_export=Path(__file__).with_name("Steam-Bibliothek.json")
    owned=args.owned or (default_export if default_export.is_file() else None)
    before=args.config.read_bytes()
    original=json.loads(before.decode("utf-8-sig"))
    games=collect(steam_path())
    states=expand(steam_path(),games,owned)
    from collections import Counter
    print("Katalog:",dict(Counter(states.values())))
    if args.apply:
        games=grid_art(games,args.config.parent/"aster-grid-art")
        games=steam_covers(games,args.config.parent/"aster-steam-art")
        games=prepare_covers(games,args.config.parent/"aster-covers")
    helper=(args.config.parent/"aster-steam-aktion.py").resolve()
    if args.apply:
        source=Path(__file__).with_name("steam_aktion.py").read_bytes()
        if not helper.exists() or helper.read_bytes()!=source:
            with tempfile.NamedTemporaryFile(dir=helper.parent,delete=False) as temp:
                temp.write(source)
            os.replace(temp.name,helper)
    result=merge(original,games,args.power,states,helper)
    managed=[a for a in result["apps"] if a.get("aster-managed")]
    print(f"{len(managed)} Aster-Einträge, davon {sum(a['image-path']!='steam.png' for a in managed if 'image-path' in a)} mit lokalem Cover.")
    if result==original:
        print("Bibliothek aktuell.")
        return
    if not args.apply:
        print("Vorschau. Mit --apply übernehmen.")
        return
    folder=args.config.parent
    backup=folder/("apps.before-aster-"+datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")+".json")
    with tempfile.NamedTemporaryFile(dir=folder,suffix=".tmp",delete=False) as f:
        temp=Path(f.name)
        f.write(json.dumps(result,ensure_ascii=False,indent=4).encode("utf8"))
    try:
        if before!=args.config.read_bytes():
            raise RuntimeError("Apollo-Konfiguration wurde geändert. Import erneut starten.")
        shutil.copy2(args.config,backup)
        os.replace(temp,args.config)
    finally:
        temp.unlink(missing_ok=True)
    print("Gesichert:",backup)
    print("Import abgeschlossen. Bei Bedarf Apollo nach der Sitzung neu starten.")


if __name__=="__main__":
    main()
