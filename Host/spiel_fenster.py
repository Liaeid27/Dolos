"""Report only whether the selected game's Windows process owns the foreground."""
import ctypes,hashlib,time
from ctypes import wintypes as wt
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).with_name("vendor")))
import vdf
from importieren import steam_path,read_vdf
from dolos_pc import CUSTOM
import json
last=0
targets={}
def foreground_path(hwnd=None):
    user,kernel=ctypes.windll.user32,ctypes.windll.kernel32
    user.GetForegroundWindow.restype=wt.HWND
    hwnd=hwnd or user.GetForegroundWindow();pid=wt.DWORD()
    user.GetWindowThreadProcessId.argtypes=[wt.HWND,ctypes.POINTER(wt.DWORD)]
    user.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
    kernel.OpenProcess.argtypes=[wt.DWORD,wt.BOOL,wt.DWORD];kernel.OpenProcess.restype=wt.HANDLE
    process=kernel.OpenProcess(0x1000,False,pid.value)
    if not process:return None
    try:
        buf=ctypes.create_unicode_buffer(32768);size=wt.DWORD(len(buf))
        kernel.QueryFullProcessImageNameW.argtypes=[wt.HANDLE,wt.DWORD,wt.LPWSTR,ctypes.POINTER(wt.DWORD)]
        return Path(buf.value).resolve() if kernel.QueryFullProcessImageNameW(process,0,buf,ctypes.byref(size)) else None
    finally:
        kernel.CloseHandle.argtypes=[wt.HANDLE];kernel.CloseHandle(process)
def targets_now():
    global targets,last
    if time.monotonic()-last<12 and targets:return targets
    steam=steam_path();result={}
    for lib in read_vdf(steam/"steamapps/libraryfolders.vdf")["libraryfolders"].values():
        folder=Path(lib["path"])/"steamapps"
        for p in folder.glob("appmanifest_*.acf"):
            try:
                g=read_vdf(p)["AppState"];result[g["appid"]]=((folder/"common"/g["installdir"]).resolve(),True)
            except (KeyError,ValueError,OSError):continue
    for f in steam.glob("userdata/*/config/shortcuts.vdf"):
        with f.open("rb") as stream:shortcuts=vdf.binary_load(stream)["shortcuts"]
        for item in shortcuts.values():
            g={k.lower():v for k,v in item.items()};exe=Path(g.get("exe","").strip('"'))
            if exe.is_file():result[str(((g["appid"]&0xffffffff)<<32)|0x02000000)]=(exe.resolve(),False)
    if CUSTOM.is_file():
        for game in json.loads(CUSTOM.read_text(encoding="utf-8")):
            key=hashlib.sha256(game["name"].strip().encode()).hexdigest()[:24]
            result[key]=(Path(game["exe"]).resolve(),False)
    targets=result;last=time.monotonic();return result
class MonitorInfo(ctypes.Structure):
    _fields_=[("size",wt.DWORD),("monitor",wt.RECT),("work",wt.RECT),("flags",wt.DWORD)]


class MonitorDevice(MonitorInfo):
    _fields_=[("device",wt.WCHAR*32)]

def capture_monitor():
    """Use Apollo's active virtual output, including negative desktop coordinates."""
    import os,re
    log=Path(os.environ["ProgramFiles"])/"Apollo/config/sunshine.log"
    name=None
    try:
        with log.open("rb") as stream:
            stream.seek(max(0,stream.seek(0,2)-1048576))
            data=stream.read().replace(b"\0",b"").decode("utf8","ignore")
        events=re.findall(r"Virtual Display (?:created at ([^\r\n]+)|removed successfully)",data)
        if events:name=events[-1].strip().casefold()
    except OSError:pass
    monitors=[]
    callback=ctypes.WINFUNCTYPE(wt.BOOL,wt.HANDLE,wt.HDC,ctypes.POINTER(wt.RECT),wt.LPARAM)
    @callback
    def visit(handle,dc,rect,param):
        info=MonitorDevice();info.size=ctypes.sizeof(info)
        if ctypes.windll.user32.GetMonitorInfoW(wt.HANDLE(handle),ctypes.byref(info)):monitors.append(info)
        return True
    ctypes.windll.user32.EnumDisplayMonitors(None,None,visit,0)
    match=next((m for m in monitors if m.device.casefold()==name),None)
    return match or (monitors[0] if len(monitors)==1 else None)

def game_window(key,background=False):
    target=targets_now().get(key)
    if not target:return None
    u=ctypes.windll.user32;u.GetForegroundWindow.restype=wt.HWND
    foreground=u.GetForegroundWindow()
    def matches(hwnd):
        title=ctypes.create_unicode_buffer(256);handle=wt.HWND(hwnd)
        u.GetWindowTextW(handle,title,len(title))
        if title.value.casefold() in ("d3dproxywindow","default ime","msctfime ui"):return False
        rect=wt.RECT()
        if not u.IsIconic(handle) and (not u.GetClientRect(handle,ctypes.byref(rect)) or rect.right<320 or rect.bottom<180):return False
        path=foreground_path(hwnd)
        return path and (path.is_relative_to(target[0]) if target[1] else path==target[0]) and not any(
            x in path.stem.casefold() for x in ("crashreport","launcher","unins","setup","redist"))
    if foreground and matches(foreground):return wt.HWND(foreground)
    if not background:return None
    windows=[]
    callback=ctypes.WINFUNCTYPE(wt.BOOL,wt.HWND,wt.LPARAM)
    @callback
    def visit(hwnd,param):
        h=wt.HWND(hwnd);rect=wt.RECT()
        if u.IsWindowVisible(h) and not u.GetWindow(h,4) and u.GetClientRect(h,ctypes.byref(rect)) and matches(hwnd):
            windows.append((rect.right*rect.bottom,hwnd))
        return True
    u.EnumWindows(visit,0)
    return wt.HWND(max(windows)[1]) if windows else None

def screen(key,prepare=False):
    u=ctypes.windll.user32
    dpi=getattr(u,"SetThreadDpiAwarenessContext",None)
    if dpi:dpi.restype=wt.HANDLE
    previous=dpi(wt.HANDLE(-4)) if dpi else None
    try:
        handle=game_window(key,prepare)
        if not handle:return False
        info=capture_monitor()
        if not info:return False
        m=info.monitor
        if prepare and u.IsIconic(handle):u.ShowWindowAsync(handle,9)
        rect=wt.RECT();origin=wt.POINT()
        if not u.GetClientRect(handle,ctypes.byref(rect)) or not u.ClientToScreen(handle,ctypes.byref(origin)):return False
        fits=all(abs(a-b)<=2 for a,b in ((origin.x,m.left),(origin.y,m.top),(origin.x+rect.right,m.right),(origin.y+rect.bottom,m.bottom)))
        if fits and not u.IsIconic(handle) and u.GetForegroundWindow()==handle.value:return True
        if prepare and not u.GetWindow(handle,4):
            style=u.GetWindowLongW(handle,-16)
            if style & 0x40000000:return False
            if not fits:
                u.SetWindowLongW(handle,-16,ctypes.c_long(style & ~0x00cf0000))
                u.SetWindowPos(handle,None,m.left,m.top,m.right-m.left,m.bottom-m.top,0x0060)
            u.SetForegroundWindow(handle)
        return False
    finally:
        if previous:dpi(wt.HANDLE(previous))

def playing(key):return screen(key)

def close_game(key):
    handle=game_window(key,True)
    if not handle:return False
    u=ctypes.windll.user32
    pid=wt.DWORD();u.GetWindowThreadProcessId(handle,ctypes.byref(pid))
    original=foreground_path(handle)
    if not u.PostMessageW(handle,0x0010,0,0):return False
    def cleanup():
        if u.IsWindow(handle) or game_window(key,True):return
        callback=ctypes.WINFUNCTYPE(wt.BOOL,wt.HWND,wt.LPARAM)
        @callback
        def visit(hwnd,_):
            h=wt.HWND(hwnd);owner=wt.DWORD();u.GetWindowThreadProcessId(h,ctypes.byref(owner))
            if owner.value==pid.value and foreground_path(h)==original:
                title=ctypes.create_unicode_buffer(256);u.GetWindowTextW(h,title,len(title))
                if title.value=="D3DProxyWindow":u.PostMessageW(h,0x0010,0,0)
            return True
        u.EnumWindows(visit,0)
    import threading
    timer=threading.Timer(1.5,cleanup);timer.daemon=True;timer.start()
    return True
