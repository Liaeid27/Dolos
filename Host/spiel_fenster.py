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

def capture_monitor(require_virtual=False):
    """Use Apollo's active virtual output, including negative desktop coordinates."""
    import os,re
    log=Path(os.environ["ProgramFiles"])/"Apollo/config/sunshine.log"
    name=None
    capture=None
    try:
        with log.open("rb") as stream:
            stream.seek(max(0,stream.seek(0,2)-1048576))
            data=stream.read().replace(b"\0",b"").decode("utf8","ignore")
        events=re.findall(r"Virtual Display (?:created at ([^\r\n]+)|removed successfully)",data)
        if events:name=events[-1].strip().casefold()
        # A long session can outlive the creation line in the log tail.
        # Apollo reports offsets relative to the virtual desktop origin.
        if not events and "Session resuming for app [Virtual Display]" in data:
            section=data.rsplit("Session resuming for app [Virtual Display]",1)[1]
            regions=re.findall(r"Capture size\s*:\s*(\d+)x(\d+)\s+Offset\s*:\s*(-?\d+)x(-?\d+)",section)
            if regions:capture=tuple(map(int,regions[-1]))
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
    if not name and capture and len(monitors)>1:
        width,height,x,y=capture
        left=min(m.monitor.left for m in monitors)+x
        top=min(m.monitor.top for m in monitors)+y
        candidates=[m for m in monitors if not m.flags&1 and
                    (m.monitor.left,m.monitor.top,m.monitor.right,m.monitor.bottom)==(left,top,left+width,top+height)]
        if len(candidates)==1:return candidates[0]
    return match if name else (monitors[0] if len(monitors)==1 and not require_virtual else None)

def stream_launch_args(key):
    # The DX9 fullscreen renderer can leave Desktop Duplication showing the desktop.
    if key=="274170" and capture_monitor(require_virtual=True):
        # Prevent Windows from stretching the legacy SDL render surface at high DPI.
        import winreg
        target=targets_now().get(key)
        if target:
            exe=target[0]/"HotlineMiami2.exe"
            if exe.is_file():
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER,r"Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers") as layers:
                    try:value=winreg.QueryValueEx(layers,str(exe))[0]
                    except FileNotFoundError:value="~"
                    if not any(x.upper() in ("HIGHDPIAWARE","DPIUNAWARE","GDIDPISCALING") for x in value.split()):
                        winreg.SetValueEx(layers,str(exe),0,winreg.REG_SZ,value+" HIGHDPIAWARE")
        return ("-gl",)
    if key=="1874880":
        info=capture_monitor(require_virtual=True)
        if info:
            r=info.monitor
            return ("-window","-screenWidth",str(r.right-r.left),"-screenHeight",str(r.bottom-r.top),
                    "-posX",str(r.left),"-posY",str(r.top),"-forceUpdate")
    target=targets_now().get(key)
    if not target or not target[1] or not (target[0]/"Engine/Binaries").is_dir():
        return ()
    if not any(target[0].glob("*/Binaries/Win64/*-Shipping.exe")):
        return ()
    user=ctypes.windll.user32
    dpi=getattr(user,"SetThreadDpiAwarenessContext",None)
    if dpi:dpi.restype=wt.HANDLE
    previous=dpi(wt.HANDLE(-4)) if dpi else None
    try:
        info=capture_monitor(require_virtual=True)
        if not info:return ()
        r=info.monitor
        return ("-windowed","-ForceRes",f"-ResX={r.right-r.left}",f"-ResY={r.bottom-r.top}",
                f"-WinX={r.left}",f"-WinY={r.top}")
    finally:
        if previous:dpi(wt.HANDLE(previous))

def hotline_resolution(path,size,expected=None):
    """Apply and conditionally restore the four settings of the known window.dat format."""
    import struct
    if not path.is_file() or path.is_symlink():return None
    data=path.read_bytes()
    if len(data)!=16:return None
    original=struct.unpack("<4I",data)
    if not all(240<=v<=16384 for v in (*original[:2],*size[:2])) or max(*original[2:],*size[2:])>2:return None
    if expected is not None and list(original)!=list(expected):return None
    if original!=tuple(size):
        from tempfile import NamedTemporaryFile
        with NamedTemporaryFile(dir=path.parent,delete=False) as tmp:
            name=Path(tmp.name)
            tmp.write(struct.pack("<4I",*size))
        try:name.replace(path)
        finally:name.unlink(missing_ok=True)
    return original

def hotline_window_file():
    buf=ctypes.create_unicode_buffer(260)
    if ctypes.windll.shell32.SHGetFolderPathW(None,5,None,0,buf)!=0:return None
    return Path(buf.value)/"My Games/HotlineMiami2/window.dat"

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
    u.GetAncestor.argtypes=[wt.HWND,wt.UINT];u.GetAncestor.restype=wt.HWND
    if foreground and matches(foreground):
        owner=u.GetAncestor(foreground,3)
        return wt.HWND(owner if owner and matches(owner) else foreground)
    if not background:return None
    windows=[]
    callback=ctypes.WINFUNCTYPE(wt.BOOL,wt.HWND,wt.LPARAM)
    @callback
    def visit(hwnd,param):
        h=wt.HWND(hwnd);rect=wt.RECT()
        if u.IsWindowVisible(h) and u.GetClientRect(h,ctypes.byref(rect)) and matches(hwnd):
            windows.append((rect.right*rect.bottom,hwnd))
        return True
    u.EnumWindows(visit,0)
    return wt.HWND(max(windows)[1]) if windows else None

def screen(key,prepare=False,require_virtual=False):
    u=ctypes.windll.user32
    dpi=getattr(u,"SetThreadDpiAwarenessContext",None)
    if dpi:dpi.restype=wt.HANDLE
    previous=dpi(wt.HANDLE(-4)) if dpi else None
    try:
        handle=game_window(key,True)
        if not handle:return False
        info=capture_monitor(require_virtual) if require_virtual else capture_monitor()
        if not info:return False
        m=info.monitor
        if prepare and u.IsIconic(handle):u.ShowWindowAsync(handle,9)
        rect=wt.RECT();origin=wt.POINT()
        if not u.GetClientRect(handle,ctypes.byref(rect)) or not u.ClientToScreen(handle,ctypes.byref(origin)):return False
        # A larger game window covers every sample yet the encoder sees only a crop.
        fits=(abs(origin.x-m.left)<=8 and abs(origin.y-m.top)<=8 and
              abs(origin.x+rect.right-m.right)<=8 and abs(origin.y+rect.bottom-m.bottom)<=8)
        u.WindowFromPoint.argtypes=[wt.POINT];u.WindowFromPoint.restype=wt.HWND
        u.GetAncestor.argtypes=[wt.HWND,wt.UINT];u.GetAncestor.restype=wt.HWND
        def game_pixel(x,y):
            window=u.WindowFromPoint(wt.POINT(x,y))
            return window and (u.GetAncestor(window,2)==handle.value or u.GetAncestor(window,3)==handle.value and foreground_path(window)==foreground_path(handle))
        visible=fits and not u.IsIconic(handle) and all(
            game_pixel(m.left+int((m.right-m.left)*x),m.top+int((m.bottom-m.top)*y))
            for x,y in ((.5,.5),(.08,.08),(.92,.08),(.08,.92),(.92,.92)))
        if visible:return True
        if prepare:
            style=u.GetWindowLongW(handle,-16)
            if style & 0x40000000:return False
            if not fits:
                if u.IsZoomed(handle):u.ShowWindow(handle,9)
                if (key=="1874880" or key=="274170" and m.right-m.left>=3000) and style & 0x00c00000:
                    # Legacy SDL windows can retain a DPI-scaled minimum frame on UHD displays.
                    u.SetWindowLongW(handle,-16,ctypes.c_long((style & ~0x00cf0000)|0x80000000))
                    u.SetWindowPos(handle,None,m.left,m.top,m.right-m.left,m.bottom-m.top,0x0060)
                    return False
                outer=wt.RECT()
                if not u.GetWindowRect(handle,ctypes.byref(outer)):return False
                u.SetWindowPos(handle,None,m.left+outer.left-origin.x,m.top+outer.top-origin.y,
                               m.right-m.left+outer.right-outer.left-rect.right,
                               m.bottom-m.top+outer.bottom-outer.top-rect.bottom,0x0060)
            u.SetWindowPos(handle,None,0,0,0,0,0x0013)
            u.SetForegroundWindow(handle)
        return False
    finally:
        if previous:dpi(wt.HANDLE(previous))

def launch_stage(key):
    if not key.isascii() or not key.isdecimal() or len(key)>10:return ""
    import datetime,re
    try:
        with (steam_path()/"logs/console_log.txt").open("rb") as log:
            log.seek(max(0,log.seek(0,2)-65536))
            lines=log.read().decode("utf8","replace").splitlines()
        for line in reversed(lines):
            if f"GameAction [AppID {key}," not in line or "changed task to " not in line:continue
            timestamp=datetime.datetime.strptime(line[1:20],"%Y-%m-%d %H:%M:%S").timestamp()
            if abs(time.time()-timestamp)>600:return ""
            task=re.search(r"changed task to (\w+)",line)
            return {"RunningInstallScript":"Steam richtet die Spielkomponenten ein",
                    "SynchronizingCloud":"Steam gleicht Spielstände ab",
                    "UpdatingApp":"Steam aktualisiert das Spiel",
                    "ProcessingVulkanShaders":"Steam bereitet Shader vor"}.get(task[1] if task else "","")
    except (OSError,ValueError):pass
    return ""

def playing(key):return screen(key)

def close_game(key):
    handle=game_window(key,True)
    if not handle:return False
    u=ctypes.windll.user32
    pid=wt.DWORD();u.GetWindowThreadProcessId(handle,ctypes.byref(pid))
    original=foreground_path(handle)
    if not u.PostMessageW(handle,0x0010,0,0):return False
    def cleanup():
        # Several engines destroy their render window but leave Steam tracking a helper.
        # Ask Steam to stop only this title, and only while the original process still owns its PID.
        if not key.isascii() or not key.isdecimal() or len(key)>10:return
        from steam_aktion import running
        if not running(key):return
        from ctypes import windll
        kernel=windll.kernel32
        process=kernel.OpenProcess(0x1000,False,pid.value)
        if not process:return
        try:
            size=wt.DWORD(32768);name=ctypes.create_unicode_buffer(size.value)
            if not kernel.QueryFullProcessImageNameW(process,0,name,ctypes.byref(size)) or Path(name.value).resolve()!=original:return
            import subprocess
            subprocess.Popen([str(steam_path()/"steam.exe"),"+app_stop",key,"0"],creationflags=subprocess.CREATE_NO_WINDOW)
        finally:kernel.CloseHandle(process)
    import threading
    timer=threading.Timer(3,cleanup);timer.daemon=True;timer.start()
    return True
