"""Dolos LAN controller. Authenticated HTTPS, bounded commands, no desktop transport."""
import argparse, collections, datetime, hashlib, hmac, json, os, secrets, shutil, socket, ssl, subprocess, sys, threading, time, winreg
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from dolos_pc import save
from importieren import steam_path,read_vdf

PORT=48291
DATA=Path(os.environ["LOCALAPPDATA"])/"Dolos"/"Control"
LOCK=threading.RLock()
LAST={}
QUEUE=[]
PAUSED=False
ATTEMPTS=collections.deque(maxlen=24)
PENDING_OFF=False
DOWNLOAD_ACTION={}
LAUNCH_TERMS={}
CATALOG=[]
REQUIRED={}
SIZE_STAMP=None
DISKS=[]
COVERS={}
STORE_LINKS={}
SAVE_TIMES={}
from save_times import subnautica_slots
ART_FILES={}
ART_REVISIONS={}
ATLAS={}
MEDIA={}
def store_worker():
    from store_cache import update,warm_heroes
    folder=DATA/"store-media"
    for path in folder.glob("*.json"):
        try:
            row=json.loads(path.read_text(encoding="utf8"))
            if row.get("header"):MEDIA[path.stem]=row
        except (ValueError,OSError):continue
    while True:
        if CATALOG:
            try:
                update(folder,CATALOG,ART_FILES,MEDIA)
                warm_heroes(folder,ART_FILES,MEDIA)
            except (ValueError,OSError):pass
        time.sleep(10 if not CATALOG else 300)

from steam_aktion import BUILTIN_PROFILES,folders,profile_path,restore_idle,running

def profile_helper_ready():
    helper=Path(os.environ["ProgramFiles"])/"Apollo"/"config"/"aster-steam-aktion.py"
    try:return helper.read_bytes()==Path(__file__).with_name("steam_aktion.py").read_bytes()
    except OSError:return False

def cached_art(steam,ids):
    base=steam/"appcache"/"librarycache";found={}
    for sid in ids:
        if not sid.isdecimal() or len(sid)>10:continue
        folder=base/sid
        if not folder.is_dir():continue
        for kind,filename in (("cover","library_600x900.jpg"),("hero","library_hero.jpg")):
            file=next(folder.glob("*/"+filename),folder/filename)
            if file.is_file():found[(sid,kind)]=file
    return found

def refresh_catalog():
    global CATALOG,DISKS,COVERS,STORE_LINKS,SAVE_TIMES
    from importieren import collect
    from katalog import expand
    steam=steam_path()
    games=collect(steam)
    owned=Path(__file__).with_name("Steam-Bibliothek.json")
    states=expand(steam,games,owned if owned.exists() else None)
    artwork=Path(os.environ["ProgramFiles"])/"Apollo"/"config"
    COVERS={k:bool((v[1] and v[1].is_file()) or (artwork/"aster-grid-art"/(k+".art")).is_file() or (artwork/"aster-steam-art"/(k+".jpg")).is_file()) for k,v in games.items()}
    from dolos_pc import host_entries
    for row in host_entries():COVERS[row["name"]]=bool(row.get("image-path") and Path(row["image-path"]).is_file())
    links=Path(__file__).with_name("Spielseiten.json")
    STORE_LINKS=json.loads(links.read_text(encoding="utf8")) if links.is_file() else {}
    global ART_FILES,ART_REVISIONS,ATLAS
    ART_FILES=cached_art(steam,games)
    for sid,(_,image,*rest) in games.items():
        hero=DATA/"store-media"/(sid+"-hero.jpg")
        if hero.is_file():ART_FILES.setdefault((sid,"hero"),hero)
        for candidate in (DATA/"store-media"/(sid+".jpg"),artwork/"aster-grid-art"/(sid+".art"),image,artwork/"aster-steam-art"/(sid+".jpg")):
            if candidate and candidate.is_file():
                ART_FILES.setdefault((sid,"cover"),candidate)
                break
    revisions={}
    for (sid,kind),path in ART_FILES.items():
        if kind=="cover":COVERS[sid]=True
        revisions.setdefault(sid,{})[kind]=int(path.stat().st_mtime)
    ART_REVISIONS=revisions
    from cover_atlas import prepare
    try:ATLAS=prepare(DATA,ART_FILES)
    except (OSError,ValueError,subprocess.SubprocessError):ATLAS={}
    global REQUIRED,SIZE_STAMP
    try:
        stamp=(steam/"appcache/appinfo.vdf").stat().st_mtime_ns
        if stamp!=SIZE_STAMP:
            from install_sizes import required_sizes
            REQUIRED=required_sizes(steam,set(games));SIZE_STAMP=stamp
    except (OSError,ValueError,IndexError):pass
    CATALOG=[dict(id=k,name=v[0],required=REQUIRED.get(k,0),state=states[k]) for k,v in games.items() if len(k)<=10]
    disks=[]
    times=[]
    for lib in read_vdf(steam/"steamapps/libraryfolders.vdf")["libraryfolders"].values():
        folder=Path(lib["path"])
        if folder.is_dir():
            times.extend(subnautica_slots(folder))
            usage=shutil.disk_usage(folder)
            disks.append(dict(name=folder.drive or folder.name,drive=folder.drive,total=usage.total,free=usage.free))
    SAVE_TIMES={'264710':times} if len({s['slot'] for s in times})==len(times) else {}
    DISKS=disks

def catalog_worker():
    from steam_konto import fetch_owned
    last_update=0
    while True:
        try:
            refresh_catalog()
            account=Path(__file__).with_name("Steam-Konto.json")
            if time.time()-last_update>1800 and account.is_file():
                last_update=time.time()
                doc=fetch_owned(json.loads(account.read_text(encoding="utf8"))["steamid"])
                if doc:save(Path(__file__).with_name("Steam-Bibliothek.json"),doc);refresh_catalog()
        except (OSError,ValueError,RuntimeError,KeyError):pass
        time.sleep(60)

def read(name,default):
    p=DATA/name
    if not p.exists():return default
    return json.loads(p.read_text(encoding="utf-8"))
def write(name,value):save(DATA/name,value)

def certificate():
    DATA.mkdir(parents=True,exist_ok=True)
    cert,key=DATA/"host.pem",DATA/"key.pem"
    if not (cert.exists() and key.exists()):
        openssl=shutil.which("openssl") or str(Path(os.environ["ProgramFiles"])/"Git/usr/bin/openssl.exe")
        subprocess.run([openssl,"req","-x509","-newkey","rsa:2048","-nodes","-keyout",str(key),"-out",str(cert),"-days","3650","-subj","/CN=Dolos LAN"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)
    return cert,key

def open_pairing():
    cert,_=certificate()
    pin=str(secrets.randbelow(1000000)).zfill(6)
    write("pair.json",{"hash":hashlib.sha256(pin.encode()).hexdigest(),"until":time.time()+180})
    mark=hashlib.sha256(ssl.PEM_cert_to_DER_cert(cert.read_text())).hexdigest().upper()[:12]
    return pin," ".join(mark[i:i+4] for i in range(0,12,4))

def manifests():
    steam=steam_path();roots=read_vdf(steam/"steamapps/libraryfolders.vdf")["libraryfolders"];apps={}
    for lib in roots.values():
        folder=Path(lib["path"])/"steamapps"
        for file in folder.glob("appmanifest_*.acf"):
            try:
                g=read_vdf(file)["AppState"];flags=int(g["StateFlags"])
                active=bool(flags&(1048576|2097152|4194304|262144|524288|512))
                remaining=int(g.get("BytesToDownload",0))>int(g.get("BytesDownloaded",0))
                staging=int(g.get("BytesToStage",0))>int(g.get("BytesStaged",0))
                active=active or remaining or staging or bool(flags & (2|32|1024|65536|131072))
                scheduled=int(g.get("ScheduledAutoUpdate",0))
                state=("staging" if flags&(2097152|4194304) else "downloading" if flags&(1048576|262144|524288)
                       else "paused" if flags&256 or (flags&32 and not scheduled) else "waiting" if scheduled or flags&1024 else
                       "paused" if active and not flags&65536 else "downloading" if active else "installed" if flags&4 else "waiting")
                staged=state=="staging"
                apps[g["appid"]]={"id":g["appid"],"name":g["name"],"state":state,"drive":folder.drive,"scheduled":scheduled,"partial":not int(g.get("buildid",0)) and not g.get("InstalledDepots") and not flags&4,"size":int(g.get("SizeOnDisk",0)),"done":int(g.get("BytesStaged" if staged else "BytesDownloaded",0)),"total":int(g.get("BytesToStage" if staged else "BytesToDownload",0))}
            except (ValueError,KeyError,OSError,SyntaxError):continue
    return apps

def download_command(key,action):
    global DOWNLOAD_ACTION
    if action not in ("downloadfirst","downloadpause","downloadcancel") or not key.isdecimal() or len(key)>10:
        return False,"Unbekannter Download."
    with LOCK:
        job=next((q for q in QUEUE if q["id"]==key and q["action"]=="install" and not q.get("sent")),None)
        if job:
            if action=="downloadpause":job["held"]=True
            elif action=="downloadcancel":QUEUE.remove(job)
            else:
                job.pop("held",None);QUEUE.remove(job);QUEUE.insert(0,job)
            write("queue.json",QUEUE)
            return True,None
    game=manifests().get(key)
    if not game or game["state"]=="installed":return False,"Steam hat diesen Download bereits abgeschlossen oder entfernt."
    with LOCK:
        if DOWNLOAD_ACTION.get("pending"):return False,"Steam verarbeitet noch den letzten Auftrag."
        DOWNLOAD_ACTION={"id":key,"pending":True}
    def run():
        global DOWNLOAD_ACTION
        error=None
        try:
            if action=="downloadcancel" and game["partial"]:
                current=manifests().get(key)
                if not current or not current["partial"] or running(key):raise ValueError("Der Installationszustand hat sich geändert.")
                subprocess.Popen([str(steam_path()/"steam.exe"),"+app_uninstall",key],creationflags=subprocess.CREATE_NO_WINDOW)
                for _ in range(24):
                    time.sleep(.5)
                    if key not in manifests():break
                else:raise ValueError("Steam hat den Abbruch noch nicht bestätigt.")
            else:
                result=subprocess.run([sys.executable,str(Path(__file__).with_name("steam_download.py")),action[8:],game["name"]],
                    capture_output=True,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
                reply=json.loads(result.stdout)
                if not reply.get("ok"):raise ValueError(reply.get("error","Steam konnte den Auftrag nicht ausführen."))
            if action=="downloadcancel":
                with LOCK:
                    QUEUE[:]=[q for q in QUEUE if q["id"]!=key or q["action"]!="install"]
                    write("queue.json",QUEUE)
        except (ValueError,OSError,subprocess.TimeoutExpired) as exc:
            error=str(exc) if type(exc) is ValueError else "Steam hat den Auftrag nicht bestätigt."
        finally:
            with LOCK:DOWNLOAD_ACTION={"id":key,"pending":False,"error":error}
    threading.Thread(target=run,daemon=True).start()
    return True,None

def save_candidates(key):
    from steam_aktion import validate_folder
    if key in BUILTIN_PROFILES or not key.isascii() or not key.isdecimal():return []
    game=LAST.get("apps",{}).get(key,{})
    if game.get("state")!="installed":return []
    from spiel_fenster import targets_now
    target=targets_now().get(key)
    names={game.get("name",""),target[0].name if target else ""}
    roots=[Path.home()/"Documents",Path.home()/"Documents/My Games",Path.home()/"Saved Games",Path(os.environ["LOCALAPPDATA"]),Path(os.environ["APPDATA"]),Path.home()/"AppData/LocalLow"]
    result=set()
    if key=="1145350":
        hades=Path.home()/"Saved Games/Hades II"
        if any(hades.glob("Profile[1-9].sav")) and hades.resolve()==hades.absolute():result.add(hades)
    if key=="1091500":
        cyberpunk=Path.home()/"Saved Games/CD Projekt Red/Cyberpunk 2077"
        if any(cyberpunk.glob("*/sav.dat")):
            try:result.add(validate_folder(cyberpunk))
            except ValueError:pass
    for root in roots:
        for name in names:
            if not name or Path(name).name!=name or name in (".",".."):continue
            for leaf in ("Savegames","Saves","Saved/SaveGames","SaveData","Save"):
                p=root/name/leaf
                if not p.is_dir() or p.resolve()!=p.absolute():continue
                try:result.add(validate_folder(p))
                except ValueError:continue
    return sorted(result)

def allowed(key):
    if not str(key).isdecimal() or int(key)>0xffffffff:return False
    from importieren import collect
    from katalog import expand
    games=collect(steam_path());owned=Path(__file__).with_name("Steam-Bibliothek.json")
    expand(steam_path(),games,owned if owned.is_file() else None)
    return str(key) in games

def steam_dialog(name,mode="inspect",drive=None,expected=None):
    try:
        cmd=["powershell.exe","-NoProfile","-NonInteractive","-File",str(Path(__file__).with_name("DolosDialog.ps1")),
             "-SteamRoot",str(steam_path()),"-Title",name,"-Action",mode]
        if expected:cmd.extend(["-Expected",expected])
        if drive and mode in ("inspect","install","confirm"):
            cmd=["powershell.exe","-NoProfile","-NonInteractive","-File",str(Path(__file__).with_name("SteamInstall.ps1")),
                 "-SteamRoot",str(steam_path()),"-Title",name,"-Drive",drive]
            if mode!="inspect":cmd.append("-Install")
        result=subprocess.run(cmd,capture_output=True,timeout=6,creationflags=subprocess.CREATE_NO_WINDOW)
        return json.loads(result.stdout.decode("utf-8-sig")) if result.returncode==0 else {}
    except (ValueError,OSError,subprocess.TimeoutExpired):return {}

def install_to_drive(key,drive):
    steam=steam_path()
    libraries=read_vdf(steam/"steamapps/libraryfolders.vdf")["libraryfolders"]
    choices=[index for index,library in libraries.items() if index.isascii() and index.isdecimal()
             and Path(library["path"]).drive.casefold()==drive.casefold() and Path(library["path"]).is_dir()]
    if len(choices)!=1 or not key.isascii() or not key.isdecimal():
        raise ValueError("Steam-Bibliothek nicht eindeutig verfügbar.")
    root=Path(libraries[choices[0]]["path"])
    if shutil.disk_usage(root).free<REQUIRED.get(key,1):raise ValueError("Zu wenig freier Speicher auf "+drive)
    subprocess.Popen([str(steam/"steam.exe"),"+app_install",key,choices[0]],creationflags=subprocess.CREATE_NO_WINDOW)

def steam_space_error(steam,job):
    # Only attribute errors logged after this request to this game.
    path=steam/"logs"/"content_log.txt"
    try:
        import re
        with path.open("rb") as stream:
            stream.seek(max(0,stream.seek(0,2)-65536));lines=stream.read().decode("utf8","replace").splitlines()
        for line in reversed(lines):
            if not re.search(r"(?:AppID|App) "+re.escape(job["id"])+r"\b",line,re.I):continue
            stamp=datetime.datetime.strptime(line[1:20],"%Y-%m-%d %H:%M:%S").timestamp()
            if stamp<job["sentAt"]-1:break
            if re.search(r"not enough (?:free )?disk space|disk full|insufficient disk space",line,re.I):return True
    except (ValueError,OSError,KeyError):pass
    return False

def queue_step(apps):
    global QUEUE
    with LOCK:
        changed=False
        for q in list(QUEUE):
            current=apps.get(q["id"],{}).get("state")
            if q.get("direct") and q.get("sent") and not q.get("error") and current not in ("installed","downloading","staging") and steam_space_error(steam_path(),q):
                q["error"]="Auf dem gewählten Steam-Laufwerk ist zu wenig Speicher frei.";changed=True
            if q["action"]=="install" and current=="installed" or q["action"]=="remove" and not current:
                QUEUE.remove(q);changed=True
        for q in QUEUE:
            if q["action"]=="install" and q.get("drive") and q.get("sent") and not q.get("direct") and not q.get("error") and not apps.get(q["id"]):
                q["sent"]=False;changed=True
        q=next((job for job in QUEUE if not job.get("held")),None)
        if not PAUSED and q and not any(job.get("sent") for job in QUEUE):
            try:
                if q["action"]=="install" and q.get("drive"):
                    install_to_drive(q["id"],q["drive"]);q["direct"]=True
                else:os.startfile("steam://"+("install" if q["action"]=="install" else "uninstall")+"/"+q["id"])
                q.pop("error",None)
            except ValueError as err:q["error"]=str(err)
            except (OSError,KeyError):q["error"]="Steam oder die gewählte Bibliothek ist nicht verfügbar."
            q["sent"]=True;q["sentAt"]=int(time.time())
            changed=True
        if changed:write("queue.json",QUEUE)

def launch_pending(last):
    return bool(last and not last.get("closed") and not last.get("observed") and
                (time.time()-last["time"]<45 or LAUNCH_TERMS.get(last.get("request"))))

def end_managed_game(last):
    """Called under LOCK after matching the launch generation."""
    from spiel_fenster import close_game
    key=last["id"]
    if not last.get("ending") or time.time()-last.get("endTime",0)>12:
        has_window=close_game(key,lambda:read("last-launch.json",{}).get("request")==last.get("request"))
        steam_running=running(key)
        if has_window or steam_running:last["observed"]=True
        if not has_window and (steam_running or launch_pending(last)):
            # Startup helpers can keep Steam running without an open game window.
            subprocess.Popen([str(steam_path()/"steam.exe"),"+app_stop",key,"0"],
                             creationflags=subprocess.CREATE_NO_WINDOW)
        last["endTime"]=time.time()
    last["ending"]=True
    write("last-launch.json",last)

def watch_managed_game(last):
    if not last.get("id") or last.get("closed"):return
    if running(last["id"]):
        if last.get("observed") and "goneSince" not in last:return
        cancelled_start=last.get("ending") and launch_pending(last)
        last["observed"]=True
        last.pop("goneSince",None)
        if cancelled_start:
            last.pop("endTime",None)
            end_managed_game(last)
        else:write("last-launch.json",last)
        return
    if not last.get("observed") and (launch_pending(last) or not last.get("ending") and time.time()-last["time"]<180):return
    from spiel_fenster import game_window
    if game_window(last["id"],True):return
    now=time.time()
    if "goneSince" not in last:last["goneSince"]=now
    elif now-last["goneSince"]<4:return
    else:last["closed"]=True
    write("last-launch.json",last)

def acc_gamepad(prepare=False):
    """Select ACC's gamepad driving mode for a console launch, preserving wheel bindings."""
    import re
    from spiel_fenster import documents_folder
    documents=documents_folder()
    if documents is None:return
    path=documents/"Assetto Corsa Competizione/Config/controls.json"
    marker=DATA/"acc-gamepad.json"
    previous=read(marker.name,{})
    if running("805550"):
        if previous and not previous.get("started"):
            previous["started"]=True;write(marker.name,previous)
        return
    if not prepare and not previous:return
    if previous and not prepare and not previous.get("started") and time.time()-previous["time"]<180:return
    if not path.is_file() or path.is_symlink():return
    data=path.read_bytes()
    pattern=rb'("carControllerMode"\s*:\s*)([0-9]+)(?=\s*[,}])'
    matches=list(re.finditer(pattern,data))
    if len(matches)!=1:return
    start,end=matches[0].span(2)
    mode=int(data[start:end])
    if prepare:
        if mode==1:
            if previous:write(marker.name,{"mode":previous["mode"],"time":time.time()})
            return
        write(marker.name,{"mode":mode,"time":time.time()})
        target=1
    else:
        target=previous["mode"]
        if mode!=1:
            marker.unlink(missing_ok=True);return
    from tempfile import NamedTemporaryFile
    with NamedTemporaryFile(dir=path.parent,delete=False) as f:
        tmp=Path(f.name)
        f.write(data[:start]+str(target).encode("ascii")+data[end:])
    try:tmp.replace(path)
    finally:tmp.unlink(missing_ok=True)
    if not prepare:marker.unlink(missing_ok=True)

def hotline_display(prepare=False):
    from spiel_fenster import capture_monitor,hotline_resolution,hotline_window_file
    import struct
    marker=DATA/"hotline-display.json"
    path=hotline_window_file()
    if path is None:return
    if running("274170"):
        if marker.exists():
            record=read(marker.name,{})
            if not record.get("started"):
                record["started"]=True;write(marker.name,record)
        return
    if marker.exists():
        record=read(marker.name,{})
        if not prepare and not record.get("started") and time.time()-record["start"]<120:return
        hotline_resolution(path,record["original"],record["stream"])
        marker.unlink(missing_ok=True)
    if not prepare or not path.is_file():return
    monitor=capture_monitor(require_virtual=True)
    if not monitor:return
    rect=monitor.monitor
    size=(rect.right-rect.left,rect.bottom-rect.top,0,0)
    data=path.read_bytes()
    if len(data)!=16:return
    original=struct.unpack("<4I",data)
    if original==size:return
    write(marker.name,dict(original=original,stream=size,start=time.time()))
    hotline_resolution(path,size,expected=original)

TRANSFER_VIEW_UNTIL=0

def worker():
    global LAST
    seen={}
    while True:
        try:
            try:restore_idle(seen)
            except (OSError,ValueError,KeyError):pass
            with LOCK:
                last=read("last-launch.json",{})
                watch_managed_game(last)
                if (DATA/"hotline-display.json").exists():hotline_display()
                if (DATA/"acc-gamepad.json").exists():acc_gamepad()
            apps=manifests()
            if time.monotonic()<TRANSFER_VIEW_UNTIL:
                from steam_progress import update
                update(steam_path(),apps)
            queue_step(apps)
            pending=next((q.copy() for q in QUEUE if q.get("sent") and not q.get("direct") and apps.get(q["id"],{}).get("state") not in ("downloading","staging")),None)
            prompt=steam_dialog(pending["name"],drive=pending.get("drive")) if pending else {}
            if pending and prompt:
                prompt["id"]=pending["id"]
                if pending["action"]=="install" and prompt.get("confirm","").casefold() in ("install","installieren"):
                    with LOCK:
                        queued=next((q for q in QUEUE if q["id"]==pending["id"] and q.get("sent")),None)
                        ready=queued and not PAUSED and not queued.get("confirmed")
                    if ready and steam_dialog(pending["name"],"install",pending.get("drive")):
                        with LOCK:
                            if queued in QUEUE:
                                queued["confirmed"]=True;write("queue.json",QUEUE);prompt={}
            with LOCK:LAST={"apps":apps,"updated":int(time.time()),"prompt":prompt,"queue":list(QUEUE),"paused":PAUSED}
        except Exception:
            with LOCK:LAST=dict(LAST,error="Steam-Bibliothek derzeit nicht lesbar")
        time.sleep(3)

def trophies(key):
    from urllib import parse,request
    account=Path(__file__).with_name("Steam-Konto.json")
    api=os.environ.get("STEAM_WEB_API_KEY")
    if not api or not account.is_file():return {"notice":"Für Trophäen beim Einrichten das Steam-Konto verbinden und den Web-API-Schlüssel hinterlegen."}
    params=parse.urlencode(dict(key=api,steamid=json.loads(account.read_text(encoding="utf8"))["steamid"],appid=key,l="german"))
    try:
        with request.urlopen("https://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v1/?"+params,timeout=5) as response:
            data=json.load(response)["playerstats"]["achievements"]
        return {"rows":[dict(name=r.get("name") or r["apiname"],done=bool(r["achieved"])) for r in data]}
    except (OSError,KeyError,ValueError):return {"notice":"Steam liefert für dieses Konto und Spiel derzeit keine Erfolge."}

def digest(s):return hashlib.sha256(s.encode()).hexdigest()
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*_):pass
    def reply(self,status,data):
        body=json.dumps(data).encode();self.send_response(status);self.send_header("Content-Type","application/json");self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)
    def do_GET(self):self.handle_api(False)
    def do_POST(self):self.handle_api(True)
    def handle_api(self,post):
        global PAUSED,PENDING_OFF,TRANSFER_VIEW_UNTIL
        try:
            length=int(self.headers.get("Content-Length",0))
            if length>1024 or length<0:return self.reply(413,{})
            req=json.loads(self.rfile.read(length)) if length else {}
            with LOCK:
                if self.path=="/pair" and post:
                    state=read("pair.json",{});now=time.time()
                    if len([t for t in ATTEMPTS if now-t<180])>=6:return self.reply(429,{"error":"Kurz warten und neu koppeln."})
                    if now>state.get("until",0) or not hmac.compare_digest(state.get("hash",""),digest(str(req.get("pin","")))):
                        ATTEMPTS.append(now);return self.reply(403,{"error":"Code ungültig oder abgelaufen."})
                    token=secrets.token_urlsafe(32);tokens=read("clients.json",[]);tokens.append(digest(token));write("clients.json",tokens);write("pair.json",{})
                    return self.reply(200,{"token":token})
                token=self.headers.get("Authorization","").removeprefix("Bearer ")
                if not token or not any(hmac.compare_digest(digest(token),x) for x in read("clients.json",[])):return self.reply(401,{"error":"PC-Verwaltung koppeln."})
            prefix="/remote-updates/" if self.path.startswith("/remote-updates/") else "/updates/"
            if not post and self.path.startswith(prefix):
                folder=DATA/prefix.strip("/")
                try:
                    release=json.loads((folder/"release.json").read_text(encoding="utf8"))
                except FileNotFoundError:
                    return self.reply(200,{"version":0}) if self.path==prefix+"latest" else self.reply(404,{})
                if self.path==prefix+"latest":return self.reply(200,release)
                if self.path!=prefix+release["sha256"]:return self.reply(404,{"error":"Version wurde ersetzt."})
                with (folder/(release["sha256"]+".apk")).open("rb") as stream:
                    self.send_response(200);self.send_header("Content-Type","application/vnd.android.package-archive")
                    self.send_header("Content-Length",str(release["size"]));self.end_headers()
                    shutil.copyfileobj(stream,self.wfile)
                return
            if self.path in ("/status","/status/downloads") and not post:
                if self.path=="/status/downloads":TRANSFER_VIEW_UNTIL=time.monotonic()+12
                with LOCK:status=dict(LAST,hostBuild=340,downloadAction=DOWNLOAD_ACTION,mediaCount=len(MEDIA),coverAtlas=ATLAS,pcArtwork=ART_REVISIONS,directProfiles=sorted(BUILTIN_PROFILES|set(folders())),profileLaunch=sorted(BUILTIN_PROFILES|set(folders())) if profile_helper_ready() else [],profileNames=read("profiles.json",{}),catalog=CATALOG,saveTimes=SAVE_TIMES,covers=COVERS,storeLinks=STORE_LINKS,disks=DISKS,queue=list(QUEUE),paused=PAUSED)
                last=read("last-launch.json",{})
                if last.get("id") and not last.get("closed") and (running(last["id"]) or launch_pending(last) and not last.get("ending")):
                    status["activeGame"]={"id":last["id"],"request":last.get("request"),"profile":last.get("profile",0),"name":status.get("apps",{}).get(last["id"],{}).get("name","Spiel")}
                return self.reply(200,status)
            if self.path=="/catalog-media" and not post:return self.reply(200,MEDIA.copy())
            if self.path.startswith("/trophies/") and not post:
                key=self.path.rsplit("/",1)[1]
                return self.reply(200,trophies(key)) if key.isdecimal() and len(key)<=10 else self.reply(400,{})
            if self.path.startswith("/artwork/") and not post:
                parts=self.path.split("/")
                file=ART_FILES.get(tuple(parts[2:4])) if len(parts)==5 else None
                if len(parts)==5 and parts[3]=="atlas" and parts[2].isascii() and parts[2].isdigit() and parts[4].isascii() and parts[4].isdigit():
                    file=DATA/"cover-atlas"/parts[4]/(parts[2]+".jpg")
                if not file or not file.is_file():return self.reply(404,{})
                with file.open("rb") as image:
                    self.send_response(200);self.send_header("Content-Type","image/jpeg")
                    self.send_header("Content-Length",str(os.fstat(image.fileno()).st_size));self.end_headers()
                    try:shutil.copyfileobj(image,self.wfile)
                    except (ConnectionError,ssl.SSLError):pass
                return
            if self.path.startswith("/screen/") and post:
                from spiel_fenster import screen,close_game
                game=self.path.rsplit("/",1)[1]
                with LOCK:
                    session=req.get("session")
                    last=read("last-launch.json",{})
                    if session and (last.get("request")!=session or last.get("id")!=game):
                        return self.reply(200,{"replaced":True})
                    if session and last.get("closed"):return self.reply(200,{"accepted":True,"visible":False})
                    if req.get("action")=="close":
                        if session:
                            end_managed_game(last)
                            return self.reply(200,{"accepted":True})
                        accepted=close_game(game)
                        if accepted and last.get("id")==game:
                            last["ending"]=True;write("last-launch.json",last)
                        return self.reply(200,{"accepted":accepted})
                    if req.get("action")=="prepare":
                        if last.get("id")==game and last.get("ending") and session:return self.reply(200,{"visible":False})
                        visible=screen(game,True,req.get("virtual") is True)
                        if visible and last.get("id")==game and not last.get("observed"):
                            last["observed"]=True;write("last-launch.json",last)
                        return self.reply(200,{"visible":visible})
                    return self.reply(400,{})
            if self.path=="/launch-terms" and post:
                last=read("last-launch.json",{})
                if not last.get("request") or last.get("request")!=req.get("request") or last.get("ending") or last.get("closed"):return self.reply(409,{})
                title=LAST.get("apps",{}).get(last["id"],{}).get("name")
                if not title:return self.reply(409,{})
                expected=req.get("hash")
                if expected:
                    with LOCK:
                        current=read("last-launch.json",{})
                        if current.get("request")!=last["request"] or current.get("ending") or current.get("closed"):return self.reply(409,{})
                        return self.reply(200,steam_dialog(title,"accept",expected=expected))
                return self.reply(200,steam_dialog(title,"terms"))
            if self.path=="/end-active" and post:
                from spiel_fenster import close_game
                with LOCK:
                    last=read("last-launch.json",{})
                    if not last or last.get("id")!=req.get("id") or last.get("request")!=req.get("request"):
                        return self.reply(409,{"error":"Die aktive Spielsitzung hat sich geändert."})
                    if not last.get("closed"):end_managed_game(last)
                    return self.reply(200,{"ok":True})
            if self.path=="/save-candidates" and post:
                key=str(req.get("id",""))
                return self.reply(200,{"paths":[str(p) for p in save_candidates(key)]})
            if self.path=="/profile-folder" and post:
                key=str(req.get("id",""));slot=req.get("slot")
                if type(slot)!=int or slot not in (1,2,3):return self.reply(400,{})
                chosen=req.get("path")
                if chosen:
                    with LOCK:
                        if running(key) or chosen not in {str(p) for p in save_candidates(key)}:return self.reply(409,{"error":"Speicherordner nicht verfügbar oder Spiel läuft."})
                        mapping=folders()
                        if key in mapping and mapping[key]!=chosen or any(Path(chosen).is_relative_to(Path(v)) or Path(v).is_relative_to(Path(chosen)) for k,v in mapping.items() if k!=key):
                            return self.reply(409,{"error":"Speicherordner ist bereits zugeordnet."})
                        mapping[key]=chosen;write("save-folders.json",mapping)
                if key not in (BUILTIN_PROFILES|set(folders())):return self.reply(409,{"error":"Diesem Spiel in Dolos-PC unter Einrichtung einen lokalen Speicherordner zuordnen."})
                path=profile_path(key,slot)
                if key in folders() and (DATA/("active-"+key+".json")).exists():return self.reply(409,{"error":"Profilwechsel erst nach Spielende möglich."})
                from steam_aktion import save_lock
                with save_lock(key):
                    if key in folders() and (DATA/("active-"+key+".json")).exists():return self.reply(409,{"error":"Spiel zuerst beenden."})
                    path.mkdir(parents=True,exist_ok=True)
                return self.reply(200,{"path":str(path)})
            if self.path.startswith("/foreground/") and not post:
                from spiel_fenster import screen,launch_stage
                key,_,query=self.path.rsplit("/",1)[1].partition("?")
                from urllib.parse import parse_qs
                options=parse_qs(query)
                session=options.get("session",[None])[0]
                visible=screen(key,require_virtual=options.get("virtual")==["1"])
                steam_running=running(key) if key.isdecimal() and len(key)<=10 else None
                with LOCK:
                    last=read("last-launch.json",{})
                    if session and (session!=last.get("request") or key!=last.get("id")):return self.reply(200,{"replaced":True})
                    if session and last.get("closed"):return self.reply(200,{"visible":False,"running":False,"closed":True})
                    if (visible or steam_running) and last.get("id")==key and not last.get("observed") and not last.get("ending") and not last.get("closed"):
                        last["observed"]=True;write("last-launch.json",last)
                    pending_stop=bool(session and last.get("ending") and launch_pending(last))
                return self.reply(200,{"visible":visible,"pendingStop":pending_stop,"terms":LAUNCH_TERMS.get(session) if session and not visible else None,"stage":"" if visible else launch_stage(key),"running":steam_running})
            if post and self.path=="/queue" and req.get("action") in ("downloadfirst","downloadpause","downloadcancel"):
                ok,error=download_command(str(req.get("id","")),req["action"])
                return self.reply(200 if ok else 409,{"ok":True,"error":error})
            with LOCK:
                if self.path=="/ping" and not post:return self.reply(200,{"ok":True})
                if self.path=="/profiles" and post:
                    slot=req.get("slot");name=req.get("name")
                    if type(slot) is not int or not 0<=slot<4 or not isinstance(name,str) or not 0<len(name.strip())<=20:return self.reply(400,{})
                    names=read("profiles.json",{})
                    if not req.get("seed") or str(slot) not in names:
                        names[str(slot)]=name.strip();write("profiles.json",names)
                    return self.reply(200,names)
                if self.path=="/launch" and post:
                    key=str(req.get("id",""));profile=req.get("profile");nonce=req.get("request","")
                    if LAST.get("apps",{}).get(key,{}).get("state")!="installed" or not key.isdecimal() or len(key)>10 or type(profile)!=int or profile not in range(4) or not isinstance(nonce,str) or len(nonce)!=36:
                        return self.reply(409,{"error":"Spiel noch nicht bereit."})
                    last=read("last-launch.json",{})
                    if last and not last.get("closed") and (running(last["id"]) or launch_pending(last)):
                        if not last.get("ending") and last["id"]==key and last["profile"]==profile:return self.reply(200,{"ok":True,"session":last.get("request")})
                        if last.get("ending"):return self.reply(409,{"error":"Steam beendet den vorigen Spielstart. Versuche es in einem Moment erneut."})
                        return self.reply(409,{"error":"Das vorige Spiel zuerst beenden."})
                    if last and last.get("request")==nonce:return self.reply(409,{"error":"Diese Spielsitzung ist beendet. Starte das Spiel erneut."})
                    if running(key):return self.reply(409,{"error":"Dieses Spiel ist bereits auf dem PC geöffnet."})
                    from steam_aktion import launch_game
                    from spiel_fenster import stream_launch_args
                    try:
                        if key=="274170":hotline_display(prepare=True)
                        if key=="805550":acc_gamepad(prepare=True)
                        launch_game(steam_path(),key,profile,stream_launch_args(key))
                    except (ValueError,OSError) as err:return self.reply(409,{"error":str(err)})
                    write("last-launch.json",dict(id=key,profile=profile,request=nonce,time=time.time()))
                    title=LAST["apps"][key].get("name")
                    if title:
                        def confirm_start():
                            from spiel_fenster import screen
                            try:
                                for delay in (2,4,8,12,20,30,45,60):
                                    time.sleep(delay)
                                    last=read("last-launch.json",{})
                                    if last.get("request")!=nonce or last.get("ending") or screen(key):return
                                    terms=steam_dialog(title,"terms")
                                    if terms.get("hash"):
                                        LAUNCH_TERMS[nonce]=terms["hash"]
                                    else:
                                        LAUNCH_TERMS.pop(nonce,None)
                                        steam_dialog(title,"launch")
                            finally:
                                LAUNCH_TERMS.pop(nonce,None)
                        threading.Thread(target=confirm_start,daemon=True).start()
                    return self.reply(200,{"ok":True,"session":nonce})
                if self.path=="/select" and post:
                    key=str(req.get("id",""))
                    if not key.isdecimal() or len(key)>10 or LAST.get("apps",{}).get(key,{}).get("state")!="installed":
                        return self.reply(409,{"error":"Spiel noch nicht bereit."})
                    profile=req.get("profile",0)
                    if type(profile) is not int or profile not in range(4) or profile and key not in (BUILTIN_PROFILES|set(folders())):
                        return self.reply(409,{"error":"Kein eigener Speicherpfad für dieses Spiel."})
                    if profile and not profile_helper_ready():
                        return self.reply(409,{"error":"Dolos-PC → Einrichtung → Spielstart aktualisieren."})
                    previous=read("start.json",{})
                    if previous.get("until",0)>time.time() and (previous.get("id")!=key or previous.get("profile",0)!=profile):
                        return self.reply(409,{"error":"Ein anderes Spiel startet gerade."})
                    write("start.json",dict(id=key,profile=profile,until=time.time()+60))
                    return self.reply(200,{"ok":True})
                if not post:return self.reply(404,{})
                if self.path in ("/power","/sleep"):
                    if not PENDING_OFF:
                        PENDING_OFF=True
                        def shutdown():
                            global PENDING_OFF
                            if self.path=="/sleep":
                                import ctypes
                                ctypes.windll.powrprof.SetSuspendState(False,False,False)
                            else:subprocess.run(["shutdown.exe","/s","/t","0"],check=False)
                            with LOCK:PENDING_OFF=False
                        threading.Timer(6,shutdown).start()
                    return self.reply(200,{"ok":True})
                if self.path!="/queue":return self.reply(404,{})
                action=req.get("action");key=str(req.get("id",""))
                if action in ("pause","resume"):PAUSED=action=="pause";write("paused.json",PAUSED)
                elif action=="retry":
                    q=next((job for job in QUEUE if job["id"]==key),None)
                    if not q or not q.get("sent") or time.time()-q.get("sentAt",0)<40 or LAST.get("apps",{}).get(key,{}).get("state") in ("staging","downloading","installed"):
                        return self.reply(409,{"error":"Auftrag läuft bereits."})
                    for field in ("sent","sentAt","confirmed","error"):q.pop(field,None)
                elif action in ("confirm","cancel"):
                    q=next((x for x in QUEUE if x["id"]==key and x.get("sent")),None)
                    if not q or LAST.get("prompt",{}).get("id")!=key or not steam_dialog(q["name"],action,q.get("drive")):
                        return self.reply(409,{"error":"Steam-Dialog geändert. Bitte aktualisieren."})
                    if action=="cancel":QUEUE.remove(q)
                    LAST["prompt"]={}
                elif action=="dismiss":QUEUE[:]=[q for q in QUEUE if q["id"]!=key]
                elif action in ("install","remove") and allowed(key):
                    drive=req.get("drive")
                    if drive and drive not in {disk.get("drive") for disk in DISKS}:return self.reply(400,{"error":"Steam-Laufwerk nicht verfügbar."})
                    if action=="install" and drive and shutil.disk_usage(drive+"/").free<REQUIRED.get(key,1):return self.reply(409,{"error":"Zu wenig freier Speicher auf "+drive})
                    if not any(q["id"]==key for q in QUEUE):QUEUE.append({"drive":drive,"id":key,"action":action,"sent":False,"name":str(req.get("name",key))[:120]})
                else:return self.reply(400,{"error":"Unbekannter Spieleintrag."})
                write("queue.json",QUEUE);return self.reply(200,{"ok":True})
        except (ValueError,OSError,KeyError) as e:self.reply(400,{"error":"Anfrage fehlgeschlagen."})

def serve(host):
    global QUEUE,PAUSED
    cert,key=certificate();server=ThreadingHTTPServer((host,PORT),Handler)
    ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.minimum_version=ssl.TLSVersion.TLSv1_2;ctx.load_cert_chain(cert,key)
    server.socket=ctx.wrap_socket(server.socket,server_side=True)
    QUEUE=read("queue.json",[]);PAUSED=read("paused.json",False);threading.Thread(target=store_worker,daemon=True).start();threading.Thread(target=catalog_worker,daemon=True).start();threading.Thread(target=worker,daemon=True).start();server.serve_forever()

def enable():
    import ctypes
    if ctypes.windll.shell32.IsUserAnAdmin():raise RuntimeError("Dolos-PC zum Koppeln als normaler Windows-Benutzer öffnen.")
    pin,mark=open_pairing()
    pythonw=Path(sys.executable).with_name("pythonw.exe")
    args=[str(pythonw),str(Path(__file__).resolve()),"--serve"]
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER,r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
        winreg.SetValueEx(key,"Dolos LAN",0,winreg.REG_SZ,subprocess.list2cmdline(args))
    with socket.socket() as probe:
        probe.settimeout(.3);running=probe.connect_ex(("127.0.0.1",PORT))==0
    if not running:subprocess.Popen(args,creationflags=subprocess.CREATE_NO_WINDOW)
    return "Prüfzeichen: "+mark+"\nTV-Code: "+pin+" (3 Minuten gültig)"
if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--serve",action="store_true");parser.add_argument("--loopback",action="store_true");args=parser.parse_args()
    if args.serve:serve("127.0.0.1" if args.loopback else "0.0.0.0")
