"""Estimate the installed size of Windows public depots from Steam's local catalogue."""
import struct
from pathlib import Path

def required_sizes(steam,ids):
    data=(steam/"appcache/appinfo.vdf").read_bytes()
    if data[:4]!=b")DV\x07":return {}
    index=struct.unpack_from("<Q",data,8)[0];keys=data[index+4:].split(b"\0");offset=16;result={}
    while offset+8<=index:
        app,size=struct.unpack_from("<II",data,offset);end=offset+8+size
        if not app or size<60 or end>index:break
        pos=offset+68;offset=end;key=str(app)
        if key not in ids:continue
        stack=[];depots={}
        while pos<end:
            kind=data[pos];pos+=1
            if kind==8:
                if not stack:break
                stack.pop();continue
            field=keys[struct.unpack_from("<I",data,pos)[0]];pos+=4
            if kind==0:stack.append(field);continue
            if kind==1:
                stop=data.index(0,pos,end);value=data[pos:stop];pos=stop+1
            elif kind in (2,3,4,6):value=str(struct.unpack_from("<I",data,pos)[0]).encode();pos+=4
            elif kind in (7,10):value=str(struct.unpack_from("<Q",data,pos)[0]).encode();pos+=8
            else:break
            if len(stack)>=3 and stack[1]==b"depots" and stack[2].isdigit():
                depot=depots.setdefault(stack[2],{})
                if stack[3:]==[b"manifests",b"public"] and field==b"size" and value.isdigit():depot[b"bytes"]=int(value)
                elif stack[3:]==[b"config"] and field in (b"oslist",b"language",b"osarch"):depot[field]=value
                elif len(stack)==3 and field in (b"dlcappid",b"depotfromapp",b"optional"):depot[field]=value
        total=sum(d.get(b"bytes",0) for d in depots.values() if not (set(d)&{b"dlcappid",b"depotfromapp",b"language",b"osarch"}) and d.get(b"optional")!=b"1" and b"windows" in d.get(b"oslist",b"windows").split(b","))
        if total:result[key]=total
    return result
