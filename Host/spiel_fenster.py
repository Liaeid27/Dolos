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

def game_window(key):
    target=targets_now().get(key)
    if not target:return None
    user=ctypes.windll.user32
    user.GetForegroundWindow.restype=wt.HWND
    hwnd=user.GetForegroundWindow()
    if not hwnd:return None
    path=foreground_path(hwnd)
    if not path or not (path.is_relative_to(target[0]) if target[1] else path==target[0]):return None
    if any(x in path.stem.casefold() for x in ("crashreport","launcher","unins","setup","redist")):return None
    return wt.HWND(hwnd)

def screen(key,prepare=False):
    handle=game_window(key)
    if handle is None:return False
    u=ctypes.windll.user32
    u.MonitorFromWindow.argtypes=[wt.HWND,wt.DWORD];u.MonitorFromWindow.restype=wt.HANDLE
    info=MonitorInfo();info.size=ctypes.sizeof(info)
    if not u.GetMonitorInfoW(wt.HANDLE(u.MonitorFromWindow(handle,2)),ctypes.byref(info)):return False
    rect=wt.RECT();origin=wt.POINT()
    if not u.GetClientRect(handle,ctypes.byref(rect)) or not u.ClientToScreen(handle,ctypes.byref(origin)):return False
    m=info.monitor
    if origin.x<=m.left+2 and origin.y<=m.top+2 and origin.x+rect.right>=m.right-2 and origin.y+rect.bottom>=m.bottom-2:return True
    if prepare and rect.right>=320 and rect.bottom>=200 and not u.IsIconic(handle) and u.GetForegroundWindow()==handle.value:
        # Restrict borderless sizing to the game's top-level window on its current monitor.
        style=u.GetWindowLongW(handle,-16)
        if style & 0x40000000 or u.GetWindow(handle,4):return False
        u.SetWindowLongW(handle,-16,ctypes.c_long(style & ~0x00cf0000))
        u.SetWindowPos(handle,None,m.left,m.top,m.right-m.left,m.bottom-m.top,0x0034)
    return False

def playing(key):
    return screen(key)

def close_game(key):
    handle=game_window(key)
    if handle is None:return False
    return bool(ctypes.windll.user32.PostMessageW(handle,0x0010,0,0))
