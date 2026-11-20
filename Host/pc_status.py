"""Read-only status of local console services."""
import json,os,socket,winreg,re
from pathlib import Path

def reachable(port):
    try:
        with socket.create_connection(("127.0.0.1",port),.5):return True
    except OSError:return False

def apollo_port():
    path=Path(os.environ["ProgramFiles"])/"Apollo/config/sunshine.conf"
    try:
        m=re.search(r"(?m)^\s*port\s*=\s*([0-9]+)\s*$",path.read_text(encoding="utf8",errors="replace"))
        return int(m[1]) if m else 47989
    except OSError:return 47989

def statuses(root):
    from dolos_control import DATA
    def read(path,default):
        try:return json.loads(path.read_text(encoding="utf-8-sig"))
        except (ValueError,OSError):return default
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,r"Software\Valve\Steam\ActiveProcess") as key:
            steam=bool(winreg.QueryValueEx(key,"ActiveUser")[0])
    except OSError:steam=False
    clients=read(DATA/"clients.json",[])
    build=read(DATA/"updates/release.json",{}).get("version")
    linked=bool(read(root/"Steam-Konto.json",{}).get("steamid"))
    return [("Steam","Angemeldet" if steam else "Keine lokale Anmeldung"),("Kontoimport","Verknüpft" if linked else "Kein Konto verknüpft"),("Apollo","Erreichbar" if reachable(apollo_port()) else "Offline"),("Verwaltung",("Erreichbar · "+str(len(clients))+" gekoppelt") if reachable(48291) else "Offline"),("Update",("Build "+str(build)) if build else "Keine APK bereitgestellt")]
