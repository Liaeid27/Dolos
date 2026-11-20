"""Steam library metadata. A cached title is a candidate, not proof of entitlement."""
import json
import os
import struct
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def app_names(steam):
    path=steam/"appcache/appinfo.vdf"
    if not path.is_file(): return {}
    data=path.read_bytes()
    if data[:4] != b")DV\x07":
        print("Unbekanntes Steam-Cacheformat. Installierte Spiele und Kontoexport bleiben verfügbar.")
        return {}
    index=struct.unpack_from("<Q",data,8)[0]
    keys=data[index+4:].split(b"\0")
    games={}
    offset=16
    while offset+8<=index:
        appid,size=struct.unpack_from("<II",data,offset)
        if not appid: break
        end=offset+8+size
        if size<60 or end>index: raise ValueError("Unvollständiger Steam-Appcache")
        pos=offset+68
        parents=[]
        common={}
        while pos<end:
            kind=data[pos]; pos+=1
            if kind==8:
                if not parents: break
                if parents==[b"appinfo",b"common"]: break
                parents.pop()
                continue
            key=keys[struct.unpack_from("<I",data,pos)[0]]; pos+=4
            if kind==0: parents.append(key)
            elif kind==1:
                stop=data.index(0,pos,end)
                if parents==[b"appinfo",b"common"] and key in (b"name",b"type"):
                    common[key]=data[pos:stop].decode("utf8","replace")
                pos=stop+1
            elif kind in (2,3,4,6): pos+=4
            elif kind in (7,10): pos+=8
            else: break
        if common.get(b"type","").lower() in {"game","demo","mod","application","beta","video","music"} and common.get(b"name"):
            games[str(appid)]=common[b"name"]
        offset=end
    return games


def expand(steam,installed,owned_file=None):
    titles=app_names(steam)
    states={key:"shortcut" if int(key)>0xffffffff else "installed" for key in installed}
    candidates={p.stem:titles[p.stem] for p in steam.glob("userdata/*/config/librarycache/[0-9]*.json") if p.stem in titles}
    owned={}
    if owned_file:
        doc=json.loads(Path(owned_file).read_text(encoding="utf-8-sig"))
        if "rgOwnedApps" in doc:
            owned={str(i):titles.get(str(i)) for i in doc["rgOwnedApps"]}
        else:
            owned={str(g["appid"]):g["name"] for g in doc["response"]["games"]}
        candidates.update(owned)
    family={}
    family_path=Path(__file__).with_name("Steam-Familie.json")
    if family_path.is_file():
        for row in json.loads(family_path.read_text(encoding="utf-8-sig"))["response"]["apps"]:
            key=str(row["appid"])
            if key.isdecimal() and key not in owned:family[key]=row.get("name") or titles.get(key)
        candidates.update(family)
    for appid,name in candidates.items():
        if not appid.isdecimal() or appid in installed: continue
        installed[appid]=(name or ("Steam "+appid),steam/"appcache/librarycache"/appid/"library_600x900.jpg")
        states[appid]="owned" if appid in owned else ("family" if appid in family else "cached")
    return states


def grid_art(games,folder):
    token=os.environ.get("STEAMGRIDDB_API_KEY")
    if not token: return games
    folder.mkdir(parents=True,exist_ok=True)
    def api(path):
        req=urllib.request.Request("https://www.steamgriddb.com/api/v2/"+path,
                                   headers={"Authorization":"Bearer "+token,"User-Agent":"Aster-TV/1"})
        with urllib.request.urlopen(req,timeout=8) as response:
            return json.load(response)["data"]
    result=dict(games)
    for key,(name,original) in games.items():
        path=folder/(key+".art")
        try:
            if not path.exists():
                if int(key)>0xffffffff:
                    matches=[g for g in api("search/autocomplete/"+urllib.parse.quote(name,safe="")) if g["name"].casefold()==name.casefold()]
                    if len(matches)!=1: continue
                    identifier="game/"+str(matches[0]["id"])
                else: identifier="steam/"+key
                options=api("grids/"+identifier+"?dimensions=600x900&types=static&mimes=image%2Fpng,image%2Fjpeg")
                if not options: continue
                url=options[0]["url"]; parsed=urllib.parse.urlparse(url)
                if parsed.scheme!="https" or parsed.hostname!="cdn2.steamgriddb.com": continue
                with urllib.request.urlopen(url,timeout=12) as response:
                    art=response.read(12*1024*1024+1)
                if len(art)>12*1024*1024 or not art.startswith((b"\x89PNG\r\n\x1a\n",b"\xff\xd8\xff")): continue
                temp=path.with_suffix(".tmp");temp.write_bytes(art);temp.replace(path)
            result[key]=(name,path)
        except urllib.error.HTTPError as err:
            if err.code in (401,403,429):
                print("SteamGridDB antwortet mit HTTP",err.code,"– lokale Cover werden verwendet.");break
        except (OSError,ValueError,KeyError):
            continue
    return result

def steam_covers(games, folder):
    from concurrent.futures import ThreadPoolExecutor
    folder.mkdir(parents=True,exist_ok=True)
    def load(item):
        key,(name,old)=item
        if int(key)>0xffffffff or (old and old.is_file()):return key,(name,old)
        target=folder/(key+".jpg")
        if not target.exists():
            url="https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/"+key+"/library_600x900.jpg"
            try:
                with urllib.request.urlopen(url,timeout=6) as reply: art=reply.read(5*1024*1024+1)
                if len(art)<=5*1024*1024 and art.startswith(b"\xff\xd8\xff"):
                    temp=target.with_suffix(".tmp");temp.write_bytes(art);temp.replace(target)
            except OSError: pass
        return key,(name,target if target.is_file() else old)
    with ThreadPoolExecutor(max_workers=6) as workers:
        return dict(workers.map(load,games.items()))
