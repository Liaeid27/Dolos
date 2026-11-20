package com.limelight;

import android.content.Context;
import android.content.SharedPreferences;
import com.limelight.nvstream.http.ComputerDetails;
import com.limelight.nvstream.wol.WakeOnLanSender;
import java.io.IOException;
import java.net.URL;
import java.net.HttpURLConnection;
import android.net.ConnectivityManager;
import android.net.NetworkCapabilities;
import android.net.Network;

final class RemoteWake {
    static boolean pi(String value){
        try{
            URL u=new URL(value);String[] parts=u.getHost().split("\\.");
            if(parts.length!=4||!parts[0].equals("100"))return false;
            for(String part:parts)if(!part.matches("[0-9]{1,3}")||Integer.parseInt(part)>255)return false;
            int network=Integer.parseInt(parts[1]);
            return network>=64&&network<=127&&"http".equals(u.getProtocol())&&u.getPort()>0&&"/api/wake".equals(u.getFile())&&u.getUserInfo()==null&&u.getRef()==null;
        }catch(Exception e){return false;}
    }
    static boolean valid(String address){
        if(pi(address))return true;
        try {
            URL url=new URL(address);
            return "https".equals(url.getProtocol()) && url.getHost().endsWith(".ts.net") && url.getUserInfo()==null && url.getQuery()==null && url.getRef()==null;
        } catch(Exception e){return false;}
    }
    static void send(Context context,ComputerDetails computer)throws IOException{
        if(!BuildConfig.REMOTE_BUILD){WakeOnLanSender.sendWolPacket(computer);return;}
        SharedPreferences prefs=context.getSharedPreferences("remote",0);
        String address=prefs.getString("wakeUrl",""),token=prefs.getString("wakeToken","");
        boolean existingPi=pi(address);
        if(!valid(address)||(!existingPi&&token.isEmpty()))throw new IOException("Weckdienst im Einrichtungsassistenten hinterlegen.");
        HttpURLConnection c;
        if(existingPi){
            if(android.os.Build.VERSION.SDK_INT<23)throw new IOException("Für diesen Weckdienst Android 6 oder neuer verwenden.");
            ConnectivityManager manager=(ConnectivityManager)context.getSystemService(Context.CONNECTIVITY_SERVICE);
            Network vpn=manager.getActiveNetwork();
            NetworkCapabilities caps=vpn==null?null:manager.getNetworkCapabilities(vpn);
            if(caps==null||!caps.hasTransport(NetworkCapabilities.TRANSPORT_VPN))throw new IOException("Tailscale auf dem Android-Gerät verbinden.");
            c=(HttpURLConnection)vpn.openConnection(new URL(address));
        }else c=(HttpURLConnection)new URL(address).openConnection();
        try{
            c.setConnectTimeout(4500);c.setReadTimeout(4500);c.setInstanceFollowRedirects(false);
            c.setRequestMethod("POST");if(!existingPi)c.setRequestProperty("Authorization","Bearer "+token);
            c.setDoOutput(true);c.setFixedLengthStreamingMode(0);c.getOutputStream().close();
            int status=c.getResponseCode();
            if(status<200||status>=300)throw new IOException("Weckdienst: HTTP "+status);
        }finally{c.disconnect();}
    }
}
