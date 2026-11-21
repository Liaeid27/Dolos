"""Steam's per-title transfer counters for the open Downloads view."""
import re
import subprocess
import time

def tail(path,limit):
    with path.open("rb") as file:
        file.seek(max(0,file.seek(0,2)-limit))
        return file.read().decode("utf8","replace")

def update(steam,apps):
    try:
        content=tail(steam/"logs/content_log.txt",524288)
        active={}
        for key,state in re.findall(r"AppID (\d+) App update changed : ([^\r\n]*)",content):
            active[key]="Running Update" in state
        for key,busy in active.items():
            if not busy or key not in apps:continue
            log=steam/"logs/console_log.txt"
            with log.open("rb") as stream:
                stream.seek(0,2)
                subprocess.Popen([str(steam/"steam.exe"),"+app_update_status",key],creationflags=subprocess.CREATE_NO_WINDOW)
                data=b""
                for _ in range(8):
                    time.sleep(.075);data+=stream.read(32768)
                    if b" - Memory " in data:break
            merge(apps[key],key,data.decode("utf8","replace"))
    except (OSError,ValueError):return

def merge(row,key,data):
    start=re.search(r"App Update Info "+re.escape(key)+r" :",data)
    if not start:return
    block=data[start.end():].split("App Update Info",1)[0]
    flags=re.search(r"State flags\s+: ([^\r\n]+)",block)
    if not flags or "Running Update" not in flags[1]:return
    stages={name:(int(done),int(total)) for name,done,total in re.findall(r" - ([A-Za-z ]+?)\s+: (\d+)/(\d+) bytes",block)}
    for name,label in (("Downloading","Herunterladen"),("Copying","Kopieren"),("Staging","Installieren"),("Verifying Staged","Überprüfen"),("Committing","Abschließen"),("Preallocating","Speicher vorbereiten")):
        done,total=stages.get(name,(0,0))
        if total and done<total and (name in flags[1] or name=="Copying" and "Committing" in flags[1]):
            row.update(state="downloading" if name=="Downloading" else "staging",phase=label,done=done,total=total)
            return
    row.update(state="staging",phase="Dateien werden abgeschlossen",done=0,total=0)
