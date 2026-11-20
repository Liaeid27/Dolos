package com.limelight;

import android.app.*;
import android.content.*;
import android.graphics.*;
import android.graphics.drawable.GradientDrawable;
import android.database.DataSetObserver;
import android.os.Bundle;
import android.view.*;
import android.widget.*;
import com.limelight.grid.AppGridAdapter;
import com.limelight.preferences.StreamSettings;

/** TV home. Video decoding and input forwarding stay in Game. */
final class ConsoleHome extends FrameLayout {
    interface Actions { void play(AppView.AppObject game); void quit(); }
    final Activity host;
    final Actions actions;
    final Catalog console;
    final ControlLink link;
    final TextView detail;
    AppGridAdapter library;
    int profile;
    android.content.SharedPreferences profiles() { return host.getSharedPreferences("profiles",0); }
    String profileName(int id) { return profiles().getString("name"+id,id==0?"Standard":"Spieler "+(id+1)); }
    String prefix(int id) { return "[Aster P"+id+"] "; }
    String displayName(AppView.AppObject g) { String name=Catalog.title(g.toString()); return profile!=0 && name.startsWith(prefix(profile))?name.substring(prefix(profile).length()):name; }
    void chooseProfile() {
        String[] options={profileName(0),profileName(1),profileName(2),profileName(3),"Profil umbenennen"};
        ConsoleDock.show(host,"Wer spielt?",options,i->{
            if(i==4) {
                EditText input=new EditText(host); input.setSingleLine(); input.setText(profileName(profile));
                new AlertDialog.Builder(host).setTitle("Profilname").setView(input).setNegativeButton("Abbrechen",null)
                    .setPositiveButton("Speichern",(dialog,w)->{
                        String n=input.getText().toString().trim();
                        if(!n.isEmpty()) {profiles().edit().putString("name"+profile,n.substring(0,Math.min(n.length(),20))).apply(); link.prefs().edit().putString("pendingName"+profile,profileName(profile)).apply();if(link.prefs().contains("token"))link.run("profileNames","","");refresh();}
                    }).show();
            } else {
                profile=i; profiles().edit().putInt("active",i).apply();console.applyTheme(); 
                
                refresh();
            }
        });
    }
    final DataSetObserver observer=new DataSetObserver(){
        public void onChanged(){refresh();}
        public void onInvalidated(){refresh();}
    };
    ConsoleHome(Activity a,String name,Actions callbacks){
        super(a);host=a;actions=callbacks;profile=profiles().getInt("active",0);
        detail=new TextView(a);detail.setText(name);
        link=new ControlLink(this);console=new Catalog(this);
        addView(console.web,new FrameLayout.LayoutParams(-1,-1));
    }
    void attach(AppGridAdapter adapter){
        if(library!=null)library.unregisterDataSetObserver(observer);
        library=adapter;adapter.registerDataSetObserver(observer);refresh();
    }
    void refresh(){console.update();}
    boolean belongsToProfile(AppView.AppObject g) {
        String name=g.toString();
        if((name.equals("Dolos • Ausschalten") || name.equals("Aster • Ausschalten") || name.startsWith("[AC-REMOVE:"))) return false;
        return !name.startsWith("[Aster P");
    }
    String shelfKey() { return "shelf."+host.getIntent().getStringExtra(AppView.UUID_EXTRA)+"."+profile; }
    java.util.Set<String> hiddenTiles() {
        return new java.util.HashSet<>(profiles().getStringSet(shelfKey(),java.util.Collections.emptySet()));
    }
    java.util.Set<String> extraPins() {
        return new java.util.HashSet<>(profiles().getStringSet(shelfKey()+".pins",java.util.Collections.emptySet()));
    }
    boolean onShelf(AppView.AppObject g,java.util.Set<String> hidden,java.util.Set<String> pinned) {
        String id=String.valueOf(g.app.getAppId());
        String key="steam."+Catalog.steamId(g.toString());
        return !hidden.contains(id) && !hidden.contains(key) && (pinned.contains(id) || pinned.contains(key));
    }
    void setPinned(AppView.AppObject g,boolean value) {
        String id=String.valueOf(g.app.getAppId());
        java.util.Set<String> hidden=hiddenTiles(),pinned=extraPins();
        String steamId=Catalog.steamId(g.toString());
        String key=steamId.isEmpty()?id:"steam."+steamId;
        hidden.remove(id);pinned.remove(id);
        if(value){hidden.remove(key);pinned.add(key);}else{pinned.remove(key);hidden.add(key);}
        profiles().edit().putStringSet(shelfKey(),hidden).putStringSet(shelfKey()+".pins",pinned).apply();
    }
    void power() {
        String[] entries={"PC wecken","PC herunterfahren und schließen","Konsole schließen","PC in den Energiesparmodus versetzen"};
        ConsoleDock.show(host,"Energie",entries,i->{
            if(i==0)((AppView)host).wakeHost();
            if(i==2)ConsoleBoot.sequence(host,true,host::finishAffinity);
            if(i==1||i==3)ConsoleDock.show(host,i==1?"PC herunterfahren?":"PC in den Energiesparmodus versetzen?",
                new String[]{"Abbrechen",i==1?"Herunterfahren":"Energiesparmodus"},choice->{
                    if(choice==1){if(!link.prefs().contains("token"))link.pair();else link.run(i==1?"power":"sleep","","");}
                });
        });
    }
    static SharedPreferences appearance(Context context){
        int slot=context.getSharedPreferences("profiles",0).getInt("active",0);
        return context.getSharedPreferences(slot==0?"studio":"appearance."+slot,0);
    }
    static final class Horizon extends View {
        final Paint p=new Paint(Paint.ANTI_ALIAS_FLAG); int tint=340;
        Horizon(Context c){super(c);}
        protected void onDraw(Canvas c){
            int w=getWidth(),h=getHeight(); if(w==0||h==0)return;
            int color=Color.HSVToColor(new float[]{202+((tint % 52 + 52) % 52),.61f,.36f});
            p.setShader(new LinearGradient(0,0,w,h,new int[]{0xff101728,color,0xff090e19},null,Shader.TileMode.CLAMP));
            c.drawRect(0,0,w,h,p); p.setShader(null);
            for(int i=0;i<56;i++){
                float k=i/55f+(float)Math.sin(android.os.SystemClock.uptimeMillis()/2400.0+i*.02)*.07f;
                Path path=new Path(); path.moveTo(-w*.1f,h*(.78f+k*.08f));
                path.cubicTo(w*.32f,h*(.28f+k*.23f),w*.53f,h*(1.35f-k*.34f),w*1.1f,h*(.20f+k*.30f));
                p.setStyle(Paint.Style.STROKE); p.setStrokeWidth(1.3f);
                p.setColor(Color.argb(12+(int)(22*Math.sin(k*Math.PI)),145,189,247)); c.drawPath(path,p);
            }
            p.setStyle(Paint.Style.FILL); 
        }
    }
}

