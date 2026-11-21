package com.limelight;

import android.app.Dialog;
import android.net.Uri;
import android.view.KeyEvent;
import android.webkit.*;
import java.io.*;
import java.util.*;
import java.util.regex.*;
import org.json.*;

/** Local storefront. Only IDs advertised by the paired host can be launched. */
final class Catalog {
    private static final Pattern TAG=Pattern.compile(" \\[AC:(\\d+):(installed|owned|cached|shortcut|family)\\]$");
    private static final String ORIGIN="https://aster.invalid/";
    static String title(String raw) { return TAG.matcher(raw).replaceFirst(""); }
    static String state(String raw) {
        Matcher match=TAG.matcher(raw);
        return match.find()?match.group(2):"host";
    }
    static String steamId(String raw) {
        Matcher match=TAG.matcher(raw);return match.find()?match.group(1):"";
    }
    static boolean remote(String raw) {
        return state(raw).equals("owned") || state(raw).equals("cached") || state(raw).equals("family");
    }
    final ConsoleHome home;
    final WebView web;
    boolean ready;
    String last="";
    int virtualAppId;
    int liveAppId;
    boolean liveRunning;
    JSONArray liveRows=new JSONArray();
    final Map<String,AppView.AppObject> entries=new java.util.concurrent.ConcurrentHashMap<>();
    final Map<String,AppView.AppObject> removers=new HashMap<>();
    void update(){
        if(!ready)return;
        entries.clear();removers.clear();virtualAppId=0;liveAppId=0;liveRunning=false;Set<String> seen=new HashSet<>();
        JSONArray data=new JSONArray();
        String uuid=home.host.getIntent().getStringExtra(AppView.UUID_EXTRA);
        Set<String> hidden=home.hiddenTiles(),pinned=home.extraPins();
        for(int i=0;home.library!=null && i<home.library.getCount();i++){
            AppView.AppObject g=(AppView.AppObject)home.library.getItem(i);
            if(g.toString().matches("\\[AC-REMOVE:[0-9]+\\]"))removers.put(g.toString().substring(11,g.toString().length()-1),g);
        }
        for(int i=0;home.library!=null && i<home.library.getCount();i++){
            AppView.AppObject g=(AppView.AppObject)home.library.getItem(i);
            if("Virtual Display".equalsIgnoreCase(g.toString()))virtualAppId=g.app.getAppId();
            if("[Dolos Live]".equals(g.toString())){liveAppId=g.app.getAppId();liveRunning=g.isRunning;continue;}
            if(!home.belongsToProfile(g)) continue;
            seen.add(steamId(g.toString()));
            String id=String.valueOf(g.app.getAppId());
            entries.put(id,g);
            try {
                JSONObject row=new JSONObject();
                row.put("running",g.isRunning);row.put("steamId",steamId(g.toString()));row.put("id",id);row.put("name",home.displayName(g));row.put("state",state(g.toString()));
                row.put("removable",removers.containsKey(steamId(g.toString())));row.put("pinned",home.onShelf(g,hidden,pinned));row.put("art",ORIGIN+"art/"+id);
                data.put(row);
            } catch(JSONException e){throw new IllegalStateException(e);}
        }
        if(liveAppId!=0)for(int i=0;i<liveRows.length();i++)try{
            JSONObject r=liveRows.getJSONObject(i);String sid=r.getString("id"),state=r.getString("state");
            if(!sid.matches("[0-9]{1,10}")||!seen.add(sid)||!Arrays.asList("installed","cached","owned","family").contains(state))continue;
            String id="s"+sid,name=r.getString("name");
            AppView.AppObject g=new AppView.AppObject(new com.limelight.nvstream.http.NvApp(name+" [AC:"+sid+":"+state+"]",liveAppId,false));
            entries.put(id,g);
            data.put(new JSONObject().put("id",id).put("name",name).put("steamId",sid).put("state",state)
                .put("art","https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/"+sid+"/library_600x900.jpg")
                .put("pinned",home.onShelf(g,hidden,pinned)).put("removable",state.equals("installed")));
        }catch(JSONException ignored){}
        android.content.SharedPreferences history=home.host.getSharedPreferences("dolos-history."+uuid+"."+home.profile,0);
        for(int i=0;i<data.length();i++)try{
            JSONObject row=data.getJSONObject(i);String sid=row.optString("steamId");
            AppView.AppObject game=entries.get(row.getString("id"));
            row.put("lastPlayed",history.getLong(sid.isEmpty()?game.toString():sid,0));
        }catch(JSONException ignored){}
        String args=data.toString()+","+JSONObject.quote(home.profileName(home.profile))+","+com.limelight.preferences.ProfileSettings.group(home.host,"console").getBoolean("sound",true)+","+JSONObject.quote(home.profile==0 && uuid!=null?uuid+".0":"");
        if(!last.equals(args)){last=args;web.evaluateJavascript("loadCatalog("+args+")",done->{
            if(!BuildConfig.REMOTE_BUILD&&home.library!=null&&home.host instanceof AppView){
                AppView activity=(AppView)home.host;
                if(android.os.Build.VERSION.SDK_INT>=23)web.postVisualStateCallback(0,new WebView.VisualStateCallback(){
                    public void onComplete(long requestId){activity.waitForLibraryArt();}
                });else web.postOnAnimation(activity::waitForLibraryArt);
            }
        });if(home.link.prefs().contains("token"))home.link.run("status","","");}
    }
    private String barState="";
    void updateBar(){
        if(!ready)return;
        int bars=-1;String label="Offline";
        try{
            android.net.ConnectivityManager cm=(android.net.ConnectivityManager)home.host.getSystemService(android.content.Context.CONNECTIVITY_SERVICE);
            android.net.NetworkInfo net=cm.getActiveNetworkInfo();
            if(net!=null&&net.isConnected()){
                label=net.getType()==android.net.ConnectivityManager.TYPE_ETHERNET?"LAN":"Netzwerk";
                if(net.getType()==android.net.ConnectivityManager.TYPE_WIFI){
                    android.net.wifi.WifiManager wifi=(android.net.wifi.WifiManager)home.host.getApplicationContext().getSystemService(android.content.Context.WIFI_SERVICE);
                    int rssi=wifi.getConnectionInfo().getRssi();
                    if(rssi>-127)bars=android.net.wifi.WifiManager.calculateSignalLevel(rssi,5);
                    label=bars<0?"WLAN":"WLAN · "+bars+" von 4";
                }
            }
        }catch(RuntimeException ignored){label="Netzwerk";}
        boolean pad=ControllerPairing.connected()!=null;
        String script="systemBar("+JSONObject.quote(label)+","+bars+","+pad+")";
        if(!barState.equals(script)){barState=script;web.evaluateJavascript(script,null);}
    }
    void applyTheme(){
        boolean controller=ControllerPairing.connected()!=null;
        web.evaluateJavascript("window.tvInput="+ConsoleDock.isTV(home.host)+";if(window.tvInput)document.getElementById('pairPad').hidden="+(controller||!ConsoleHome.appearance(home.host).getBoolean("padPrompt",true)),null);
        boolean enhanced="enhanced".equals(ConsoleHome.appearance(home.host).getString("theme","normal"));
        android.content.SharedPreferences settings=ConsoleHome.appearance(home.host);
        web.evaluateJavascript("window.tvTrailerAudio="+(!BuildConfig.REMOTE_BUILD&&settings.getBoolean("trailerAudio",true)),null);
        web.evaluateJavascript("setHomeDetails({time:"+settings.getBoolean("time",false)+",status:"+settings.getBoolean("status",false)+",recent:"+settings.getBoolean("recent",false)+"})",null);
        web.evaluateJavascript("document.body.classList.toggle('enhanced',"+enhanced+")",null);
    }
    Catalog(ConsoleHome owner){
        home=owner;web=new WebView(home.host);
        web.getSettings().setJavaScriptEnabled(true);web.getSettings().setMediaPlaybackRequiresUserGesture(false);web.getSettings().setDomStorageEnabled(true);
        web.getSettings().setAllowFileAccess(false);web.getSettings().setAllowContentAccess(false);
        web.setBackgroundColor(0xff10141e);
        web.setWebViewClient(new WebViewClient(){
            @Override public WebResourceResponse shouldInterceptRequest(WebView view,WebResourceRequest request){
                Uri uri=request.getUrl();
                String cdn=uri.getHost(),mediaPath=uri.getPath();
                if("https".equals(uri.getScheme()) && cdn!=null &&
                   cdn.endsWith(".steamstatic.com") && mediaPath!=null && mediaPath.matches("/(?:store_item_assets/steam/apps|steam/apps)/.+\\.(?i:jpg|jpeg|png|webp)")){
                    try{return RemoteMedia.fetch(home.host,uri.toString(),false);}
                    catch(IOException e){return new WebResourceResponse("text/plain","UTF-8",404,"Unavailable",Collections.emptyMap(),new ByteArrayInputStream(new byte[0]));}
                }
                if("https".equals(uri.getScheme()) && cdn!=null && cdn.endsWith(".steamstatic.com") && mediaPath!=null &&
                    (mediaPath.startsWith("/store_trailers/")||mediaPath.startsWith("/store_item_assets/steam/apps/")||mediaPath.startsWith("/steam/apps/")))return null;
                if("https".equals(uri.getScheme()) && "shared.fastly.steamstatic.com".equals(uri.getHost()) && uri.getPath()!=null && uri.getPath().matches("/store_item_assets/steam/apps/[0-9]+/(library_hero|library_600x900|logo)\\.(jpg|png)"))return null;
                if("https".equals(uri.getScheme()) && "aster.invalid".equals(uri.getHost())){
                    String path=uri.getPath();
                    String uuid=home.host.getIntent().getStringExtra(AppView.UUID_EXTRA);
                    try{
                        if(path!=null && path.matches("/artwork/[0-9]{1,10}/(cover|hero|atlas)/[0-9]{1,14}")&&uuid!=null){
                            return RemoteMedia.hostArt(home.host,uuid,path);
                        }
                        if(path!=null && path.matches("/metadata/[0-9]{1,10}")){
                            java.net.URL url=new java.net.URL("https://store.steampowered.com/api/appdetails?cc=de&l=german&appids="+uri.getLastPathSegment());
                            return RemoteMedia.fetch(home.host,url.toString(),true);
                        }
                        if(path!=null && path.startsWith("/art/")){
                            String id=uri.getLastPathSegment();
                            if(entries.containsKey(id) && uuid!=null && uuid.matches("[a-zA-Z0-9-]+")){
                                File file=new File(new File(new File(home.host.getCacheDir(),"boxart"),uuid),id+".png");
                                if(file.isFile())return new WebResourceResponse("image/png",null,new FileInputStream(file));
                                InputStream stream=home.library.openCatalogCover(entries.get(id));
                                if(stream!=null)return new WebResourceResponse("image/png",null,stream);
                            }
                        }
                        if("/enhanced.jpg".equals(path))return new WebResourceResponse("image/jpeg",null,home.host.getAssets().open("catalog/enhanced.jpg"));
                        if("/atelier.png".equals(path))return new WebResourceResponse("image/png",null,home.host.getAssets().open("catalog/atelier.png"));
                        if("/seal.svg".equals(path))return new WebResourceResponse("image/svg+xml","UTF-8",home.host.getAssets().open("catalog/seal.svg"));
                        if((BuildConfig.REMOTE_BUILD && "/remote-media.js".equals(path))||"/hls-light.js".equals(path)||"/store-media.js".equals(path)||"/index.html".equals(path)||"/catalog.css".equals(path)||"/tv-keyboard.js".equals(path)||"/catalog.js".equals(path)||"/motion.js".equals(path)||"/manage.js".equals(path)){
                            return new WebResourceResponse(path.endsWith("js")?"application/javascript":path.endsWith("css")?"text/css":"text/html","UTF-8",
                                home.host.getAssets().open("catalog"+path));
                        }
                    }catch(IOException ignored){}
                }
                return new WebResourceResponse("text/plain","UTF-8",404,"Missing",Collections.emptyMap(),new ByteArrayInputStream(new byte[0]));
            }
            @Override public void onPageFinished(WebView view,String url){
                if((ORIGIN+"index.html").equals(url)){ready=true;barState="";updateBar();applyTheme();
                    if(!BuildConfig.REMOTE_BUILD)web.evaluateJavascript("restoreArtwork("+JSONObject.quote(home.host.getIntent().getStringExtra(AppView.UUID_EXTRA))+")",null);
                    update();}
            }
            @Override public boolean shouldOverrideUrlLoading(WebView v,String url){
                Uri u=Uri.parse(url);
                if(!"aster".equals(u.getScheme()))return true;
                AppView.AppObject g=entries.get(u.getLastPathSegment());
                String action=u.getHost();
                if(("filmaudio".equals(action)||"menuaudio".equals(action))&&home.host instanceof AppView)((AppView)home.host).setFilmAudio("filmaudio".equals(action));
                else if("close".equals(action))home.host.finish();
                else if("studio".equals(action))ConsoleStudio.open(home.host,u.getLastPathSegment(),home.host.getIntent().getStringExtra(AppView.UUID_EXTRA),home.host.getSharedPreferences("studio",0).getString("lastHost",null));
                else if("settings".equals(action))ConsoleStudio.open(home.host,"video",home.host.getIntent().getStringExtra(AppView.UUID_EXTRA),home.host.getSharedPreferences("studio",0).getString("lastHost",null));
                else if("wifi".equals(action)){
                    try{home.host.startActivity(new android.content.Intent(android.provider.Settings.ACTION_WIFI_SETTINGS));}
                    catch(android.content.ActivityNotFoundException e){home.host.startActivity(new android.content.Intent(android.provider.Settings.ACTION_SETTINGS));}
                }
                else if("bluetooth".equals(action))ControllerPairing.show(home.host);
                else if("profile".equals(action))home.chooseProfile();
                else if("power".equals(action))home.power();
                else if("quit".equals(action))home.actions.quit();
                else if("setup".equals(action))ConsoleBoot.setup(home.host);
                else if("wake".equals(action))((AppView)home.host).wakeHost();
                else if(Arrays.asList("pair","status","transfers","measure","pause","resume").contains(action))home.link.run(action,"","");
                else if(Arrays.asList("confirm","cancel","dismiss","retry","downloadfirst","downloadcancel","downloadpause").contains(action))home.link.run(action,u.getLastPathSegment(),"");
                else if(g!=null && "trophies".equals(action))home.link.run("trophies",steamId(g.toString()),"");
                else if(g!=null && "savepath".equals(action))home.link.createSavePath(steamId(g.toString()));
                else if(g!=null && "play".equals(action)){home.link.play(g);}
                else if(g!=null && ("install".equals(action)||"remove".equals(action))){
                    String id=steamId(g.toString());if(!id.isEmpty()){
                        if("remove".equals(action))new android.app.AlertDialog.Builder(home.host).setTitle(home.displayName(g)).setMessage("Spiel auf dem PC deinstallieren?")
                            .setNegativeButton("Abbrechen",null).setPositiveButton("Deinstallieren",(d,w)->home.link.run(action,id,home.displayName(g))).show();
                        else home.link.run(action,id,home.displayName(g),u.getQueryParameter("drive"));
                    }
                }
                else if(g!=null && ("pin".equals(action)||"unpin".equals(action))){
                    home.setPinned(g,"pin".equals(action));
                }
                return true;
            }
        });
        StickNavigation.attach(web);
        web.setOnKeyListener((v,key,event)->{
            if(key==KeyEvent.KEYCODE_BUTTON_A || key==KeyEvent.KEYCODE_DPAD_CENTER){
                if(event.getAction()==KeyEvent.ACTION_UP)web.evaluateJavascript(
                    "document.activeElement.tagName==='INPUT'",isInput->{
                    if("true".equals(isInput)){
                        android.view.inputmethod.InputMethodManager ime=(android.view.inputmethod.InputMethodManager)home.host.getSystemService(android.content.Context.INPUT_METHOD_SERVICE);
                        if(ConsoleDock.isTV(home.host))web.evaluateJavascript("openTvKeyboard(document.activeElement)",null);else ime.showSoftInput(web,android.view.inputmethod.InputMethodManager.SHOW_IMPLICIT);
                    } else web.evaluateJavascript("document.activeElement.click()",null);
                });
                return true;
            }
            if(key==KeyEvent.KEYCODE_BUTTON_L1||key==KeyEvent.KEYCODE_BUTTON_R1||key==KeyEvent.KEYCODE_BUTTON_L2||key==KeyEvent.KEYCODE_BUTTON_R2){
                if(event.getAction()==KeyEvent.ACTION_UP){
                    String route=key==KeyEvent.KEYCODE_BUTTON_L1?"home":key==KeyEvent.KEYCODE_BUTTON_R1?"store":key==KeyEvent.KEYCODE_BUTTON_R2?"next":"previous";
                    web.evaluateJavascript("shoulder('"+route+"')",null);
                }return true;
            }
            if(key==KeyEvent.KEYCODE_BUTTON_Y){if(event.getAction()==KeyEvent.ACTION_UP)web.evaluateJavascript("gameOptionsForFocus()",null);return true;}
            if(key==KeyEvent.KEYCODE_MENU || key==KeyEvent.KEYCODE_BUTTON_START || key==KeyEvent.KEYCODE_BUTTON_MODE){
                if(event.getAction()==KeyEvent.ACTION_UP)web.evaluateJavascript(key==KeyEvent.KEYCODE_BUTTON_MODE?"controls()":"gameOptionsForFocus()",null);return true;
            }
            if(key!=KeyEvent.KEYCODE_BACK && key!=KeyEvent.KEYCODE_BUTTON_B)return false;
            if(event.getAction()==KeyEvent.ACTION_UP)web.evaluateJavascript("back()",null);
            return true;
        });
        web.requestFocus();web.loadUrl(ORIGIN+"index.html");
    }
}
