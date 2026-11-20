package com.limelight;
import org.json.JSONObject;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.Robolectric;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.annotation.Config;
import android.preference.PreferenceManager;
import static org.junit.Assert.*;
@RunWith(RobolectricTestRunner.class)
@Config(sdk=28,qualifiers="port",shadows=StudioSettingsTest.NoNativeStreaming.class)
public class StudioSettingsTest {
    @org.robolectric.annotation.Implements(value=com.limelight.nvstream.jni.MoonBridge.class,isInAndroidSdk=false)
    public static class NoNativeStreaming {
        @org.robolectric.annotation.Implementation protected static void __staticInitializer__(){}
    }
    @Test public void consoleSettingsWriteToTheRealStreamingPreferences() throws Exception{
        ConsoleStudio activity=Robolectric.buildActivity(ConsoleStudio.class).setup().get();
        activity.reloadStream();
        StudioPreferences model=(StudioPreferences)activity.getFragmentManager().findFragmentByTag("controls");
        JSONObject options=model.model();
        assertTrue(options.has("video"));assertTrue(options.has("audio"));assertTrue(options.has("controller"));
        model.change(new JSONObject().put("key","checkbox_host_audio").put("value",true));
        assertTrue(PreferenceManager.getDefaultSharedPreferences(activity).getBoolean("checkbox_host_audio",false));
    }
    @Test public void allowDirectNetworkOnly()throws Exception{
        byte[] a=java.net.InetAddress.getByName("192.168.0.14").getAddress();
        assertTrue(com.limelight.utils.HomeNetwork.sameSubnet(a,java.net.InetAddress.getByName("192.168.0.250").getAddress(),24));
        assertFalse(com.limelight.utils.HomeNetwork.sameSubnet(a,java.net.InetAddress.getByName("100.66.0.4").getAddress(),24));
        assertFalse(com.limelight.utils.HomeNetwork.sameSubnet(a,a,0));
    }
}
