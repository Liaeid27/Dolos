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


def remove_row(row):
    buttons=find(row,30003,50000)
    named=[b for b in buttons if b.CurrentName in REMOVE]
    if len(named)==1:
        invoke(named[0]);return
    # In the Steam Downloads accessibility tree a scheduled item exposes
    # the primary Download Now command and one icon-only queue removal command.
    primary=[b for b in buttons if b.CurrentName in FIRST]
    secondary=[b for b in buttons if not b.CurrentName and b.CurrentIsEnabled]
    if len(buttons)==2 and len(primary)==1 and len(secondary)==1:
        invoke(secondary[0]);return
    raise ValueError("Steam bietet für diesen Eintrag keine Warteschlangenaktion an.")

def perform(action,title):
    steam=steam_path().resolve();root=main_window(steam)
    if not root or not locate(root,title)[0]:
        os.startfile("steam://open/downloads")
    for _ in range(24):
        root=main_window(steam)
        if root:
            row,section=locate(root,title)
            if row:break
        time.sleep(.12)
    else:raise ValueError("Download in Steam nicht mehr verfügbar.")
    if section in DONE:return {"ok":True,"completed":True}
    buttons=find(row,30003,50000)
    if action=="inspect":return {"section":section,"buttons":[b.CurrentName for b in buttons]}
    if action=="first":
        targets=[b for b in buttons if b.CurrentName in FIRST]
        if len(targets)==1:invoke(targets[0])
        elif section not in ACTIVE:raise ValueError("Steam kann diesen Titel gerade nicht vorziehen.")
    elif action in ("pause","cancel"):
        if section in ACTIVE:
            if action=="cancel":
                # Ask Steam for this row's own commands. An installed game's
                # update may be mandatory and expose no removal command.
                try:
                    row.QueryInterface(ui.IUIAutomationElement3).ShowContextMenu()
                except Exception:
                    raise ValueError("Steam erlaubt bei diesem aktiven Update nur Anhalten.")
                for _ in range(6):
                    entries=[item for label in REMOVE for item in find(root,30005,label)
                             if item.CurrentControlType==50011 and item.CurrentIsEnabled]
                    if len(entries)==1:
                        invoke(entries[0]);break
                    time.sleep(.1)
                else:raise ValueError("Steam erlaubt bei diesem aktiven Update nur Anhalten.")
            else:
                pause=[b for b in buttons if b.CurrentName in {"Download pausieren","Pause download"}]
                if len(pause)==1:invoke(pause[0])
        elif section not in UNSCHEDULED:remove_row(row)
    else:raise ValueError("Unbekannte Aktion.")
    for _ in range(20):
        time.sleep(.2);root=main_window(steam)
        if not root:continue
        latest,group=locate(root,title)
        labels={b.CurrentName for b in find(latest,30003,50000)} if latest else set()
        if group in DONE:return {"ok":True,"completed":True}
        if action=="first" and group in ACTIVE and not labels.intersection({"Download fortsetzen","Resume download"}):return {"ok":True}
        if action=="pause" and group in ACTIVE and labels.intersection({"Download fortsetzen","Resume download"}):return {"ok":True}
        if action!="first" and group in UNSCHEDULED:return {"ok":True}
    raise ValueError("Steam hat die Änderung noch nicht bestätigt.")

if __name__=="__main__":
    try:result=perform(*sys.argv[1:3])
    except ValueError as exc:result={"error":str(exc)}
    except Exception:result={"error":"Die Steam-Downloadliste ist gerade nicht bedienbar."}
    print(json.dumps(result))
