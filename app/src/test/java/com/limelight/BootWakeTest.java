package com.limelight;

import android.content.Context;
import android.content.Intent;
import com.limelight.computers.ComputerDatabaseManager;
import com.limelight.nvstream.http.ComputerDetails;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.RuntimeEnvironment;
import org.robolectric.annotation.Config;
import javax.net.ssl.TrustManagerFactory;
import javax.net.ssl.X509TrustManager;
import java.security.KeyStore;
import java.util.ArrayList;
import java.util.List;
import static org.junit.Assert.*;

@RunWith(RobolectricTestRunner.class)
@Config(sdk=28)
public class BootWakeTest {
    @Test public void savedHostWakesDuringFilmAndOnlyOncePerBoot()throws Exception{
        Context app=RuntimeEnvironment.getApplication();
        ComputerDetails pc=new ComputerDetails();
        pc.uuid="paired-pc";pc.name="Test";pc.macAddress="02:00:00:00:00:01";
        TrustManagerFactory factory=TrustManagerFactory.getInstance(TrustManagerFactory.getDefaultAlgorithm());
        factory.init((KeyStore)null);
        pc.serverCert=((X509TrustManager)factory.getTrustManagers()[0]).getAcceptedIssuers()[0];
        ComputerDatabaseManager database=new ComputerDatabaseManager(app);
        try{assertTrue(database.updateComputer(pc));}finally{database.close();}
        app.getSharedPreferences("console",0).edit().putString("host",pc.uuid).commit();
        app.getSharedPreferences("remote",0).edit().putString("wakeUrl","https://pi.example.ts.net/wake").commit();
        List<String> sent=new ArrayList<>();
        BootWake.Sender sender=(context,target)->sent.add(target.uuid);
        Intent film=new Intent(),library=new Intent();
        BootWake.atFilmStart(app,BootWake.session(film),Runnable::run,sender);
        assertEquals(java.util.Collections.singletonList(pc.uuid),sent);
        BootWake.carry(film,library);
        BootWake.atFilmStart(app,BootWake.session(library),Runnable::run,sender);
        assertEquals(1,sent.size());
        BootWake.atFilmStart(app,BootWake.session(new Intent()),Runnable::run,sender);
        assertEquals(2,sent.size());
        app.getSharedPreferences("console",0).edit().putBoolean("wake",false).commit();
        BootWake.atFilmStart(app,BootWake.session(new Intent()),Runnable::run,sender);
        assertEquals(2,sent.size());
        app.getSharedPreferences("console",0).edit().putBoolean("wake",true).putString("host","removed").commit();
        BootWake.atFilmStart(app,BootWake.session(new Intent()),Runnable::run,sender);
        assertEquals(2,sent.size());
    }
    @Test public void pollingCanRetryFailedWakeButCannotDuplicateSuccess(){
        String key="test/"+java.util.UUID.randomUUID();
        assertTrue(BootWake.reserve(key,100));
        assertFalse(BootWake.reserve(key,105));
        BootWake.finish(key,false,120);
        assertFalse(BootWake.reserve(key,300));
        assertTrue(BootWake.reserve(key,3120));
        BootWake.finish(key,true,3150);
        assertFalse(BootWake.reserve(key,95000));
    }
}
