package com.limelight;

import android.app.Dialog;
import android.app.Activity;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.view.*;
import android.widget.*;
import java.util.Collections;

/** Full-screen console player, independent of the boot film selection. */
final class StudioPlayer {
    static void show(Activity host,Uri uri,String title,String source,Runnable failed){
        Dialog dialog=new Dialog(host,android.R.style.Theme_Black_NoTitleBar_Fullscreen);
        float density=host.getResources().getDisplayMetrics().density;
        FrameLayout stage=new FrameLayout(host);stage.setBackgroundColor(Color.BLACK);
        VideoView video=new VideoView(host);stage.addView(video,new FrameLayout.LayoutParams(-1,-1,Gravity.CENTER));
        LinearLayout bar=new LinearLayout(host);bar.setGravity(Gravity.CENTER_VERTICAL);
        bar.setPadding((int)(24*density),(int)(18*density),(int)(24*density),(int)(12*density));
        bar.setBackground(new GradientDrawable(GradientDrawable.Orientation.TOP_BOTTOM,new int[]{0x00000000,0xf00b101c}));
        LinearLayout text=new LinearLayout(host);text.setOrientation(LinearLayout.VERTICAL);
        TextView credit=new TextView(host);credit.setTextColor(0xffbdcce2);credit.setTextSize(13);credit.setText(source+"  /  Vorschau");text.addView(credit);
        TextView name=new TextView(host);name.setTextColor(Color.WHITE);name.setTextSize(23);name.setTypeface(Typeface.create("sans-serif-light",0));name.setText(title);text.addView(name);
        bar.addView(text,new LinearLayout.LayoutParams(0,-2,1));
        Button close=new Button(host);close.setText("Schließen");close.setAllCaps(false);close.setTextColor(0xff172131);
        GradientDrawable pill=new GradientDrawable();pill.setColor(0xffe4ebf6);pill.setCornerRadius(32*density);close.setBackground(pill);close.setOnClickListener(v->dialog.dismiss());bar.addView(close);
        stage.addView(bar,new FrameLayout.LayoutParams(-1,-2,Gravity.BOTTOM));dialog.setContentView(stage);
        dialog.setOnDismissListener(d->video.stopPlayback());video.setOnCompletionListener(m->dialog.dismiss());
        video.setOnErrorListener((m,w,e)->{dialog.dismiss();failed.run();return true;});
        dialog.show();dialog.getWindow().getDecorView().setSystemUiVisibility(5894);close.requestFocus();
        bar.setAlpha(0);bar.setTranslationY(10*density);bar.animate().alpha(1).translationY(0).setDuration(260);
        video.setVideoURI(uri,Collections.singletonMap("Referer","https://steamdeckrepo.com/"));video.start();
    }
}
