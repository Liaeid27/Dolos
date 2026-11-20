"""Warm the household Steam catalogue on the PC so TVs share one download."""
import json,time,os,urllib.request,urllib.parse,urllib.error
from pathlib import Path
from dolos_pc import save

def trusted(url):
    parts=urllib.parse.urlsplit(url or "")
    return url if parts.scheme=="https" and (parts.hostname or "").endswith(".steamstatic.com") else ""

def update(folder,rows,art,media):
    folder.mkdir(parents=True,exist_ok=True)
    for row in sorted(rows,key=lambda r:(r["state"]!="installed",r["name"].casefold())):
        key=row["id"]
        if not key.isascii() or not key.isdecimal():continue
        target=folder/(key+".json")
        if target.exists() and time.time()-target.stat().st_mtime<604800:continue
        try:
            with urllib.request.urlopen("https://store.steampowered.com/api/appdetails?l=german&cc=de&appids="+key,timeout=7) as res:
                data=json.load(res).get(key,{}).get("data",{})
            movies=data.get("movies",[])
            movie=next((trusted(m.get("hls_h264")) or trusted(m.get("mp4",{}).get("480")) for m in sorted(movies,key=lambda m:not m.get("highlight")) if trusted(m.get("hls_h264")) or trusted(m.get("mp4",{}).get("480"))),"")
            compact=dict(header=trusted(data.get("header_image")),description=data.get("short_description",""),genre=" · ".join(g["description"] for g in data.get("genres",[])[:2]),movie=movie,shots=[dict(thumb=trusted(s.get("path_thumbnail")),full=trusted(s.get("path_full"))) for s in data.get("screenshots",[])[:4]])
            if (key,"cover") not in art and compact["header"]:
                base="https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/"+key
                for url in (base+"/library_600x900.jpg",compact["header"]):
                    try:
                        with urllib.request.urlopen(url,timeout=5) as res:payload=res.read(4000001)
                        if payload.startswith(b"\xff\xd8") and len(payload)<=4000000:
                            temp=folder/(key+".part");temp.write_bytes(payload);os.replace(temp,folder/(key+".jpg"));break
                    except OSError:continue
            save(target,compact)
            if data:media[key]=compact
        except urllib.error.HTTPError as error:
            if error.code==429:return
        except (OSError,ValueError,KeyError):pass
        time.sleep(1.25)

def warm_heroes(folder,art,media):
    for key,row in list(media.items()):
        target=folder/(key+"-hero.jpg")
        if (key,"hero") in art or target.exists() or not row.get("shots"):continue
        url=trusted(row["shots"][0].get("thumb"))
        if not url:continue
        try:
            with urllib.request.urlopen(url,timeout=5) as res:payload=res.read(1500001)
            if payload.startswith(b"\xff\xd8") and len(payload)<=1500000:
                temp=target.with_suffix(".part");temp.write_bytes(payload);os.replace(temp,target)
        except OSError:pass
        time.sleep(.6)
