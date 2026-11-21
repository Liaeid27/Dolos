package com.limelight;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.*;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.media.MediaMetadataRetriever;
import android.net.Uri;
import android.os.*;
import android.webkit.*;
import android.widget.VideoView;
import org.json.*;
import java.io.*;
import java.net.*;
import java.security.MessageDigest;
import java.util.*;
import java.util.concurrent.*;
import javax.net.ssl.HttpsURLConnection;

public class ConsoleStudio extends Activity {
    private static final String ORIGIN="https://studio.invalid/";
    static final String[] BUILTINS={"dolos","orbit","maske","stich","signet","portikus","helm","galerie"};
    static final ExecutorService transfers=Executors.newSingleThreadExecutor();
    private WebView web;
    private SharedPreferences prefs;
    private StudioPreferences stream;
    private android.widget.FrameLayout modelView;
    public void reloadStream(){
        stream=new StudioPreferences();getFragmentManager().beginTransaction().replace(modelView.getId(),stream,"controls").commitAllowingStateLoss();
        getFragmentManager().executePendingTransactions();sendOptions();
    }
    void sendOptions(){try{js("streamOptions("+stream.model()+")");}catch(Exception e){note(message(e));}}
    private boolean working;
    private static final String LOCAL_STUDIO="file:///android_asset/catalog/studio.html";

    static void open(Activity a,String section,String uuid,String host){
        Intent i=new Intent(a,ConsoleStudio.class).putExtra("section",section);
        if(uuid!=null && host!=null)a.getSharedPreferences("studio",0).edit().putString("lastUuid",uuid).putString("lastHost",host).apply();
        if(a instanceof AppView){i.putExtra("libraryHost",true);a.startActivityForResult(i,7323);}else a.startActivity(i);
    }
    static Uri film(Context c,String key,String mode){
        if(!("on".equals(mode)||"off".equals(mode)))return null;
        if(Arrays.asList(BUILTINS).contains(key)){
            int id=c.getResources().getIdentifier(key+"_"+mode,"raw",c.getPackageName());
            return id==0?null:Uri.parse("android.resource://"+c.getPackageName()+"/"+id);
        }
        if(key!=null&&key.matches("(deck|swap)_[a-zA-Z0-9_-]{1,100}")){
            File f=new File(c.getFilesDir(),key+".webm");
            if(f.isFile())return Uri.fromFile(f);
        }
        return null;
    }
    @Override public void onCreate(Bundle state){
        super.onCreate(state);getWindow().getDecorView().setSystemUiVisibility(5894);
        prefs=getSharedPreferences("studio",0);web=new WebView(this);android.widget.FrameLayout root=new android.widget.FrameLayout(this);
        modelView=new android.widget.FrameLayout(this);modelView.setId(0x00da1001);modelView.setVisibility(android.view.View.GONE);
        root.addView(modelView);root.addView(web);setContentView(root);
        stream=(StudioPreferences)getFragmentManager().findFragmentByTag("controls");
        web.setBackgroundColor(0xff101622);web.getSettings().setJavaScriptEnabled(true);
        web.getSettings().setAllowFileAccess(false);web.getSettings().setAllowContentAccess(false);
        web.setWebViewClient(new WebViewClient(){
            public boolean shouldOverrideUrlLoading(WebView v,String url){
                Uri u=Uri.parse(url);
                if(ORIGIN.concat("studio.html").equals(url)||LOCAL_STUDIO.equals(url))return false;
                if("studio".equals(u.getScheme()))try{action(u.getHost(),new JSONObject(u.getLastPathSegment()));}catch(Exception e){note(message(e));}
                return true;
            }
            public WebResourceResponse shouldInterceptRequest(WebView v,WebResourceRequest req){
                Uri u=req.getUrl();
                if("file".equals(u.getScheme()) && u.getPath()!=null && u.getPath().startsWith("/android_asset/catalog/"))return null;
                if("https".equals(u.getScheme())&&"cdn.steamdeckrepo.com".equals(u.getHost())&&u.getPath()!=null&&u.getPath().startsWith("/thumbnails/"))return null;
                if(ORIGIN.startsWith("https://"+u.getHost()+"/") && "https".equals(u.getScheme()))try{
                    String route=u.getPath();
                    if("/deck".equals(route)||"/swap".equals(route)){
                        boolean deck="/deck".equals(route);
                        String src=deck?"https://steamdeckrepo.com/api/posts/all":"https://api.github.com/repos/AutoMcG/steamdeck_tools/git/trees/HEAD?recursive=1";
                        HttpURLConnection con=connect(src);byte[] data;
                        try(InputStream in=con.getInputStream();ByteArrayOutputStream out=new ByteArrayOutputStream()){
                            copy(in,out,24*1024*1024);data=out.toByteArray();
                        }finally{con.disconnect();}
                        return new WebResourceResponse("application/json","UTF-8",200,"OK",Collections.singletonMap("Access-Control-Allow-Origin","*"),new ByteArrayInputStream(data));
                    }
                    if(route.matches("/still_[a-z]+_(on|off)\\.jpg"))return new WebResourceResponse("image/jpeg",null,getAssets().open("catalog"+route));
                    if(Arrays.asList("/tv-keyboard.js","/studio.html","/studio.css","/studio.js","/atelier.png","/enhanced.jpg").contains(route))
                        return new WebResourceResponse(route.endsWith(".js")?"application/javascript":route.endsWith(".css")?"text/css":route.endsWith(".html")?"text/html":route.endsWith(".jpg")?"image/jpeg":"image/png",null,getAssets().open("catalog"+route));
                }catch(Exception ignored){}
                return new WebResourceResponse("text/plain","UTF-8",404,"Unavailable",Collections.emptyMap(),new ByteArrayInputStream(new byte[0]));
            }
            @Override public void onReceivedError(WebView v,int code,String description,String failingUrl){
                if((ORIGIN+"studio.html").equals(failingUrl))v.post(()->v.loadUrl(LOCAL_STUDIO));
            }
            public void onPageFinished(WebView v,String url){if((ORIGIN+"studio.html").equals(url)||LOCAL_STUDIO.equals(url)){js("window.tvInput="+ConsoleDock.isTV(ConsoleStudio.this));sync();}}
        });
        StickNavigation.attach(web);web.loadUrl(ORIGIN+"studio.html");
    }
    private String asset(String name)throws IOException{
        try(InputStream in=getAssets().open("catalog/"+name);ByteArrayOutputStream out=new ByteArrayOutputStream()){
            copy(in,out,1024*1024);return out.toString("UTF-8");
        }
    }
    static HttpURLConnection connect(String url)throws IOException{
        HttpURLConnection c=(HttpURLConnection)new URL(url).openConnection();
        c.setInstanceFollowRedirects(false);c.setConnectTimeout(7000);c.setReadTimeout(20000);c.setRequestProperty("User-Agent","Dolos/322");
        if(url.startsWith("https://cdn.steamdeckrepo.com/"))c.setRequestProperty("Referer","https://steamdeckrepo.com/");
        return c;
    }
    static long copy(InputStream input,OutputStream out,long limit)throws IOException{
        long total=0;byte[] b=new byte[32768];int n;
        while((n=input.read(b))!=-1){total+=n;if(total>limit)throw new IOException("Datei überschreitet das Größenlimit.");out.write(b,0,n);}return total;
    }
    void js(String script){if(!isFinishing()&&!isDestroyed())web.evaluateJavascript(script,null);}
    void note(String text){js("notice("+JSONObject.quote(text)+")");}
    static String message(Exception e){return e.getMessage()==null?"Vorgang fehlgeschlagen.":e.getMessage();}
    void sync(){
        try{
            JSONObject d=new JSONObject().put("menuBinding",ConsoleHome.appearance(this).getInt("menuBinding",0)).put("faceLayout",ConsoleHome.appearance(this).getInt("faceLayout",0)).put("padPrompt",ConsoleHome.appearance(this).getBoolean("padPrompt",true)).put("tvEdition",!BuildConfig.REMOTE_BUILD).put("trailerAudio",ConsoleHome.appearance(this).getBoolean("trailerAudio",true)).put("on",ConsoleHome.appearance(this).getString("on","dolos")).put("off",ConsoleHome.appearance(this).getString("off","dolos")).put("theme",ConsoleHome.appearance(this).getString("theme","normal")).put("route",prefs.getString("route","")).put("time",ConsoleHome.appearance(this).getBoolean("time",false)).put("status",ConsoleHome.appearance(this).getBoolean("status",false)).put("recent",ConsoleHome.appearance(this).getBoolean("recent",false)).put("build",BuildConfig.VERSION_CODE).put("section",getIntent().getStringExtra("section")).put("connectedMenu",getIntent().getBooleanExtra("libraryHost",false));
            JSONArray files=new JSONArray();for(String k:prefs.getAll().keySet())if(k.startsWith("file.")&&film(this,k.substring(5),"on")!=null)files.put(new JSONObject(prefs.getString(k,"{}")));
            js("studioState("+d.put("files",files)+")");
        }catch(Exception e){note(message(e));}
    }
    static String source(JSONObject row)throws Exception{
        String url=row.getString("url"),key=row.getString("id");
        if(key.matches("deck_[A-Za-z0-9_-]{1,100}")&&url.matches("https://cdn\\.steamdeckrepo\\.com/videos/[A-Za-z0-9._-]+\\.webm")
            ||key.matches("swap_[A-Za-z0-9_-]{1,100}")&&url.matches("https://raw\\.githubusercontent\\.com/AutoMcG/steamdeck_tools/(HEAD|[a-f0-9]{40})/vidswap/vids/[A-Za-z0-9._-]+\\.webm"))return url;
        throw new IOException("Unbekannte Filmquelle.");
    }
    void action(String action,JSONObject row)throws Exception{
        String key=row.optString("id"),mode="off".equals(row.optString("mode"))?"off":"on";
        Uri local=film(this,key,mode);
        switch(action){
            case "close":finish();break;
            case "bluetooth":
                try{startActivity(new Intent(android.provider.Settings.ACTION_BLUETOOTH_SETTINGS));}
                catch(ActivityNotFoundException e){startActivity(new Intent(android.provider.Settings.ACTION_SETTINGS));}break;
            case "menuBinding":case "faceLayout":
                ConsoleHome.appearance(this).edit().putInt(action,(ConsoleHome.appearance(this).getInt(action,0)+1)%4).apply();sync();break;
            case "padPrompt":
                ConsoleHome.appearance(this).edit().putBoolean("padPrompt",!ConsoleHome.appearance(this).getBoolean("padPrompt",true)).apply();sync();break;
            case "consoleAction":
                if("setup".equals(key)){ConsoleBoot.setup(this);break;}
                if(getIntent().getBooleanExtra("libraryHost",false)&&Arrays.asList("storage","network","pair","profile","power").contains(key)){
                    setResult(RESULT_OK,new Intent().putExtra("destination",key));finish();
                }break;
            case "stream":if(stream==null)reloadStream();else sendOptions();break;
            case "option":if(stream!=null){stream.change(row);sendOptions();}break;
            case "homeinfo":String field=row.optString("id");if(Arrays.asList("time","recent","status","trailerAudio").contains(field))ConsoleHome.appearance(this).edit().putBoolean(field,!ConsoleHome.appearance(this).getBoolean(field,"trailerAudio".equals(field))).apply();sync();break;
            case "theme":ConsoleHome.appearance(this).edit().putString("theme","enhanced".equals(key)?key:"normal").apply();sync();break;
            case "apply":
                if(local==null&&!("aster".equals(key)&&"on".equals(mode)))throw new IOException("Bitte zuerst herunterladen.");
                ConsoleHome.appearance(this).edit().putString(mode,key).apply();sync();note("Animation angewendet.");break;
            case "delete":{
                if(!key.matches("(deck|swap)_[A-Za-z0-9_-]{1,100}"))return;
                new AlertDialog.Builder(this).setTitle("Download entfernen?").setMessage(row.optString("title")).setNegativeButton("Behalten",null).setPositiveButton("Entfernen",(dialog,which)->{
                    File f=new File(getFilesDir(),key+".webm");if(f.exists()&&!f.delete()){note("Datei konnte nicht entfernt werden.");return;}
                    prefs.edit().remove("file."+key).apply();
                    for(int i=0;i<4;i++){SharedPreferences owner=getSharedPreferences(i==0?"studio":"appearance."+i,0);
                        for(String slot:new String[]{"on","off"})if(key.equals(owner.getString(slot,"")))owner.edit().remove(slot).apply();}sync();note("Download entfernt.");
                }).show();break;
            }
            case "preview":{
                if("aster".equals(key)){ConsoleBoot.classic(this,()->{});break;}
                Uri uri=local!=null?local:Uri.parse(source(row));
                StudioPlayer.show(this,uri,row.optString("title"),row.optString("source"),()->note("Vorschau nicht abspielbar. Verbindung oder Videoformat prüfen."));break;
            }
            case "download":{
                String url=source(row);task(()->{
                    File tmp=File.createTempFile("film-",".part",getCacheDir());HttpURLConnection c=connect(url);
                    try{
                        try(InputStream in=c.getInputStream();OutputStream out=new FileOutputStream(tmp)){copy(in,out,128L*1024*1024);}
                        MediaMetadataRetriever probe=new MediaMetadataRetriever();
                        try{probe.setDataSource(tmp.getPath());if(probe.extractMetadata(MediaMetadataRetriever.METADATA_KEY_VIDEO_WIDTH)==null)throw new IOException("Kein abspielbares Video.");}finally{probe.release();}
                        if(!tmp.renameTo(new File(getFilesDir(),key+".webm")))throw new IOException("Speichern fehlgeschlagen.");
                        prefs.edit().putString("file."+key,row.toString()).commit();
                        return "Gespeichert. Die Animation kann jetzt angewendet werden.";
                    }finally{c.disconnect();tmp.delete();}
                },"Download läuft …");break;
            }
            case "check":case "install":update("install".equals(action));break;
        }
    }
    interface Job{String run()throws Exception;}
    void task(Job job,String status){
        if(working){note("Ein Vorgang läuft bereits.");return;}working=true;note(status);
        transfers.execute(()->{String result;try{result=job.run();}catch(Exception e){result=message(e);}
            final String text=result;runOnUiThread(()->{working=false;sync();note(text);});});
    }
    void update(boolean install){
        final String host=prefs.getString("lastHost",""),uuid=prefs.getString("lastUuid","");
        SharedPreferences link=getSharedPreferences("dolos-control-"+uuid,0);
        String pin=link.getString("cert",null),token=link.getString("token",null);
        task(()->{
            JSONObject latest;
            try{latest=GithubUpdates.latest(BuildConfig.REMOTE_BUILD);}
            catch(IOException e){
                if(host.isEmpty()||pin==null||token==null)throw new IOException("GitHub nicht erreichbar. Verbindung prüfen.");
                latest=ControlLink.request(host,(BuildConfig.REMOTE_BUILD?"/remote-updates/":"/updates/")+"latest",null,pin,token);
            }
            int version=latest.getInt("version");
            if(version<=BuildConfig.VERSION_CODE){runOnUiThread(()->js("available(0)"));return version==0?"Am PC wurde noch keine APK bereitgestellt.":"Dolos ist aktuell.";}
            if(!install){runOnUiThread(()->js("available("+version+")"));return "Build "+version+" ist verfügbar.";}
            String digest=latest.getString("sha256");long size=latest.getLong("size");
            if(!digest.matches("[a-f0-9]{64}")||size<1||size>256L*1024*1024)throw new IOException("Ungültige Updateinformationen.");
            File dir=new File(getCacheDir(),"releases");dir.mkdirs();File apk=new File(dir,digest+".apk");
            if(!apk.isFile()){
                HttpsURLConnection c;
                if(latest.has("url"))c=GithubUpdates.download(latest.getString("url"));
                else{c=ControlLink.connection(host,(BuildConfig.REMOTE_BUILD?"/remote-updates/":"/updates/")+digest,pin);c.setRequestProperty("Authorization","Bearer "+token);}
                File tmp=File.createTempFile("download-",".part",dir);
                try{
                    MessageDigest md=MessageDigest.getInstance("SHA-256");
                    try(InputStream in=new java.security.DigestInputStream(c.getInputStream(),md);OutputStream out=new FileOutputStream(tmp)){
                        if(copy(in,out,size)!=size)throw new IOException("Download unvollständig.");
                    }
                    StringBuilder hash=new StringBuilder();for(byte b:md.digest())hash.append(String.format(Locale.US,"%02x",b&255));
                    if(!digest.contentEquals(hash)||!tmp.renameTo(apk))throw new IOException("Update konnte nicht verifiziert werden.");
                }finally{c.disconnect();tmp.delete();}
            }
            PackageManager pm=getPackageManager();PackageInfo archive=pm.getPackageArchiveInfo(apk.getPath(),PackageManager.GET_SIGNATURES),self=pm.getPackageInfo(getPackageName(),PackageManager.GET_SIGNATURES);
            if(archive==null||!getPackageName().equals(archive.packageName)||archive.versionCode!=version||self.signatures==null||self.signatures.length==0||!Arrays.equals(self.signatures,archive.signatures))throw new IOException("Paket, Version oder Signatur passt nicht zu Dolos.");
            runOnUiThread(()->{
                try{
                    if(Build.VERSION.SDK_INT>=26&&!pm.canRequestPackageInstalls()){
                        startActivity(new Intent(android.provider.Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,Uri.parse("package:"+getPackageName())));return;
                    }
                    Uri uri=Uri.parse("content://"+getPackageName()+".updates/"+digest+".apk");
                    startActivity(new Intent(Intent.ACTION_VIEW).setDataAndType(uri,"application/vnd.android.package-archive").addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION));
                }catch(ActivityNotFoundException e){note("Android bietet auf diesem Gerät keinen Paketinstaller an.");}
            });return "Android-Installation bestätigen. Nach einer Freigabe erneut auf Installieren drücken.";
        },install?"Update wird geprüft und heruntergeladen …":"GitHub-Releases werden geprüft …");
    }
    @Override public boolean dispatchKeyEvent(android.view.KeyEvent e){
        int shoulder=e.getKeyCode();
        if(shoulder==android.view.KeyEvent.KEYCODE_BUTTON_L1||shoulder==android.view.KeyEvent.KEYCODE_BUTTON_R1){
            if(e.getAction()==android.view.KeyEvent.ACTION_UP)js("nextCategory("+ (shoulder==android.view.KeyEvent.KEYCODE_BUTTON_R1?1:-1)+")");
            return true;
        }
        int k=e.getKeyCode();
        if(web.hasFocus()&&(k==android.view.KeyEvent.KEYCODE_BUTTON_A||k==android.view.KeyEvent.KEYCODE_DPAD_CENTER)){
            if(e.getAction()==android.view.KeyEvent.ACTION_UP)web.evaluateJavascript("document.activeElement.tagName==='INPUT'",input->{
                if("true".equals(input)){if(ConsoleDock.isTV(this))js("openTvKeyboard(document.activeElement)");else ((android.view.inputmethod.InputMethodManager)getSystemService(INPUT_METHOD_SERVICE)).showSoftInput(web,0);}
                else js("document.activeElement.click()");
            });return true;
        }
        if(k==android.view.KeyEvent.KEYCODE_BUTTON_B){if(e.getAction()==android.view.KeyEvent.ACTION_UP)onBackPressed();return true;}
        return super.dispatchKeyEvent(e);
    }
    @Override public void onBackPressed(){js("goBack()");}
}
