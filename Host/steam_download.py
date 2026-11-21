"""Operate the selected row in the local Steam client's Downloads view."""
import ctypes
from ctypes import wintypes as wt
import json
import os
from pathlib import Path
import sys
import time

sys.path.insert(0,str(Path(__file__).with_name("vendor")))
import comtypes.client as com
from importieren import steam_path
from spiel_fenster import foreground_path

com.gen_dir=None
ui=com.GetModule("UIAutomationCore.dll")
automation=com.CreateObject(ui.CUIAutomation8,interface=ui.IUIAutomation)
user=ctypes.windll.user32
user.GetForegroundWindow.restype=wt.HWND
user.WindowFromPoint.argtypes=[wt.POINT]
user.WindowFromPoint.restype=wt.HWND
user.GetAncestor.argtypes=[wt.HWND,wt.UINT]
user.GetAncestor.restype=wt.HWND
user.SetThreadDpiAwarenessContext(wt.HANDLE(-4))

FIRST={"Jetzt herunterladen","Download now","Download fortsetzen","Resume download","Retry","Erneut versuchen"}
REMOVE={"Aus Warteschlange entfernen","Remove from Queue"}
ACTIVE={"Aktiv","Active"}
UNSCHEDULED={"Nicht in der Warteschlange","Unscheduled"}
DONE={"Abgeschlossen","Completed"}


def find(parent,property_id,value,scope=4):
    rows=parent.FindAll(scope,automation.CreatePropertyCondition(property_id,value))
    return [rows.GetElement(i) for i in range(rows.Length)]


def steam_window(hwnd,steam):
    path=foreground_path(hwnd) if hwnd else None
    return path and path.name.lower()=="steamwebhelper.exe" and path.is_relative_to(steam)


def main_window(steam):
    user.FindWindowW.restype=wt.HWND
    hwnd=user.FindWindowW(None,"Steam")
    if hwnd and steam_window(hwnd,steam):return automation.ElementFromHandle(hwnd)


def locate(root,title):
    rows=[]
    for link in find(root,30005,title):
        if link.CurrentControlType not in (50005,50020):continue
        node=link;row=None
        while node:
            if node.CurrentControlType==50000 and row is None:row=node
            if node.CurrentControlType==50008:
                if row and not any(automation.CompareElements(row,old) for old,_ in rows):rows.append((row,node.CurrentName.strip()))
                break
            node=automation.ControlViewWalker.GetParentElement(node)
    if not rows:
        # Steam hides the title link in the active row, but exposes its complete accessible name.
        for group in find(root,30003,50008):
            if group.CurrentName.strip() not in ACTIVE:continue
            for button in find(group,30003,50000):
                if button.CurrentName.startswith(title+" "):rows.append((button,group.CurrentName.strip()))
    return rows[0] if len(rows)==1 else (None,"")


def invoke(element):
    pattern=element.GetCurrentPattern(10000)
    if not pattern:raise ValueError("Die Steam-Aktion ist gerade nicht verfügbar.")
    pattern.QueryInterface(ui.IUIAutomationInvokePattern).Invoke()


def remove_row(row,handle,steam):
    # The remove icon has no accessible name. Select its named context-menu command.
    scroll=row.GetCurrentPattern(10017)
    if scroll:scroll.QueryInterface(ui.IUIAutomationScrollItemPattern).ScrollIntoView()
    rect=row.CurrentBoundingRectangle
    point=wt.POINT((rect.left+rect.right)//2,(rect.top+rect.bottom)//2)
    if user.GetForegroundWindow()!=handle or user.GetAncestor(user.WindowFromPoint(point),2)!=handle:
        raise ValueError("Steam konnte die Downloadliste nicht in den Vordergrund holen.")
    old=wt.POINT();user.GetCursorPos(ctypes.byref(old))
    try:
        user.SetCursorPos(point.x,point.y)
        user.mouse_event(8,0,0,0,0);user.mouse_event(16,0,0,0,0)
        for _ in range(10):
            time.sleep(.09)
            active=user.GetForegroundWindow()
            if not steam_window(active,steam):break
            window=automation.ElementFromHandle(active)
            for label in REMOVE:
                for entry in find(window,30005,label):
                    if entry.CurrentControlType in (50011,50000):
                        r=entry.CurrentBoundingRectangle
                        target=wt.POINT((r.left+r.right)//2,(r.top+r.bottom)//2)
                        if entry.CurrentIsOffscreen or r.right<=r.left or not steam_window(user.GetAncestor(user.WindowFromPoint(target),2),steam):continue
                        user.SetCursorPos(target.x,target.y)
                        user.mouse_event(2,0,0,0,0);user.mouse_event(4,0,0,0,0)
                        user.SetCursorPos(point.x,point.y);return
    finally:
        now=wt.POINT();user.GetCursorPos(ctypes.byref(now))
        if (now.x,now.y)==(point.x,point.y):user.SetCursorPos(old.x,old.y)
    raise ValueError("Steam bietet für diesen Titel kein Entfernen aus der Warteschlange an.")


def perform(action,title):
    steam=steam_path().resolve()
    root=main_window(steam)
    handle=root.CurrentNativeWindowHandle if root else 0
    before=user.GetForegroundWindow();minimized=handle and user.IsIconic(handle)
    try:
        if not root or not locate(root,title)[0] or minimized:
            os.startfile("steam://open/downloads")
        for _ in range(24):
            root=main_window(steam)
            if root:
                handle=root.CurrentNativeWindowHandle
                row,section=locate(root,title)
                if row:break
            time.sleep(.12)
        else:raise ValueError("Download in Steam nicht mehr verfügbar.")
        if section in DONE:raise ValueError("Steam hat diesen Download bereits abgeschlossen.")
        buttons=find(row,30003,50000)
        if action=="inspect":return {"section":section,"buttons":[b.CurrentName for b in buttons]}
        if action=="first":
            buttons=[b for b in buttons if b.CurrentName in FIRST]
            if len(buttons)==1:invoke(buttons[0])
            elif section not in ACTIVE:raise ValueError("Steam kann diesen Titel gerade nicht vorziehen.")
        elif action in ("pause","cancel"):
            pause=next((b for b in buttons if b.CurrentName in {"Download pausieren","Pause download"}),None)
            paused_here=False
            if section in ACTIVE and pause:
                invoke(pause);paused_here=True
                for _ in range(12):
                    time.sleep(.1);row,section=locate(root,title)
                    if row and any(b.CurrentName in {"Download fortsetzen","Resume download"} for b in find(row,30003,50000)):break
            try:
                if row and section not in UNSCHEDULED:remove_row(row,handle,steam)
            except Exception:
                if paused_here:
                    row,section=locate(root,title)
                    if row and section in ACTIVE:
                        resume=[b for b in find(row,30003,50000) if b.CurrentName in {"Download fortsetzen","Resume download"}]
                        if len(resume)==1:invoke(resume[0])
                raise
        else:raise ValueError("Unbekannte Aktion.")
        for _ in range(18):
            time.sleep(.25)
            current=main_window(steam)
            if not current:continue
            latest,group=locate(current,title)
            if action=="first" and group in ACTIVE|DONE:return {"ok":True}
            if action!="first" and (not latest or group in UNSCHEDULED):return {"ok":True}
            if group in DONE:raise ValueError("Steam hat den Download inzwischen abgeschlossen.")
        raise ValueError("Steam hat die Änderung der Warteschlange noch nicht bestätigt.")
    finally:
        if before and before!=handle and user.GetForegroundWindow()==handle:
            if minimized:user.ShowWindowAsync(wt.HWND(handle),6)
            user.SetForegroundWindow(wt.HWND(before))


if __name__=="__main__":
    try:result=perform(*sys.argv[1:3])
    except ValueError as exc:result={"error":str(exc)}
    except Exception:result={"error":"Die Steam-Downloadliste ist gerade nicht bedienbar."}
    print(json.dumps(result))
