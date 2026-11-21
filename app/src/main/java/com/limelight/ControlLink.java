package com.limelight;

import android.app.AlertDialog;
import android.content.SharedPreferences;
import android.os.SystemClock;
import android.widget.EditText;
import android.widget.Toast;
import org.json.JSONObject;
import java.io.*;
import java.net.*;
import java.security.*;
import java.security.cert.X509Certificate;
import java.util.*;
import java.util.concurrent.*;
import javax.net.ssl.*;

/** TLS-pinned companion for console management. Video uses Moonlight separately. */
final class ControlLink {
    final ConsoleHome home;
    final ExecutorService io=Executors.newSingleThreadExecutor();
    volatile boolean busy,closed;
    volatile long lastResponse;
    int mediaCount=-1;
    String fingerprint;
    JSONObject snapshot=new JSONObject();
    ControlLink(ConsoleHome h){home=h;}
    SharedPreferences prefs(){return home.host.getSharedPreferences("dolos-control-"+home.host.getIntent().getStringExtra(AppView.UUID_EXTRA),0);}
    String address(){return ((AppView)home.host).controlAddress();}
    static String hash(X509Certificate cert)throws Exception {
        StringBuilder b=new StringBuilder();
        for(byte v:MessageDigest.getInstance("SHA-256").digest(cert.getEncoded()))b.append(String.format(Locale.US,"%02X",v&255));
        return b.toString();
    }
    static HttpsURLConnection connection(String host,String path,String expected)throws Exception {
        String[] seen={null};
        TrustManager[] trust={new X509TrustManager(){
            public X509Certificate[] getAcceptedIssuers(){return new X509Certificate[0];}
            public void checkClientTrusted(X509Certificate[] c,String a)throws java.security.cert.CertificateException {throw new java.security.cert.CertificateException();}
            public void checkServerTrusted(X509Certificate[] c,String a)throws java.security.cert.CertificateException{
                try{c[0].checkValidity();seen[0]=hash(c[0]);if(expected!=null&&!expected.equals(seen[0]))throw new Exception("Prüfzeichen geändert");}
                catch(Exception e){throw new java.security.cert.CertificateException(e);}
            }
        }};
        SSLContext ssl=SSLContext.getInstance("TLS");ssl.init(null,trust,new SecureRandom());
        URL endpoint=new URL("https",host,48291,path);
        HttpsURLConnection con=(HttpsURLConnection)endpoint.openConnection();
        con.setInstanceFollowRedirects(false);con.setConnectTimeout(2200);con.setReadTimeout(8500);
        con.setSSLSocketFactory(ssl.getSocketFactory());
        con.setHostnameVerifier((h,s)->seen[0]!=null && (expected==null || expected.equals(seen[0])));
        return con;
    }
    static JSONObject request(String host,String path,JSONObject data,String expected,String token)throws Exception {
        HttpsURLConnection con=connection(host,path,expected);
        try{
            if(token!=null)con.setRequestProperty("Authorization","Bearer "+token);
            if(data!=null){con.setRequestMethod("POST");con.setRequestProperty("Content-Type","application/json");con.setDoOutput(true);
                try(OutputStream out=con.getOutputStream()){out.write(data.toString().getBytes("UTF-8"));}}
            int code=con.getResponseCode();
            if(expected==null){JSONObject cert=new JSONObject();cert.put("pin",hash((X509Certificate)con.getServerCertificates()[0]));return cert;}
            try(InputStream stream=code<400?con.getInputStream():con.getErrorStream()){
                if(stream==null)throw new IOException("PC antwortet mit "+code);
                ByteArrayOutputStream bytes=new ByteArrayOutputStream();byte[] buffer=new byte[4096];int n;
                while((n=stream.read(buffer))!=-1){if(bytes.size()+n>4194304)throw new IOException("Antwort zu groß");bytes.write(buffer,0,n);}
                JSONObject body=new JSONObject(bytes.toString("UTF-8"));
                if(code>=400)throw new IOException(body.optString("error","PC-Verwaltung nicht erreichbar"));return body;
            }
        }finally{con.disconnect();}
    }
    void emit(JSONObject state){if(!closed)home.console.web.evaluateJavascript("controlState("+state.toString()+")",null);}
    void fail(String text){
        JSONObject o=new JSONObject();try{o.put("error",text);o.put("paired",prefs().contains("token"));}catch(Exception ignored){}
        emit(o);
    }
    void pair(){
        String host=address();if(host==null){fail("PC ist offline. Zuerst mit Apollo koppeln.");return;}
        io.execute(()->{try{
            String pin=request(host,"/ping",null,null,null).getString("pin");
            home.host.runOnUiThread(()->{
                if(closed)return;
                EditText code=new EditText(home.host);code.setInputType(2);code.setHint("Sechsstelliger TV-Code");
                String shortPin=pin.substring(0,4)+" "+pin.substring(4,8)+" "+pin.substring(8,12);
                new AlertDialog.Builder(home.host).setTitle("PC-Verwaltung koppeln").setMessage("In Dolos-PC „TV-Verwaltung koppeln“ öffnen. Prüfzeichen vergleichen: "+shortPin)
                    .setView(code).setNegativeButton("Abbrechen",null).setPositiveButton("Verbinden",(d,w)->{
                        String input=code.getText().toString().trim();
                        io.execute(()->{try{String token=request(host,"/pair",new JSONObject().put("pin",input),pin,null).getString("token");
                            prefs().edit().putString("cert",pin).putString("token",token).apply();home.host.runOnUiThread(()->run("status","",""));}
                            catch(Exception e){home.host.runOnUiThread(()->fail("Kopplung fehlgeschlagen. Code und Prüfzeichen kontrollieren."));}});
                    }).show();
            });
        }catch(Exception e){home.host.runOnUiThread(()->fail("Verwaltung unerreichbar. Dolos-PC öffnen und die Heimnetz-Freigabe prüfen."));}});
    }
    void run(String action,String key,String name){run(action,key,name,null);}
    void run(String action,String key,String name,String drive){
        if(closed)return;
        if(action.equals("pair")){pair();return;}
        boolean polling=action.equals("status")||action.equals("transfers");
        if(polling&&busy)return;
        String host=address(),pin=prefs().getString("cert",null),token=prefs().getString("token",null);
        if(pin==null||token==null){fail("PC-Verwaltung noch nicht gekoppelt.");return;}
        if(host==null){fail("Die PC-Adresse wird noch ermittelt. Verbindung erneut prüfen.");return;}
        busy=true;io.execute(()->{
            try{
                if(action.equals("power")||action.equals("sleep")){
                    request(host,"/"+action,new JSONObject(),pin,token);
                    home.host.runOnUiThread(()->{if(!closed)ConsoleBoot.sequence(home.host,true,home.host::finishAffinity);});return;
                }
                if(action.equals("trophies")){
                    JSONObject result=request(host,"/trophies/"+key,null,pin,token);
                    home.host.runOnUiThread(()->{if(!closed)home.console.web.evaluateJavascript("trophyResult("+JSONObject.quote(key)+","+result+")",null);});return;
                }
                if(!polling && !action.equals("measure") && !action.equals("profileNames")){
                    request(host,"/queue",new JSONObject().put("action",action).put("id",key).put("name",name).put("drive",drive),pin,token);
                }
                JSONObject status=request(host,action.equals("transfers")&&snapshot.optInt("hostBuild")>=334?"/status/downloads":"/status",null,pin,token);status.put("paired",true);lastResponse=SystemClock.elapsedRealtime();
                String uuid=home.host.getIntent().getStringExtra(AppView.UUID_EXTRA);
                if(uuid!=null){
                    home.host.getSharedPreferences("studio",0).edit().putString("lastUuid",uuid).putString("lastHost",host).apply();
                    JSONObject art=status.optJSONObject("pcArtwork");
                    if(art!=null)prefs().edit().putString("artwork",art.toString()).apply();
                    JSONObject atlas=status.optJSONObject("coverAtlas");if(atlas!=null)prefs().edit().putString("atlas",atlas.toString()).apply();
                }
                int available=status.optInt("mediaCount",0);
                if(!BuildConfig.REMOTE_BUILD && available>0 && (mediaCount<0 || available-mediaCount>=12 || status.optJSONArray("catalog")!=null && available==status.optJSONArray("catalog").length()&&available!=mediaCount)){
                    JSONObject media=request(host,"/catalog-media",null,pin,token);mediaCount=available;
                    home.host.runOnUiThread(()->{if(!closed)home.console.web.evaluateJavascript("receiveMedia("+media+")",null);});
                }
                JSONObject names=status.optJSONObject("profileNames");
                if(names!=null){
                    SharedPreferences local=home.profiles();
                    for(int i=0;i<4;i++){
                        String pending=prefs().getString("pendingName"+i,null);
                        String cached=local.getString("name"+i,null);
                        if(pending!=null || (!names.has(""+i)&&cached!=null)){
                            String intended=pending!=null?pending:cached;
                            names=request(host,"/profiles",new JSONObject().put("slot",i).put("name",intended).put("seed",pending==null),pin,token);
                            if(intended.equals(prefs().getString("pendingName"+i,null)))prefs().edit().remove("pendingName"+i).apply();
                        }
                    }
                    for(int i=0;i<4;i++)if(names.has(""+i)&&!prefs().contains("pendingName"+i))
                        local.edit().putString("name"+i,names.getString(""+i)).apply();
                }
                if(action.equals("measure")){
                    long sum=0,min=Long.MAX_VALUE,max=0;int received=0;
                    for(int i=0;i<5;i++){long before=SystemClock.elapsedRealtime();try{request(host,"/ping",null,pin,token);
                        long ms=SystemClock.elapsedRealtime()-before;min=Math.min(min,ms);max=Math.max(max,ms);sum+=ms;received++;}catch(Exception ignored){}}
                    status.put("measurement",new JSONObject().put("received",received).put("mean",received==0?0:sum/received).put("spread",received==0?0:max-min));
                }
                home.host.runOnUiThread(()->{if(closed)return;snapshot=status;
                    org.json.JSONArray live=status.optJSONArray("catalog");
                    if(live!=null && !live.toString().equals(home.console.liveRows.toString())){home.console.liveRows=live;home.console.update();}
                    if(namesChanged(status))home.console.update();emit(status);});
            }catch(Exception e){home.host.runOnUiThread(()->fail(e instanceof IOException && e.getMessage()!=null && e.getMessage().length()<100?e.getMessage():"Keine Verbindung zur PC-Verwaltung."));}
            finally{busy=false;}
        });
    }
    void play(AppView.AppObject game){
        if(!prefs().contains("token")){
            Toast.makeText(home.host,"Zuerst die PC-Verwaltung koppeln.",Toast.LENGTH_SHORT).show();pair();return;
        }
        String id=Catalog.steamId(game.toString());
        final int profile=home.profile;
        final boolean direct=home.console.virtualAppId!=0&&snapshot.has("directProfiles")&&id.matches("[0-9]{1,10}");
        org.json.JSONArray supported=snapshot.optJSONArray(direct?"directProfiles":"profileLaunch");
        final boolean isolated=profile!=0&&(direct||home.console.liveAppId!=0)&&supported!=null&&containsId(supported,id);
        if(profile!=0&&!isolated){
            String alias=home.prefix(home.profile)+home.displayName(game);
            for(int i=0;home.library!=null&&i<home.library.getCount();i++){
                AppView.AppObject candidate=(AppView.AppObject)home.library.getItem(i);
                if(alias.equals(candidate.toString())){home.actions.play(candidate);return;}
            }
            ConsoleDock.show(home.host,"Eigenen Spielstand einrichten",new String[]{"Ordner auswählen","Zurück"},i->{if(i==0)createSavePath(id);});
            return;
        }
        if(id.isEmpty()||id.length()>10){home.actions.play(game);return;}
        String host=address();
        if(host==null){fail("PC-Adresse noch nicht verfügbar.");return;}
        io.execute(()->{try{
            JSONObject status=request(host,"/status",null,prefs().getString("cert",null),prefs().getString("token",null));
            JSONObject apps=status.optJSONObject("apps");JSONObject g=apps==null?null:apps.optJSONObject(id);
            JSONObject active=status.optJSONObject("activeGame");
            if(active!=null&&(!id.equals(active.optString("id"))||active.optInt("profile")!=profile)){
                home.host.runOnUiThread(()->ConsoleDock.show(home.host,active.optString("name")+" beenden und "+home.displayName(game)+" starten?",new String[]{"Zurück","Spiel wechseln"},index->{
                    if(index!=1)return;
                    io.execute(()->{try{
                        String pin=prefs().getString("cert",null),token=prefs().getString("token",null);
                        request(host,"/end-active",active,pin,token);
                        for(int i=0;i<48;i++){
                            if(!request(host,"/foreground/"+active.getString("id"),null,pin,token).optBoolean("running",true)){
                                home.host.runOnUiThread(()->{if(!closed&&home.profile==profile)play(game);});return;
                            }
                            Thread.sleep(400);
                        }
                        throw new IOException("Das vorige Spiel wartet noch auf das Beenden.");
                    }catch(Exception e){home.host.runOnUiThread(()->fail(e.getMessage()));}});
                }));return;
            }
            if(apps==null)throw new IOException("PC liest die Spieleliste.");
            if(!direct && g!=null && "installed".equals(g.optString("state")) && (isolated||home.console.liveAppId==game.app.getAppId())){
                if(home.console.liveRunning)throw new IOException("Aktive Sitzung im Kontrollzentrum beenden und erneut starten.");
                request(host,"/select",new JSONObject().put("id",id).put("profile",profile),prefs().getString("cert",null),prefs().getString("token",null));
            }
            home.host.runOnUiThread(()->{if(closed)return;
                if(profile!=home.profile)return;
                if(g!=null&&"installed".equals(g.optString("state")))home.actions.play(direct||isolated?new AppView.AppObject(new com.limelight.nvstream.http.NvApp(game.toString(),direct?home.console.virtualAppId:home.console.liveAppId,false)):game);
                else {home.console.web.evaluateJavascript("selectInstallDrive(items.find(g=>g.steamId==="+JSONObject.quote(id)+"))",null);}});
        }catch(Exception e){home.host.runOnUiThread(()->{if(!closed){home.console.web.evaluateJavascript("manage('Verbindung')",null);fail(e instanceof IOException && e.getMessage()!=null?e.getMessage():"PC-Verwaltung nicht erreichbar.");}});}});
    }
    private static boolean containsId(org.json.JSONArray ids,String id){if(ids==null)return false;for(int i=0;i<ids.length();i++)if(id.equals(ids.optString(i)))return true;return false;}
    void createSavePath(String id){
        int slot=home.profile;
        if(slot==0){ConsoleDock.show(home.host,"Das Standardprofil nutzt den vorhandenen Spielstand.",new String[]{"Zurück"},i->{});return;}
        String host=address();
        if(id.isEmpty())return;
        io.execute(()->{try{
            String pin=prefs().getString("cert",null),token=prefs().getString("token",null);
            JSONObject body=new JSONObject().put("id",id).put("slot",slot);
            if(containsId(snapshot.optJSONArray("directProfiles"),id)){finishSaveSetup(host,body);return;}
            org.json.JSONArray paths=request(host,"/save-candidates",body,pin,token).getJSONArray("paths");
            if(paths.length()==0)throw new IOException("Kein eigener lokaler Speicherordner erkannt. Das Spiel im Standardprofil einmal speichern.");
            String[] labels=new String[paths.length()+1];for(int i=0;i<paths.length();i++)labels[i]=paths.getString(i);
            labels[paths.length()]="Zurück";
            home.host.runOnUiThread(()->ConsoleDock.show(home.host,"Spielstandordner für "+home.profileName(slot)+" auswählen",labels,i->{
                if(i<paths.length()&&home.profile==slot)io.execute(()->{try{finishSaveSetup(host,body.put("path",labels[i]));}catch(Exception e){home.host.runOnUiThread(()->fail(e.getMessage()));}});
            }));
        }catch(Exception e){home.host.runOnUiThread(()->fail(e.getMessage()));}});
    }
    private void finishSaveSetup(String host,JSONObject body)throws Exception{
        request(host,"/profile-folder",body,prefs().getString("cert",null),prefs().getString("token",null));
        home.host.runOnUiThread(()->{run("status","","");ConsoleDock.show(home.host,"Eigener Spielstand eingerichtet",new String[]{"Fertig"},i->{});});
    }
    private String lastDisplayedProfile="";
    private boolean namesChanged(JSONObject ignored){
        String label=home.profileName(home.profile);
        if(label.equals(lastDisplayedProfile))return false;
        lastDisplayedProfile=label;return true;
    }
    void close(){closed=true;io.shutdownNow();}
}
