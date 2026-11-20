package com.limelight.utils;

import android.content.Context;
import android.net.*;
import android.os.Build;
import java.net.InetAddress;

/** Select a numeric, on-link PC destination on a physical Android network. */
public final class HomeNetwork {
    public final Network network;
    public final String address,transport;
    private HomeNetwork(Network n,String a,String t){network=n;address=a;transport=t;}
    public static boolean sameSubnet(byte[] local,byte[] target,int prefix){
        if(local.length!=target.length||prefix<=0||prefix>local.length*8)return false;
        for(int bit=0;bit<prefix;bit++)if(((local[bit/8]^target[bit/8])&(128>>(bit%8)))!=0)return false;
        return true;
    }
    private static InetAddress numeric(String value){
        if(value==null||value.isEmpty()||!(value.matches("[0-9.]+")||value.contains(":")))return null;
        try{
            InetAddress ip=InetAddress.getByName(value);
            byte[] b=ip.getAddress();
            if(ip.isAnyLocalAddress()||ip.isLoopbackAddress()||ip.isMulticastAddress())return null;
            if(b.length==4&&(b[0]&255)==100&&((b[1]&192)==64))return null;
            if(b.length==16&&value.toLowerCase(java.util.Locale.ROOT).startsWith("fd7a:115c:a1e0:"))return null;
            return ip;
        }catch(Exception e){return null;}
    }
    public static HomeNetwork select(Context ctx,String... hosts){
        if(Build.VERSION.SDK_INT<21)return null;
        ConnectivityManager cm=(ConnectivityManager)ctx.getSystemService(Context.CONNECTIVITY_SERVICE);
        for(String host:hosts){
            InetAddress target=numeric(host);if(target==null)continue;
            for(Network n:cm.getAllNetworks()){
                NetworkCapabilities cap=cm.getNetworkCapabilities(n);LinkProperties lp=cm.getLinkProperties(n);
                if(cap==null||lp==null||!cap.hasCapability(NetworkCapabilities.NET_CAPABILITY_NOT_VPN)||cap.hasTransport(NetworkCapabilities.TRANSPORT_VPN))continue;
                boolean cable=cap.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET);
                if(!cable&&!cap.hasTransport(NetworkCapabilities.TRANSPORT_WIFI))continue;
                for(LinkAddress link:lp.getLinkAddresses())if(sameSubnet(link.getAddress().getAddress(),target.getAddress(),link.getPrefixLength()))return new HomeNetwork(n,host,cable?"Ethernet":"WLAN");
            }
        }return null;
    }
    public boolean bind(Context c){
        ConnectivityManager cm=(ConnectivityManager)c.getSystemService(Context.CONNECTIVITY_SERVICE);
        try{return Build.VERSION.SDK_INT>=23?cm.bindProcessToNetwork(network):ConnectivityManager.setProcessDefaultNetwork(network);}
        catch(SecurityException e){return false;}
    }
    public void release(Context c){
        ConnectivityManager cm=(ConnectivityManager)c.getSystemService(Context.CONNECTIVITY_SERVICE);
        if(Build.VERSION.SDK_INT>=23){if(network.equals(cm.getBoundNetworkForProcess()))cm.bindProcessToNetwork(null);}
        else if(network.equals(ConnectivityManager.getProcessDefaultNetwork()))ConnectivityManager.setProcessDefaultNetwork(null);
    }
}
