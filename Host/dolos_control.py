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
CATALOG=[]
DISKS=[]
COVERS={}
STORE_LINKS={}
SAVE_TIMES={}
from save_times import subnautica_slots
ART_FILES={}
ART_REVISIONS={}
ATLAS={}
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
    revisions={}
    for (sid,kind),path in ART_FILES.items():
        revisions.setdefault(sid,{})[kind]=int(path.stat().st_mtime)
    ART_REVISIONS=revisions
    from cover_atlas import prepare
    try:ATLAS=prepare(DATA,ART_FILES)
    except (OSError,ValueError,subprocess.SubprocessError):ATLAS={}
    CATALOG=[dict(id=k,name=v[0],state=states[k]) for k,v in games.items() if len(k)<=10]
    disks=[]
    times=[]
    for lib in read_vdf(steam/"steamapps/libraryfolders.vdf")["libraryfolders"].values():
        folder=Path(lib["path"])
        if folder.is_dir():
            times.extend(subnautica_slots(folder))
            usage=shutil.disk_usage(folder)
            disks.append(dict(name=folder.drive or folder.name,total=usage.total,free=usage.free))
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
                state="paused" if flags&256 else "staging" if flags&(2097152|4194304) else "downloading" if active else "installed" if flags&4 else "waiting"
                staged=state=="staging"
                apps[g["appid"]]={"id":g["appid"],"name":g["name"],"state":state,"done":int(g.get("BytesStaged" if staged else "BytesDownloaded",0)),"total":int(g.get("BytesToStage" if staged else "BytesToDownload",0))}
            except (ValueError,KeyError,OSError,SyntaxError):continue
    return apps

def allowed(key):
    if not str(key).isdecimal() or int(key)>0xffffffff:return False
    from importieren import collect
    from katalog import expand
    games=collect(steam_path());owned=Path(__file__).with_name("Steam-Bibliothek.json")
    expand(steam_path(),games,owned if owned.is_file() else None)
    return str(key) in games

def steam_dialog(name,mode="inspect"):
    try:
        cmd=["powershell.exe","-NoProfile","-NonInteractive","-File",str(Path(__file__).with_name("DolosDialog.ps1")),
             "-SteamRoot",str(steam_path()),"-Title",name,"-Action",mode]
        result=subprocess.run(cmd,capture_output=True,timeout=6,creationflags=subprocess.CREATE_NO_WINDOW)
        return json.loads(result.stdout.decode("utf-8-sig")) if result.returncode==0 else {}
    except (ValueError,OSError,subprocess.TimeoutExpired):return {}

def queue_step(apps):
    global QUEUE
    with LOCK:
        changed=False
        for q in list(QUEUE):
            current=apps.get(q["id"],{}).get("state")
            if q["action"]=="install" and current=="installed" or q["action"]=="remove" and not current:
                QUEUE.remove(q);changed=True
        if not PAUSED and QUEUE and not any(q.get("sent") for q in QUEUE):
            q=QUEUE[0]
            try:os.startfile("steam://"+("install" if q["action"]=="install" else "uninstall")+"/"+q["id"]);q["sent"]=True;q["sentAt"]=int(time.time())
            except OSError:q["error"]="Steam konnte nicht geöffnet werden."
            changed=True
        if changed:write("queue.json",QUEUE)

def worker():
    global LAST
    while True:
        try:
            apps=manifests();queue_step(apps)
            pending=next((q.copy() for q in QUEUE if q.get("sent") and apps.get(q["id"],{}).get("state") not in ("downloading","staging")),None)
            prompt=steam_dialog(pending["name"]) if pending else {}
            if pending and prompt:
                prompt["id"]=pending["id"]
                if pending["action"]=="install" and prompt.get("confirm","").casefold() in ("install","installieren"):
                    with LOCK:
                        queued=next((q for q in QUEUE if q["id"]==pending["id"] and q.get("sent")),None)
                        if queued and not PAUSED and not queued.get("confirmed") and steam_dialog(pending["name"],"install"):
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
        global PAUSED,PENDING_OFF
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
                if req.get("action")=="close":return self.reply(200,{"accepted":close_game(game)})
                if req.get("action")=="prepare":return self.reply(200,{"visible":screen(game,True)})
                return self.reply(400,{})
            if self.path.startswith("/foreground/") and not post:
                from spiel_fenster import playing
                return self.reply(200,{"visible":playing(self.path.rsplit("/",1)[1])})
            with LOCK:
                if self.path=="/ping" and not post:return self.reply(200,{"ok":True})
                if self.path=="/profiles" and post:
                    slot=req.get("slot");name=req.get("name")
                    if type(slot) is not int or not 0<=slot<4 or not isinstance(name,str) or not 0<len(name.strip())<=20:return self.reply(400,{})
                    names=read("profiles.json",{})
                    if not req.get("seed") or str(slot) not in names:
                        names[str(slot)]=name.strip();write("profiles.json",names)
                    return self.reply(200,names)
                if self.path=="/status" and not post:return self.reply(200,dict(LAST,coverAtlas=ATLAS,pcArtwork=ART_REVISIONS,profileLaunch=["105600","294100","1874880"] if profile_helper_ready() else [],profileNames=read("profiles.json",{}),catalog=CATALOG,saveTimes=SAVE_TIMES,covers=COVERS,storeLinks=STORE_LINKS,disks=DISKS,queue=list(QUEUE),paused=PAUSED))
                if self.path=="/select" and post:
                    key=str(req.get("id",""))
                    if not key.isdecimal() or len(key)>10 or LAST.get("apps",{}).get(key,{}).get("state")!="installed":
                        return self.reply(409,{"error":"Spiel noch nicht bereit."})
                    profile=req.get("profile",0)
                    if type(profile) is not int or profile not in range(4) or profile and key not in ("105600","294100","1874880"):
                        return self.reply(409,{"error":"Kein eigener Speicherpfad für dieses Spiel."})
                    if profile and not profile_helper_ready():
                        return self.reply(409,{"error":"Am PC den Store einmal als Administrator aktualisieren."})
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
                    if not q or LAST.get("prompt",{}).get("id")!=key or not steam_dialog(q["name"],action):
                        return self.reply(409,{"error":"Steam-Dialog geändert. Bitte aktualisieren."})
                    if action=="cancel":QUEUE.remove(q)
                    LAST["prompt"]={}
                elif action=="dismiss":QUEUE[:]=[q for q in QUEUE if q["id"]!=key]
                elif action in ("install","remove") and allowed(key):
                    if not any(q["id"]==key for q in QUEUE):QUEUE.append({"id":key,"action":action,"sent":False,"name":str(req.get("name",key))[:120]})
                else:return self.reply(400,{"error":"Unbekannter Spieleintrag."})
                write("queue.json",QUEUE);return self.reply(200,{"ok":True})
        except (ValueError,OSError,KeyError) as e:self.reply(400,{"error":"Anfrage fehlgeschlagen."})

def serve(host):
    global QUEUE,PAUSED
    cert,key=certificate();server=ThreadingHTTPServer((host,PORT),Handler)
    ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.minimum_version=ssl.TLSVersion.TLSv1_2;ctx.load_cert_chain(cert,key)
    server.socket=ctx.wrap_socket(server.socket,server_side=True)
    QUEUE=read("queue.json",[]);PAUSED=read("paused.json",False);threading.Thread(target=catalog_worker,daemon=True).start();threading.Thread(target=worker,daemon=True).start();server.serve_forever()

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
