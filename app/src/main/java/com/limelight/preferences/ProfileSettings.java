package com.limelight.preferences;

import android.content.Context;
import android.content.SharedPreferences;

/** Device pairing is shared. Input, playback and appearance follow the selected user. */
public final class ProfileSettings {
    public static String name(Context context,String base){
        int slot=context.getSharedPreferences("profiles",0).getInt("active",0);
        return slot==0?base:base+".profile."+slot;
    }
    public static SharedPreferences group(Context context,String base){
        return context.getSharedPreferences(name(context,base),0);
    }
    public static String streamName(Context context){return name(context,context.getPackageName()+"_preferences");}
    public static synchronized SharedPreferences stream(Context context){
        SharedPreferences prefs=context.getSharedPreferences(streamName(context),0);
        if(com.limelight.BuildConfig.REMOTE_BUILD&&!prefs.contains("list_resolution")&&context.getSharedPreferences("profiles",0).getInt("active",0)!=0){
            prefs.edit().putString("list_resolution","1280x720").putString("list_fps","60").putInt("seekbar_bitrate_kbps",7500)
                .putBoolean("checkbox_show_onscreen_controls",context.getPackageManager().hasSystemFeature("android.hardware.touchscreen")).apply();
        }
        return prefs;
    }
}
