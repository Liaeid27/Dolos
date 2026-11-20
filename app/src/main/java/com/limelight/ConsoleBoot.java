package com.limelight;

import android.app.*;
import android.content.*;
import android.graphics.Typeface;
import android.media.MediaPlayer;
import android.view.*;
import android.widget.*;

final class ConsoleBoot {
    static FrameLayout curtain(Activity a,String title) {
        FrameLayout layer=new FrameLayout(a);
        layer.setBackgroundColor(0xff101724);layer.addView(new ConsoleHome.Horizon(a));
        TextView word=new TextView(a); word.setText(title); word.setGravity(Gravity.CENTER);
        word.setTextSize(42); word.setTextColor(-1); word.setLetterSpacing(.18f);
        word.setTypeface(Typeface.create("sans-serif-light",Typeface.NORMAL));
        layer.addView(word,new FrameLayout.LayoutParams(-1,-1));
        a.addContentView(layer,new FrameLayout.LayoutParams(-1,-1));
        word.setAlpha(0); word.setTranslationY(14);
        word.animate().alpha(1).translationY(0).setDuration(450);
        return layer;
    }
    static void remove(FrameLayout layer) {
        if(layer.getParent() instanceof ViewGroup) ((ViewGroup)layer.getParent()).removeView(layer);
    }
    @android.annotation.TargetApi(21)
    static boolean supportsFilmRate() {
        if(android.os.Build.VERSION.SDK_INT<21)return false;
        try {
            android.media.MediaCodecList list=new android.media.MediaCodecList(android.media.MediaCodecList.REGULAR_CODECS);
            for(android.media.MediaCodecInfo codec:list.getCodecInfos()){
                if(codec.isEncoder())continue;
                if(android.os.Build.VERSION.SDK_INT>=29 && !codec.isHardwareAccelerated())continue;
                for(String type:codec.getSupportedTypes()){
                    if(type.equalsIgnoreCase("video/avc") && codec.getCapabilitiesForType(type)
                        .getVideoCapabilities().areSizeAndRateSupported(1280,720,60))return true;
                }
            }
        } catch(RuntimeException ignored){}
        return false;
    }
    static void classic(Activity a,Runnable done){
        FrameLayout layer=curtain(a,"ASTER");
        if(com.limelight.preferences.ProfileSettings.group(a,"console").getBoolean("sound",true)){
            MediaPlayer music=MediaPlayer.create(a,R.raw.arrival);
            if(music!=null){music.setOnCompletionListener(MediaPlayer::release);music.start();}
        }
        layer.postDelayed(()->layer.animate().alpha(0).setDuration(320).withEndAction(()->{
            remove(layer);if(!a.isFinishing()&&!a.isDestroyed())done.run();
        }),740);
    }
    static void sequence(Activity a,boolean off,Runnable done) {
        String mode=off?"off":"on";
        String chosen=ConsoleHome.appearance(a).getString(mode,"dolos");
        if(!off&&"aster".equals(chosen)){classic(a,done);return;}
        android.net.Uri selected="dolos".equals(chosen)?null:ConsoleStudio.film(a,chosen,mode);
        FrameLayout layer=new FrameLayout(a);
        layer.setBackgroundColor(android.graphics.Color.BLACK);
        layer.setClickable(true);
        VideoView video=new VideoView(a);
        video.setZOrderMediaOverlay(true);
        layer.addView(video,new FrameLayout.LayoutParams(-1,-1,Gravity.CENTER));
        // Suspend drawing of the menu under the opaque video surface.
        ViewGroup content=a.findViewById(android.R.id.content);
        java.util.ArrayList<View> obscured=new java.util.ArrayList<>();
        for(int i=0;i<content.getChildCount();i++){
            View child=content.getChildAt(i);
            if(child.getVisibility()==View.VISIBLE){
                obscured.add(child);
                child.setVisibility(View.INVISIBLE);
            }
        }
        a.addContentView(layer,new FrameLayout.LayoutParams(-1,-1));
        boolean[] complete={false};
        Runnable finish=()->{
            if(complete[0])return;
            complete[0]=true;
            for(View child:obscured)child.setVisibility(View.VISIBLE);
            if(!BuildConfig.REMOTE_BUILD&&!off&&a instanceof PcView&&((PcView)a).openingLibraryAfterBoot()){
                video.stopPlayback();video.setVisibility(View.GONE);
                ImageView mark=new ImageView(a);mark.setImageResource(R.drawable.dolos_transition);mark.setScaleType(ImageView.ScaleType.FIT_CENTER);
                layer.addView(mark,new FrameLayout.LayoutParams(-1,-1));done.run();layer.postDelayed(()->remove(layer),750);return;
            }
            if(selected==null&&!off&&!a.isFinishing()&&!a.isDestroyed()){
                ImageView still=new ImageView(a);still.setScaleType(ImageView.ScaleType.FIT_CENTER);still.setImageResource(R.drawable.dolos_transition);
                layer.addView(still,new FrameLayout.LayoutParams(-1,-1));video.setVisibility(View.GONE);video.stopPlayback();
                layer.animate().alpha(0f).setDuration(360).withEndAction(()->{remove(layer);if(!a.isFinishing()&&!a.isDestroyed())done.run();});
                return;
            }
            video.stopPlayback();remove(layer);
            if(!a.isFinishing()&&!a.isDestroyed())done.run();
        };
        video.setOnCompletionListener(mp->finish.run());
        int fallback=off?R.raw.dolos_off_compat:R.raw.dolos_on_compat;
        boolean[] useMain={selected!=null||(!ConsoleDock.isTV(a)&&supportsFilmRate())};
        String resource="android.resource://"+a.getPackageName()+"/";
        video.setOnErrorListener((mp,what,extra)->{
            if(useMain[0]&&!complete[0]){
                useMain[0]=false;
                layer.removeCallbacks(finish);
                layer.postDelayed(finish,9000);
                video.setVideoURI(android.net.Uri.parse(resource+fallback));
            }else layer.post(finish);
            return true;
        });
        video.setOnPreparedListener(mp->{
            if(complete[0])return;layer.removeCallbacks(finish);layer.postDelayed(finish,Math.max(2000,mp.getDuration()+1600));
            boolean enabled=com.limelight.preferences.ProfileSettings.group(a,"console").getBoolean("sound",true);
            mp.setVolume(enabled?1:0,enabled?1:0);video.start();
        });
        int id=useMain[0]?(off?R.raw.dolos_off:R.raw.dolos_on):fallback;
        video.setVideoURI(selected!=null?selected:android.net.Uri.parse(resource+id));
        layer.postDelayed(finish,9000);
    }
    static void show(Activity a,Runnable complete) {
        sequence(a,false,()->{
            complete.run();
            if(!a.getSharedPreferences("console",0).getBoolean("setup",false))setup(a);
        });
    }
    static void setup(Activity a) {
        a.startActivity(new Intent(a,SetupGuide.class));a.overridePendingTransition(android.R.anim.fade_in,android.R.anim.fade_out);
    }
}
