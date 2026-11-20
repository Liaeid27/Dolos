"""PC game picker for the Dolos Store. Changes are applied by the host import."""
import json
import os
import subprocess
import sys
import time
import tempfile
import uuid
from pathlib import Path
import socket
import tkinter as tk
from tkinter import Tk, ttk, messagebox, filedialog, simpledialog

ROOT=Path(__file__).resolve().parent
CUSTOM=ROOT/"Eigene-Spiele.json"

def save(path,doc):
    with tempfile.NamedTemporaryFile(dir=path.parent,delete=False) as f:
        temp=Path(f.name);f.write(json.dumps(doc,ensure_ascii=False,indent=2).encode())
    try:os.replace(temp,path)
    finally:temp.unlink(missing_ok=True)

def host_entries(path=CUSTOM):
    if not path.exists():return []
    rows=[]
    for game in json.loads(path.read_text(encoding="utf-8")):
        exe=Path(game["exe"])
        if not exe.is_absolute() or exe.suffix.lower()!=".exe":raise ValueError("Ungültiger Spielpfad")
        row={"name":game["name"],"cmd":subprocess.list2cmdline([str(exe)]),"working-dir":str(exe.parent),
             "uuid":str(uuid.uuid5(uuid.NAMESPACE_URL,"dolos/windows/"+str(exe).casefold())).upper(),
             "virtual-display":True,"aster-managed":True}
        if game.get("cover"):row["image-path"]=game["cover"]
        rows.append(row)
    return rows

def gui():
    import threading,queue,urllib.request,xml.etree.ElementTree as ET
    root=Tk();root.title("Dolos · Spiel-PC");root.geometry("970x650");root.minsize(830,610)
    ink="#0e1019";panel_ink="#181c2c";paper="#f0eada";muted="#aab3ca";cobalt="#334ed6"
    root.configure(bg=ink)
    sidebar=tk.Frame(root,bg="#11152a",width=220);sidebar.pack(side="left",fill="y");sidebar.pack_propagate(False)
    poster=tk.PhotoImage(file=str(ROOT/"atelier.png"))
    portrait=tk.Canvas(sidebar,height=155,bg="#192ca3",highlightthickness=0);portrait.pack(fill="x")
    portrait.create_image(0,0,image=poster,anchor="nw")
    tk.Label(sidebar,text="Dolos",bg="#11152a",fg=paper,font=("Times New Roman",36)).pack(anchor="w",padx=20,pady=(14,22))
    body=tk.Frame(root,bg=ink,padx=28,pady=24);body.pack(expand=True,fill="both")
    heading=tk.Label(body,bg=ink,fg=paper,font=("Times New Roman",32));heading.pack(anchor="w")
    area=tk.Frame(body,bg=ink);area.pack(fill="both",expand=True,pady=(16,0))
    status=tk.Label(body,text="",bg=ink,fg=paper,font=("Segoe UI",11),anchor="w",justify="left",wraplength=540);status.pack(fill="x",pady=(5,0))
    address=tk.StringVar(value="Wird ermittelt …");health=tk.StringVar(value="Apollo wird geprüft …")
    tip=tk.StringVar(value="");result=queue.Queue();checking=False
    def diagnose():
        nonlocal checking
        if checking:return
        checking=True;health.set("Apollo wird geprüft …")
        def work():
            try:
                cmd="$physical=@(Get-NetAdapter -Physical | Where-Object Status -eq Up | ForEach-Object ifIndex); Get-NetIPConfiguration | Where-Object {$_.InterfaceIndex -in $physical -and $_.IPv4Address} | Sort-Object @{Expression={if($_.IPv4DefaultGateway){0}else{1}}},@{Expression={$_.NetIPv4Interface.InterfaceMetric}} | ForEach-Object {$_.IPv4Address.IPAddress}"
                options=dict(capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=10)
                ips=subprocess.run(["powershell.exe","-NoProfile","-Command",cmd],**options).stdout.splitlines()
                ips=[ip.strip() for ip in ips if ip.strip()]
                if not ips:raise ValueError("Ethernet oder WLAN mit dem Router verbinden und erneut prüfen.")
                from pc_status import apollo_port
                port=apollo_port()
                opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
                for ip in ips:
                    try:
                        with opener.open("http://"+ip+":"+str(port)+"/serverinfo",timeout=2) as r:doc=ET.fromstring(r.read(100000))
                        if doc.findtext("uniqueid") and doc.get("status_code")=="200":
                            result.put((ip+(":"+str(port) if port!=47989 else ""),"Apollo bereit","Am Handy oder TV „PC suchen“ wählen. Alternativ diese Adresse eingeben."));return
                    except (OSError,ValueError,ET.ParseError):continue
                result.put((ips[0],"Apollo am PC nicht erreichbar","Öffne Apollo am PC. Warte, bis der Dienst läuft, und prüfe erneut."))
            except Exception as e:result.put(("—","Verbindung prüfen",str(e)))
        def finish():
            nonlocal checking
            if result.empty():root.after(120,finish);return
            ip,ok,note=result.get();address.set(ip);health.set(ok);tip.set(note);checking=False
        threading.Thread(target=work,daemon=True).start();finish()
    def action(parent,title,fn,primary=False):
        bg=cobalt if primary else panel_ink
        btn=tk.Button(parent,text=title,command=lambda:safe(fn),anchor="w",bg=bg,fg=paper,font=("Segoe UI Semibold",11),relief="flat",bd=0,cursor="hand2",padx=15,pady=9,takefocus=True,highlightthickness=1,highlightbackground=bg,highlightcolor="#d9c68d",activebackground="#4456af",activeforeground="white")
        btn.bind("<Enter>",lambda e:btn.configure(bg="#3e50ac" if primary else "#292f48"))
        btn.bind("<Leave>",lambda e:btn.configure(bg=bg))
        return btn
    def pairing_tile(parent,title,caption,callback,link):
        tile=tk.Canvas(parent,height=145,bg=panel_ink,bd=0,highlightthickness=0,cursor="hand2",takefocus=True)
        hovered=[0.0];target=[0.0];anim=[None]
        def paint():
            w=max(110,tile.winfo_width());h=145;k=hovered[0]
            def blend(a,b):return "#"+"".join(f"{round(u+(v-u)*k):02x}" for u,v in zip(a,b))
            tile.delete("all");tile.configure(bg=blend((27,35,66) if link else (29,37,80),(49,67,132)))
            tile.create_line(0,0,w,0,fill=blend((84,103,167),(232,218,168)),width=2)
            x=32+3*k;y=41
            if link:
                tile.create_arc(x-11,y-12,x+18,y+11,start=10,extent=272,style="arc",outline="#c8d5ff",width=2)
                tile.create_arc(x+5,y-22,x+34,y+2,start=192,extent=275,style="arc",outline="#dccda8",width=2)
            else:
                tile.create_rectangle(x-13,y-16,x+28,y+10,outline="#ccd6ff",width=2)
                tile.create_line(x+7,y+11,x+7,y+17,x-2,y+17,x+18,y+17,fill="#ccd6ff",width=2)
                for j in range(4):tile.create_oval(x-6+j*8,y-5,x-3+j*8,y-2,fill="#f2db9d",outline="")
            tile.create_text(w-16,17,text="↗" if not link else "→",anchor="ne",fill="#d4dfff",font=("Segoe UI",17))
            tile.create_text(14,79,text=title,anchor="nw",font=("Segoe UI Semibold",12),fill=paper)
            tile.create_text(14,110,text=caption,anchor="nw",font=("Segoe UI",9),fill="#c3cce6")
        def animate():
            hovered[0]+=(target[0]-hovered[0])*.32;paint()
            anim[0]=tile.after(16,animate) if abs(hovered[0]-target[0])>.015 else None
        def focus(on):
            target[0]=float(on)
            if anim[0] is None:animate()
        tile.bind("<Configure>",lambda e:paint());tile.bind("<Enter>",lambda e:focus(True));tile.bind("<Leave>",lambda e:focus(False))
        tile.bind("<FocusIn>",lambda e:focus(True));tile.bind("<FocusOut>",lambda e:focus(False))
        for event in ("<ButtonRelease-1>","<Return>","<space>"):tile.bind(event,lambda e:safe(callback))
        return tile
    def copy_address():
        if health.get()!="Apollo bereit":return
        root.clipboard_clear();root.clipboard_append(address.get());status.configure(text="PC-Adresse kopiert.")
    def add():
        file=filedialog.askopenfilename(title="Spiel auswählen",filetypes=[("Windows-Spiel","*.exe")])
        if not file:return
        exe=Path(file).resolve();name=simpledialog.askstring("Spiel hinzufügen","Titel im Store",initialvalue=exe.stem)
        if not name or not name.strip():return
        cover=filedialog.askopenfilename(title="Optionales Cover · Abbrechen zum Überspringen",filetypes=[("PNG","*.png")])
        games=json.loads(CUSTOM.read_text(encoding="utf8")) if CUSTOM.exists() else []
        games=[g for g in games if Path(g["exe"])!=exe]
        games.append(dict(name=name.strip(),exe=str(exe),cover=cover));save(CUSTOM,games)
        status.configure(text="Gespeichert. Mit „Store aktualisieren“ an Apollo übernehmen.")
    def apollo_pin():
        from pc_status import apollo_port
        import webbrowser
        url="https://localhost:"+str(apollo_port()+1)+"/pin#PIN"
        from apollo_pair import pair as submit_pin
        dialog=tk.Toplevel(root);dialog.title("Apollo koppeln");dialog.configure(bg=ink);dialog.transient(root)
        content=tk.Frame(dialog,bg=ink,padx=22,pady=18);content.pack(fill="both")
        tk.Label(content,text="PIN vom Handy oder TV",font=("Times New Roman",22),bg=ink,fg=paper).pack(anchor="w")
        tk.Label(content,text="Auf dem Android-Gerät die PC-Adresse eingeben und PC verbinden wählen. Diese Seite mit den vier Ziffern offen lassen.",wraplength=420,justify="left",bg=ink,fg=muted).pack(anchor="w",pady=(0,12))
        fields=[]
        for label,mask in [("Vierstellige PIN",""),("Apollo-Benutzername",""),("Apollo-Passwort","•")]:
            tk.Label(content,text=label,bg=ink,fg=paper).pack(anchor="w")
            entry=tk.Entry(content,show=mask,font=("Segoe UI",13));entry.pack(fill="x",pady=(2,8));fields.append(entry)
        feedback=tk.StringVar()
        tk.Label(content,textvariable=feedback,bg=ink,fg=muted,wraplength=440,justify="left").pack(anchor="w")
        def send():
            values=[f.get() for f in fields]
            if len(values[0])!=4 or not values[0].isdigit():feedback.set("Vier Ziffern vom Android-Gerät eingeben.");return
            sent.configure(state="disabled");feedback.set("Kopplung wird bestätigt …")
            events=queue.Queue()
            def work():
                try:submit_pin(*values);events.put((True,"Apollo hat die PIN akzeptiert. Am Android-Gerät mit PC-Verwaltung fortfahren."))
                except Exception as e:events.put((False,str(e)))
            def check():
                if not dialog.winfo_exists():return
                if events.empty():dialog.after(100,check);return
                ok,msg=events.get();fields[2].delete(0,"end");feedback.set(msg)
                if ok:status.configure(text=msg);sent.configure(text="Gekoppelt")
                else:sent.configure(state="normal")
            threading.Thread(target=work,daemon=True).start();dialog.after(100,check)
        sent=action(content,"PIN bestätigen",send,True);sent.pack(anchor="w",pady=4)
        action(content,"In Apollo öffnen",lambda:webbrowser.open(url)).pack(anchor="w");fields[0].focus_set()
    def firewall_help():
        messagebox.showinfo("Zugriff aus dem Heimnetz","Wenn die Adresse stimmt und der PC hier erreichbar ist, öffne den Dolos-PC-Ordner. Einrichten.cmd einmal per Rechtsklick als Administrator ausführen. Die Freigabe gilt für lokale Geräte im privaten Windows-Netz. Danach auf Handy oder TV erneut verbinden.")
    def pair():
        from dolos_control import enable
        code=enable();status.configure(text="Kopplungsfenster geöffnet.");messagebox.showinfo("PC-Verwaltung · Code für Android",code+"\n\nIm dritten Schritt auf Handy oder TV eingeben.")
    def assign_store():
        title=simpledialog.askstring("Spielseite zuordnen","Name des eigenen Spiels, genau wie im Dolos Store:")
        if not title or not title.strip():return
        val=simpledialog.askstring("Spielseite zuordnen","Steam-Shopadresse oder App-ID des Spiels:")
        if val is None:return
        import re
        match=re.fullmatch(r"(?:https://store\.steampowered\.com/app/)?([1-9][0-9]{0,9})(?:/[^?]*)?(?:\?.*)?",val.strip())
        if not match:raise ValueError("Eine Steam-Shopadresse oder numerische App-ID eingeben.")
        target=ROOT/"Spielseiten.json"
        rows=json.loads(target.read_text(encoding="utf8")) if target.exists() else {}
        rows[title.strip()]=match[1];save(target,rows)
        status.configure(text="Spielseite gespeichert. Der Begleitdienst übernimmt sie beim nächsten Katalogabgleich.")
    def import_file():
        file=filedialog.askopenfilename(title="Bibliotheksdatei",filetypes=[("JSON","*.json")])
        if not file:return
        doc=json.loads(Path(file).read_text(encoding="utf-8-sig"))
        if isinstance(doc.get("response",{}).get("apps"),list):target="Steam-Familie.json"
        elif "rgOwnedApps" in doc or "games" in doc.get("response",{}):target="Steam-Bibliothek.json"
        else:raise ValueError("Unbekanntes Listenformat.")
        save(ROOT/target,doc);status.configure(text="Liste gespeichert. Jetzt Store aktualisieren.")
    def sync():
        if subprocess.run([sys.executable,"-X","utf8",str(ROOT/"importieren.py"),"--apply","--power"]).returncode:
            raise RuntimeError("Import fehlgeschlagen. Für das Apollo-Verzeichnis Dolos-PC.cmd als Administrator öffnen.")
        status.configure(text="Store aktualisiert.")
    def login():
        import threading,queue
        from steam_konto import login as authenticate,fetch_owned
        result=queue.Queue()
        def work():
            try:
                steam_id=authenticate()
                doc=fetch_owned(steam_id)
                if doc is not None:save(ROOT/"Steam-Bibliothek.json",doc)
                save(ROOT/"Steam-Konto.json",{"steamid":steam_id})
                result.put("Besitzliste gespeichert. Jetzt Store aktualisieren." if doc is not None else
                           "Konto verbunden. Für GetOwnedGames STEAM_WEB_API_KEY setzen oder eine Bibliotheksdatei importieren.")
            except Exception as err:result.put(str(err))
        def check():
            if result.empty():root.after(300,check);return
            status.configure(text=result.get());login_button.configure(state="normal") if login_button and login_button.winfo_exists() else None
        login_button.configure(state="disabled");status.configure(text="Anmeldung im Steam-Browser abschließen.")
        threading.Thread(target=work,daemon=True).start();check()
    def safe(f):
        try:f()
        except Exception as e:messagebox.showerror("Dolos",str(e))
    login_button=None
    def show(tab):
        nonlocal login_button
        for child in area.winfo_children():child.destroy()
        heading.configure(text=tab);status.configure(text="")
        for key,w in nav.items():w.configure(fg=paper if tab==key else muted)
        if tab=="Verbindung":
            card=tk.Frame(area,bg=panel_ink,padx=18,pady=15);card.pack(fill="x")
            tk.Label(card,textvariable=health,bg=panel_ink,fg="#bed1ff",font=("Segoe UI Semibold",11)).pack(anchor="w")
            tk.Label(card,textvariable=address,bg=panel_ink,fg=paper,font=("Consolas",25)).pack(anchor="w",pady=(2,4))
            tk.Label(card,textvariable=tip,bg=panel_ink,fg=muted,wraplength=490,justify="left",font=("Segoe UI",10)).pack(anchor="w")
            row=tk.Frame(card,bg=panel_ink);row.pack(anchor="w",pady=(6,0))
            action(row,"Adresse kopieren",copy_address).pack(side="left")
            action(row,"Erneut prüfen",diagnose).pack(side="left");action(row,"Heimnetz-Hilfe",firewall_help).pack(side="left")
            def remote_address():
                import subprocess,os
                cli=Path(os.environ["ProgramFiles"])/"Tailscale"/"tailscale.exe"
                ip=subprocess.check_output([str(cli),"ip","-4"],timeout=4,creationflags=subprocess.CREATE_NO_WINDOW,text=True).strip()
                root=area.winfo_toplevel();root.clipboard_clear();root.clipboard_append(ip);status.configure(text="Dolos Remote · "+ip+" kopiert")
            action(card,"Remote-Adresse kopieren",lambda:safe(remote_address)).pack(anchor="w",pady=3)
            tk.Label(area,text="Gerät koppeln",bg=ink,fg=paper,font=("Times New Roman",21)).pack(anchor="w",pady=(18,6))
            tiles=tk.Frame(area,bg=ink);tiles.pack(fill="x",pady=4)
            tiles.columnconfigure(0,weight=1,uniform="tile");tiles.columnconfigure(1,weight=1,uniform="tile")
            pairing_tile(tiles,"Apollo-PIN eingeben","4 Ziffern vom Android-Gerät",apollo_pin,False).grid(row=0,column=0,sticky="ew",padx=(0,6))
            pairing_tile(tiles,"TV-Verwaltung koppeln","Code für die Konsole anzeigen",pair,True).grid(row=0,column=1,sticky="ew",padx=(6,0))
        elif tab=="Einrichtung":
            for title,detail,button,fn in [
                ("Windows-Anmeldung","Automatische Anmeldung für den nächsten PC-Start einrichten.","Microsoft-Einrichtung öffnen",lambda:__import__("webbrowser").open("https://learn.microsoft.com/de-de/sysinternals/downloads/autologon")),
                ("1   Im Heimnetz verbinden","PC per Ethernet oder WLAN mit dem Router verbinden. Das Android-Gerät im selben Heimnetz anmelden.","PC-Adresse anzeigen",lambda:show("Verbindung")),
                ("2   Spielstream koppeln","In Dolos auf Android IP eingeben wählen und die PC-Adresse übernehmen. Die vier Ziffern vom Android-Bildschirm hier auf dem PC bestätigen.","Apollo-PIN eingeben",apollo_pin),
                ("3   PC-Verwaltung koppeln","Jetzt hier den sechsstelligen TV-Code anzeigen. Auf Android das Prüfzeichen vergleichen, den Code eingeben und Konsole öffnen wählen.","TV-Code anzeigen",pair)]:
                row=tk.Frame(area,bg=panel_ink,padx=12,pady=6);row.pack(fill="x",pady=3)
                tk.Label(row,text=title,bg=panel_ink,fg=paper,font=("Segoe UI Semibold",13)).pack(anchor="w")
                tk.Label(row,text=detail,bg=panel_ink,fg=muted,wraplength=490,justify="left").pack(anchor="w")
                action(row,button,fn).pack(anchor="w",pady=2)
        elif tab=="App-Updates":
            from dolos_control import DATA
            from app_update import publish
            folder=DATA/"updates"
            def publish_apk(channel):
                file=filedialog.askopenfilename(title="Dolos-APK auswählen",filetypes=[("Android-App","*.apk")])
                if file:
                    release=publish(file,DATA/channel);show(tab);status.configure(text="Build "+str(release["version"])+" ist im Heimnetz verfügbar.")
            try:
                version=json.loads((folder/"release.json").read_text(encoding="utf8"))["version"]
            except FileNotFoundError:
                version=None
            tk.Label(area,text=("Build "+str(version) if version else "Keine Version bereitgestellt"),bg=ink,fg=paper,font=("Times New Roman",25)).pack(anchor="w")
            tk.Label(area,text="Gekoppelte Fernseher und Handys finden die APK unter Einstellungen → Systemupdate.",bg=ink,fg=muted,wraplength=490,justify="left").pack(anchor="w",pady=12)
            for channel,label in [("updates","Dolos TV"),("remote-updates","Dolos Remote")]:
                action(area,label+" · APK bereitstellen",lambda channel=channel:safe(lambda:publish_apk(channel))).pack(anchor="w")
        else:
            for title,desc,callback in [("Eigenes Spiel hinzufügen","EXE und Cover auswählen",add),("Steam-Konto verbinden","Besitzliste und Erfolge",login),("Bibliotheksdatei importieren","Steam- oder Familienliste übernehmen",import_file),("Spielseite zuordnen","Store-Medien für ein eigenes Spiel",assign_store),("Store aktualisieren","Gespeicherte Einträge an Apollo übertragen",sync)]:
                row=tk.Frame(area,bg=panel_ink);row.pack(fill="x",pady=3)
                btn=action(row,title+"   →",callback);btn.pack(side="left")
                tk.Label(row,text=desc,bg=panel_ink,fg=muted,font=("Segoe UI",9)).pack(side="right",padx=10)
                if callback==login:login_button=btn
    nav={}
    for tab in ["Verbindung","Einrichtung","Bibliothek","App-Updates"]:
        nav[tab]=action(sidebar,tab,lambda name=tab:show(name));nav[tab].pack(fill="x",padx=12,pady=3)
    from pc_status import statuses
    indicators=tk.Frame(sidebar,bg="#11152a");indicators.pack(side="bottom",fill="x",padx=16,pady=8)
    labels={}
    status_events=queue.Queue()
    def read_status():
        def job():
            try:status_events.put(statuses(ROOT))
            except Exception:status_events.put([])
        threading.Thread(target=job,daemon=True).start()
        def collect():
            if status_events.empty():root.after(100,collect);return
            for title,value in status_events.get():
                if title not in labels:
                    labels[title]=tk.Label(indicators,bg="#11152a",fg="#d3dded",anchor="w",justify="left",font=("Segoe UI",9),wraplength=194)
                    labels[title].pack(fill="x",pady=2)
                labels[title].configure(text=title+"  ·  "+value)
            root.after(5000,read_status)
        root.after(100,collect)
    read_status()
    show("Verbindung");root.after(10,diagnose)
    sheets=sorted((ROOT/"intro").glob("sheet*.png"))
    if sheets:
        surface=tk.PhotoImage(width=384,height=216)
        splash=tk.Label(root,bg=ink,image=surface)
        splash.place(relwidth=1,relheight=1)
        cache={}
        def load_sheet(index):
            if index<len(sheets) and index not in cache:
                cache[index]=tk.PhotoImage(file=str(sheets[index]))
        load_sheet(0)
        started=time.monotonic()
        def intro():
            frame=int((time.monotonic()-started)*30)
            index,cell=divmod(frame,12)
            if index>=len(sheets):
                splash.destroy()
                cache.clear()
                return
            load_sheet(index)
            x,y=cell%4*384,cell//4*216
            root.tk.call(str(surface),"copy",str(cache[index]),"-from",x,y,x+384,y+216,"-to",0,0)
            cache.pop(index-1,None)
            if cell<6 and index+1 not in cache:
                root.after_idle(load_sheet,index+1)
            delay=round((started+(frame+1)/30-time.monotonic())*1000)
            root.after(max(1,delay),intro)
        intro()
    root.mainloop()
if __name__=="__main__":gui()
