"""Steam OpenID login through the PC browser. Only an owned-games JSON list is saved."""
import json
import os
import re
import secrets
import time
import urllib.parse as url
import urllib.request as net
import webbrowser
from http.server import BaseHTTPRequestHandler,HTTPServer

ENDPOINT="https://steamcommunity.com/openid/login"
def login():
    path="/"+secrets.token_urlsafe(24)
    class Return(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            parsed=url.urlsplit(self.path)
            if parsed.path!=path:self.send_error(404);return
            q=dict(url.parse_qsl(parsed.query));claimed=q.get("openid.claimed_id","")
            try:
                if not (q.get("openid.mode")=="id_res" and q.get("openid.op_endpoint")==ENDPOINT and
                        q.get("openid.return_to")==callback and q.get("openid.identity")==claimed and
                        re.fullmatch(r"https://steamcommunity\.com/openid/id/\d{17}",claimed)):
                    raise ValueError("Steam-Anmeldung abgebrochen oder ungültig.")
                q["openid.mode"]="check_authentication"
                with net.urlopen(ENDPOINT,url.urlencode(q).encode(),timeout=15) as r:
                    if "is_valid:true" not in r.read().decode().splitlines():raise ValueError("Steam hat die Anmeldung nicht bestätigt.")
                self.server.result=claimed.rsplit("/",1)[1];self.send_response(200);self.end_headers()
                self.wfile.write(b"Dolos: Steam-Konto bestaetigt. Dieses Fenster kann geschlossen werden.")
            except (ValueError,OSError) as e:self.server.error=str(e);self.send_error(400)
    with HTTPServer(("127.0.0.1",0),Return) as server:
        server.timeout=1
        realm="http://127.0.0.1:"+str(server.server_port)+"/";callback=realm+path[1:];ns="http://specs.openid.net/auth/2.0"
        webbrowser.open(ENDPOINT+"?"+url.urlencode({"openid.ns":ns,"openid.mode":"checkid_setup","openid.realm":realm,
            "openid.return_to":callback,"openid.identity":ns+"/identifier_select","openid.claimed_id":ns+"/identifier_select"}))
        deadline=time.monotonic()+180
        while time.monotonic()<deadline:
            server.handle_request()
            if hasattr(server,"result"):return server.result
            if hasattr(server,"error"):raise ValueError(server.error)
    raise TimeoutError("Steam-Anmeldung abgelaufen.")

def fetch_owned(steam_id):
    key=os.environ.get("STEAM_WEB_API_KEY")
    if not key:return None
    params=url.urlencode(dict(steamid=steam_id,key=key,include_appinfo=1,include_played_free_games=1))
    try:
        with net.urlopen("https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/?"+params,timeout=15) as r:doc=json.load(r)
    except OSError:raise RuntimeError("Steam-Bibliothek nicht erreichbar. API-Schlüssel und Verbindung prüfen.") from None
    if not isinstance(doc.get("response",{}).get("games"),list):raise ValueError("Steam gibt die Spieleliste nicht frei. Spieldetails und Kontozugriff prüfen.")
    return doc
