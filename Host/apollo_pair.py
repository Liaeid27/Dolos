"""Submit the Android pairing PIN directly to the local Apollo service."""
from http.client import HTTPSConnection
from http.cookies import SimpleCookie
import json
import re
import ssl
import subprocess
from pc_status import apollo_port

def verified_connection():
    port=apollo_port()+1
    # Apollo uses a self-signed certificate. Authenticate this exact loopback socket
    # by the Windows service owning its server endpoint before sending credentials.
    ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname=False
    ctx.verify_mode=ssl.CERT_NONE
    con=HTTPSConnection("127.0.0.1",port,context=ctx,timeout=8)
    con.connect()
    try:
        peer=con.sock.getsockname()[1]
        script=("$ErrorActionPreference='Stop';"
                f"$c=Get-NetTCPConnection -State Established -LocalPort {port} -RemotePort {peer} -RemoteAddress 127.0.0.1;"
                "$s=Get-CimInstance Win32_Service -Filter \"Name='ApolloService'\";"
                "$p=Get-CimInstance Win32_Process -Filter ('ProcessId='+$c.OwningProcess);"
                "if($s.State -eq 'Running' -and $p.Name -eq 'sunshine.exe' -and ($p.ParentProcessId -eq $s.ProcessId -or $p.ProcessId -eq $s.ProcessId)){exit 0};exit 1")
        r=subprocess.run(["powershell.exe","-NoProfile","-Command",script],capture_output=True,timeout=12,creationflags=subprocess.CREATE_NO_WINDOW)
        if r.returncode:raise ValueError("Der lokale Apollo-Dienst konnte nicht bestätigt werden. Verwende die Apollo-Webseite.")
        return con
    except Exception:
        con.close()
        raise

def post(route,body,cookie=""):
    con=verified_connection()
    try:
        headers={"Content-Type":"application/json"}
        if cookie:headers["Cookie"]=cookie
        con.request("POST",route,json.dumps(body).encode(),headers)
        response=con.getresponse()
        status=response.status;cookies=SimpleCookie()
        for key,value in response.getheaders():
            if key.lower()=="set-cookie":cookies.load(value)
        raw=response.read(65536)
        if status!=200:
            raise ValueError("Apollo-Anmeldung prüfen." if status in (401,403) else "Apollo antwortet mit "+str(status)+".")
        return raw,"; ".join(k+"="+v.coded_value for k,v in cookies.items())
    finally:con.close()

def pair(pin,username,password):
    if not re.fullmatch(r"[0-9]{4}",pin):raise ValueError("Die vier Ziffern vom Android-Bildschirm eingeben.")
    _,session=post("/api/login",{"username":username,"password":password})
    if not session:raise ValueError("Apollo hat die Anmeldung nicht bestätigt.")
    raw,_=post("/api/pin",{"pin":pin,"name":"Dolos"},session)
    if json.loads(raw).get("status") is not True:raise ValueError("Keine passende Kopplung offen. Eine neue PIN am Handy oder TV anzeigen lassen.")
