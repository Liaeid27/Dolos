package com.limelight;

import android.view.InputDevice;
import android.view.KeyEvent;
import android.view.MotionEvent;
import android.view.View;

final class StickNavigation {
    static void attach(View view) {
        view.setOnGenericMotionListener(new View.OnGenericMotionListener() {
            int direction;
            boolean leftTrigger,rightTrigger;
            long next;
            public boolean onGenericMotion(View target, MotionEvent e) {
                if (!e.isFromSource(InputDevice.SOURCE_JOYSTICK) || e.getAction()!=MotionEvent.ACTION_MOVE) return false;
                boolean left=Math.max(e.getAxisValue(MotionEvent.AXIS_LTRIGGER),e.getAxisValue(MotionEvent.AXIS_BRAKE))>.65f;
                boolean right=Math.max(e.getAxisValue(MotionEvent.AXIS_RTRIGGER),e.getAxisValue(MotionEvent.AXIS_GAS))>.65f;
                if(left&&!leftTrigger||right&&!rightTrigger){
                    int shoulder=left&&!leftTrigger?KeyEvent.KEYCODE_BUTTON_L2:KeyEvent.KEYCODE_BUTTON_R2;
                    target.dispatchKeyEvent(new KeyEvent(KeyEvent.ACTION_DOWN,shoulder));target.dispatchKeyEvent(new KeyEvent(KeyEvent.ACTION_UP,shoulder));
                }
                leftTrigger=left;rightTrigger=right;
                float x=e.getAxisValue(MotionEvent.AXIS_X), y=e.getAxisValue(MotionEvent.AXIS_Y);
                float magnitude=Math.max(Math.abs(x),Math.abs(y));
                if(magnitude<0.35f){direction=0;return false;}
                if(magnitude<0.58f)return true;
                int key=Math.abs(x)>Math.abs(y)?(x<0?KeyEvent.KEYCODE_DPAD_LEFT:KeyEvent.KEYCODE_DPAD_RIGHT):
                        (y<0?KeyEvent.KEYCODE_DPAD_UP:KeyEvent.KEYCODE_DPAD_DOWN);
                long now=e.getEventTime();
                if(key!=direction || now>=next){
                    next=now+(key==direction?150:360);direction=key;
                    target.dispatchKeyEvent(new KeyEvent(KeyEvent.ACTION_DOWN,key));
                    target.dispatchKeyEvent(new KeyEvent(KeyEvent.ACTION_UP,key));
                }
                return true;
            }
        });
    }
}
