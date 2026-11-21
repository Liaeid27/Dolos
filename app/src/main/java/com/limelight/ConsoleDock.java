package com.limelight;

import android.app.Activity;
import android.app.Dialog;
import android.graphics.Color;
import android.graphics.drawable.GradientDrawable;
import android.view.*;
import android.widget.*;

final class ConsoleDock {
    static boolean isTV(Activity activity){
        return activity.getPackageManager().hasSystemFeature("android.software.leanback")||
            (activity.getResources().getConfiguration().uiMode&15)==android.content.res.Configuration.UI_MODE_TYPE_TELEVISION;
    }
    interface Pick { void select(int index); }
    static void show(Activity a,String[] labels,Pick pick){
        show(a,"Kontrollzentrum",labels,pick);
    }
    static void show(Activity a,String title,String[] labels,Pick pick){
        panel(a,title,null,labels,pick,-1);
    }
    static Dialog panel(Activity a,String title,TextView detail,String[] labels,Pick pick,int dismissIndex){
        Dialog sheet=new Dialog(a);
        sheet.requestWindowFeature(Window.FEATURE_NO_TITLE);
        float density=a.getResources().getDisplayMetrics().density;
        int pad=(int)(16*density);
        LinearLayout panel=new LinearLayout(a);
        panel.setOrientation(LinearLayout.VERTICAL);
        panel.setPadding(pad*2,pad,pad*2,pad);
        panel.setBackground(new GradientDrawable(GradientDrawable.Orientation.LEFT_RIGHT,new int[]{0xf2222e40,0xf20e141e}));
        TextView heading=new TextView(a);heading.setText(title);heading.setTextSize(23);heading.setTextColor(Color.WHITE);panel.addView(heading);
        if(detail!=null){
            detail.setTextSize(16);detail.setTextColor(0xffdce5ef);detail.setPadding(0,pad/2,0,pad/2);
            ScrollView scroll=new ScrollView(a);scroll.addView(detail);
            int maxHeight=a.getResources().getDisplayMetrics().heightPixels/3;
            detail.measure(View.MeasureSpec.makeMeasureSpec(a.getResources().getDisplayMetrics().widthPixels-4*pad,View.MeasureSpec.AT_MOST),0);
            panel.addView(scroll,new LinearLayout.LayoutParams(-1,Math.min(maxHeight,detail.getMeasuredHeight())));
        }
        LinearLayout row=new LinearLayout(a);
        boolean compact=a.getResources().getConfiguration().screenWidthDp<600;
        if(compact)row.setOrientation(LinearLayout.VERTICAL);
        panel.addView(row);
        for(int i=0;i<labels.length;i++){
            final int index=i;
            Button b=new Button(a);b.setText(labels[i]);b.setTextSize(14);b.setAllCaps(false);
            b.setOnFocusChangeListener((v,on)->{
                GradientDrawable g=new GradientDrawable();g.setCornerRadius(pad*.5f);g.setColor(on?0xffeef3fb:0x222b3549);
                b.setBackground(g);b.setTextColor(on?0xff111927:Color.WHITE);
                b.animate().scaleX(on?1.025f:1).scaleY(on?1.025f:1).setDuration(150);
            });
            b.setTextColor(Color.WHITE);b.setBackgroundColor(0x22394456);
            b.setOnClickListener(v->{if(dismissIndex<0||dismissIndex==index)sheet.dismiss();pick.select(index);});
            LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(compact?-1:0,(int)((compact?42:56)*density),compact?0:1);
            lp.setMargins(0,pad/2,pad/3,0);row.addView(b,lp);
        }
        sheet.setContentView(panel);Window window=sheet.getWindow();
        window.setBackgroundDrawableResource(android.R.color.transparent);window.setGravity(Gravity.BOTTOM);
        window.setLayout(-1,-2);window.setDimAmount(.35f);sheet.show();
        row.getChildAt(0).requestFocus();panel.setTranslationY(pad*2);panel.setAlpha(0);
        panel.animate().translationY(0).alpha(1).setDuration(220);
        return sheet;
    }
}
