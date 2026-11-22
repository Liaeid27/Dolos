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
        if(!(a instanceof Game))layer.addView(word,new FrameLayout.LayoutParams(-1,-1));
        a.addContentView(layer,new FrameLayout.LayoutParams(-1,-1));
        word.setAlpha(0); word.setTranslationY(14);
        word.animate().alpha(1).translationY(0).setDuration(450);
        return layer;
    }
    static void gameArt(Game activity,FrameLayout layer){
        Intent intent=activity.getIntent();String id=Catalog.steamId(intent.getStringExtra(Game.EXTRA_APP_NAME)==null?"":intent.getStringExtra(Game.EXTRA_APP_NAME));
        String uuid=intent.getStringExtra(Game.EXTRA_PC_UUID);
        if(uuid==null)return;
        new Thread(()->{
            android.graphics.Bitmap bitmap=null;
            try{
                org.json.JSONObject atlas=new org.json.JSONObject(activity.getSharedPreferences("dolos-control-"+uuid,0).getString("atlas","{}"));
                org.json.JSONArray ids=atlas.optJSONArray("ids");
                for(int i=0;ids!=null&&i<ids.length();i++)if(id.equals(ids.optString(i))){
                    java.io.File file=new java.io.File(new java.io.File(activity.getCacheDir(),"pc-art-"+uuid.replaceAll("[^a-zA-Z0-9-]","")),(i/64)+"_atlas_"+atlas.optString("rev")+".jpg");
                    if(file.isFile()){
                        android.graphics.BitmapRegionDecoder decoder=android.graphics.BitmapRegionDecoder.newInstance(file.toString(),false);
                        int x=i%8*144,y=i%64/8*216;
                        try{android.graphics.Bitmap thumb=decoder.decodeRegion(new android.graphics.Rect(x,y,x+144,y+216),null);
                            activity.runOnUiThread(()->showGameArt(activity,layer,thumb));
                        }finally{decoder.recycle();}
                    }
                    break;
                }
                int artworkId=intent.getIntExtra("gameArtworkId",intent.hasExtra("managedLaunch")?0:intent.getIntExtra(Game.EXTRA_APP_ID,0));
                java.io.File box=new java.io.File(new java.io.File(new java.io.File(activity.getCacheDir(),"boxart"),uuid),artworkId+".png");
                if(artworkId!=0&&box.isFile()){
                    bitmap=android.graphics.BitmapFactory.decodeFile(box.toString());
                    final android.graphics.Bitmap cached=bitmap;
                    if(cached!=null)activity.runOnUiThread(()->showGameArt(activity,layer,cached));
                }
                org.json.JSONObject all=new org.json.JSONObject(activity.getSharedPreferences("dolos-control-"+uuid,0).getString("artwork","{}"));
                org.json.JSONObject art=all.optJSONObject(id);
                if(art!=null){
                    String kind=art.has("hero")?"hero":"cover";
                    try(java.io.InputStream in=RemoteMedia.hostArt(activity,uuid,"/artwork/"+id+"/"+kind+"/"+art.getLong(kind)).getData()){
                        android.graphics.Bitmap local=android.graphics.BitmapFactory.decodeStream(in);if(local!=null)bitmap=local;
                    }
                }
            }catch(Exception ignored){}
            if(bitmap==null && id.matches("[0-9]{1,10}")){
                try(java.io.InputStream in=RemoteMedia.fetch(activity,"https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/"+id+"/header.jpg",false).getData()){bitmap=android.graphics.BitmapFactory.decodeStream(in);}catch(Exception ignored){}
            }
            final android.graphics.Bitmap image=bitmap;if(image==null)return;
            activity.runOnUiThread(()->showGameArt(activity,layer,image));
        },"Dolos-Launch-Art").start();
    }
    private static void showGameArt(Game activity,FrameLayout layer,android.graphics.Bitmap image){
        if(image==null||activity.isFinishing()||activity.isDestroyed())return;
        ImageView backdrop=layer.findViewWithTag("gameArt");
        if(backdrop==null){
            backdrop=new ImageView(activity);backdrop.setTag("gameArt");backdrop.setScaleType(ImageView.ScaleType.CENTER_CROP);
            layer.addView(backdrop,1,new FrameLayout.LayoutParams(-1,-1));backdrop.setAlpha(0f);
        }
        backdrop.setImageBitmap(image);backdrop.animate().alpha(.70f).setDuration(220);
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
        ImageView plate=new ImageView(a);
        plate.setBackgroundColor(android.graphics.Color.BLACK);
        plate.setScaleType(ImageView.ScaleType.FIT_CENTER);
        if(!off){plate.setImageResource(R.drawable.dolos_transition);plate.setAlpha(0f);layer.addView(plate,new FrameLayout.LayoutParams(-1,-1));}
        boolean[] complete={false};
        Runnable finish=()->{
            if(complete[0])return;
            complete[0]=true;
            for(View child:obscured)child.setVisibility(View.VISIBLE);
            if(!off&&!a.isFinishing()&&!a.isDestroyed()){
                plate.animate().cancel();plate.setAlpha(1f);
                // Submit the opaque handoff frame before the video Surface is destroyed.
                plate.postOnAnimation(()->plate.postOnAnimation(()->{
                    video.setVisibility(View.GONE);video.stopPlayback();
                    boolean launching=a instanceof PcView&&((PcView)a).openingLibraryAfterBoot();
                    if(launching){done.run();layer.postDelayed(()->remove(layer),1600);}
                    else layer.animate().alpha(0f).setDuration(360).withEndAction(()->{remove(layer);if(!a.isFinishing()&&!a.isDestroyed())done.run();});
                }));
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
            if(!off)layer.post(new Runnable(){
                public void run(){
                    if(complete[0]||!layer.isAttachedToWindow())return;
                    int left=video.getDuration()-video.getCurrentPosition();
                    int blend=selected==null?1400:480;
                    if(left>0 && left<=blend){plate.animate().alpha(1f).setDuration(Math.min(680,left));return;}
                    layer.postDelayed(this,100);
                }
            });
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
