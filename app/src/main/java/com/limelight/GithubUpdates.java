package com.limelight;

import java.io.*;
import java.net.URL;
import javax.net.ssl.HttpsURLConnection;
import org.json.*;

final class GithubUpdates {
    private static final String PROJECT="Liaeid27/Dolos";
    static HttpsURLConnection open(String url)throws IOException{
        HttpsURLConnection conn=(HttpsURLConnection)new URL(url).openConnection();
        conn.setRequestProperty("User-Agent","Dolos-Updater");conn.setInstanceFollowRedirects(false);
        conn.setConnectTimeout(5000);conn.setReadTimeout(20000);return conn;
    }
    static JSONObject latest(boolean remote)throws IOException{
        HttpsURLConnection c=open("https://api.github.com/repos/"+PROJECT+"/releases/latest");
        try(InputStream in=c.getInputStream();ByteArrayOutputStream data=new ByteArrayOutputStream()){
            ConsoleStudio.copy(in,data,1024*1024);
            JSONObject release=new JSONObject(data.toString("UTF-8"));
            String tag=release.getString("tag_name");
            if(!tag.matches("build-[1-9][0-9]{0,8}"))throw new IOException("Unbekannte Release-Version");
            String file=remote?"Dolos-Remote.apk":"Dolos-TV.apk";
            JSONArray assets=release.getJSONArray("assets");
            for(int i=0;i<assets.length();i++){
                JSONObject asset=assets.getJSONObject(i);if(!file.equals(asset.optString("name")))continue;
                String url="https://github.com/"+PROJECT+"/releases/download/"+tag+"/"+file;
                String digest=asset.optString("digest","");
                if(!url.equals(asset.getString("browser_download_url"))||!digest.matches("sha256:[a-f0-9]{64}"))throw new IOException("Release-Prüfsumme fehlt");
                return new JSONObject().put("url",url).put("sha256",digest.substring(7)).put("size",asset.getLong("size")).put("version",Integer.parseInt(tag.substring(6)));
            }
            throw new IOException("APK fehlt im Release");
        }catch(JSONException e){throw new IOException("Release-Daten ungültig",e);}finally{c.disconnect();}
    }
    static HttpsURLConnection download(String url)throws IOException{
        for(int i=0;i<4;i++){
            URL target=new URL(url);String host=target.getHost();
            if(!"https".equals(target.getProtocol())||!(host.equals("github.com")||host.endsWith(".githubusercontent.com")))throw new IOException("Ungültiges Downloadziel");
            HttpsURLConnection c=open(url);int code=c.getResponseCode();
            if(code==200)return c;
            String next=c.getHeaderField("Location");c.disconnect();
            if(code<300||code>=400||next==null)throw new IOException("GitHub-Download fehlgeschlagen");
            url=new URL(target,next).toString();
        }
        throw new IOException("Zu viele Weiterleitungen");
    }
}
