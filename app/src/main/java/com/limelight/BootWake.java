package com.limelight;

import android.content.Context;
import android.content.Intent;
import android.os.SystemClock;
import com.limelight.computers.ComputerDatabaseManager;
import com.limelight.nvstream.http.ComputerDetails;
import java.io.IOException;
import java.util.LinkedHashMap;
import java.util.UUID;
import java.util.concurrent.Executor;
import java.util.concurrent.Executors;

final class BootWake {
    private static final String EXTRA="dolosBootWake";
    private static final Executor worker=Executors.newSingleThreadExecutor();
    interface Sender { void send(Context context,ComputerDetails pc)throws IOException; }
    private static final class Attempt {
        int count;
        boolean sentOrSending;
        long retryAt;
    }
    private static final LinkedHashMap<String,Attempt> attempts=new LinkedHashMap<>();

    static String session(Intent intent){
        String id=intent.getStringExtra(EXTRA);
        if(id==null){id=UUID.randomUUID().toString();intent.putExtra(EXTRA,id);}
        return id;
    }
    static void carry(Intent from,Intent to){to.putExtra(EXTRA,session(from));}

    static void atFilmStart(Context context,String boot){
        atFilmStart(context,boot,worker,RemoteWake::send);
    }
    static void atFilmStart(Context context,String boot,Executor executor,Sender sender){
        Context app=context.getApplicationContext();
        android.content.SharedPreferences console=app.getSharedPreferences("console",0);
        String host=console.getString("host","");
        if(host.isEmpty()||!console.getBoolean("wake",true))return;
        executor.execute(()->{
            try{sendIfNeeded(app,boot,ComputerDatabaseManager.readSavedComputer(app,host),sender);}
            catch(RuntimeException e){com.limelight.LimeLog.warning("Saved wake target unavailable");}
        });
    }
    static void request(Context context,String boot,ComputerDetails pc){
        Context app=context.getApplicationContext();
        worker.execute(()->sendIfNeeded(app,boot,pc,RemoteWake::send));
    }
    private static void sendIfNeeded(Context app,String boot,ComputerDetails pc,Sender sender){
        if(pc==null||pc.serverCert==null||pc.state==ComputerDetails.State.ONLINE)return;
        if(!app.getSharedPreferences("console",0).getBoolean("wake",true))return;
        if(BuildConfig.REMOTE_BUILD){
            if(!RemoteWake.valid(app.getSharedPreferences("remote",0).getString("wakeUrl","")))return;
        }else if(pc.macAddress==null||pc.macAddress.isEmpty())return;
        String key=boot+"/"+pc.uuid;
        if(!reserve(key,SystemClock.elapsedRealtime()))return;
        boolean sent=false;
        try{sender.send(app,pc);sent=true;}
        catch(IOException|RuntimeException e){com.limelight.LimeLog.warning("Automatic wake unavailable");}
        finally{finish(key,sent,SystemClock.elapsedRealtime());}
    }
    static synchronized boolean reserve(String key,long now){
        Attempt current=attempts.get(key);
        if(current==null){
            if(attempts.size()>=8)attempts.remove(attempts.keySet().iterator().next());
            current=new Attempt();attempts.put(key,current);
        }
        if(current.sentOrSending||current.count>=3||now<current.retryAt)return false;
        current.sentOrSending=true;current.count++;
        return true;
    }
    static synchronized void finish(String key,boolean sent,long now){
        Attempt current=attempts.get(key);
        if(current!=null){current.sentOrSending=sent;current.retryAt=now+3000;}
    }
}
