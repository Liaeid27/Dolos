package com.limelight;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.util.Arrays;
import java.util.HashMap;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.Executor;
import java.util.concurrent.FutureTask;

/** The catalogue and game launch screen share the same revisioned image files. */
final class ArtworkCache {
    interface Download { void write(File partial) throws Exception; }
    private final ConcurrentHashMap<File,FutureTask<Void>> pending=new ConcurrentHashMap<>();
    private final HashMap<File,Long> bytesSinceTrim=new HashMap<>();
    private final Executor maintenance;
    private final long limit;

    ArtworkCache(long limit,Executor maintenance){
        this.limit=limit;
        this.maintenance=maintenance;
    }

    FileInputStream open(File file,Download download)throws IOException{
        try{return new FileInputStream(file);}catch(FileNotFoundException miss){
            if(file.exists())throw miss;
        }
        FutureTask<Void> job=new FutureTask<>(()->{
            if(file.isFile())return null;
            File folder=file.getParentFile();
            if(!folder.isDirectory()&&!folder.mkdirs()&&!folder.isDirectory())throw new IOException("Cache unavailable");
            File partial=File.createTempFile("partial",".tmp",folder);
            try{
                download.write(partial);
                if(!partial.renameTo(file)&&!file.isFile())throw new IOException("Cache unavailable");
            }finally{partial.delete();}
            scheduleTrim(folder,file.length());
            return null;
        });
        FutureTask<Void> active=pending.putIfAbsent(file,job);
        if(active==null){active=job;job.run();}
        try{
            active.get();
            return new FileInputStream(file);
        }catch(InterruptedException e){
            Thread.currentThread().interrupt();throw new IOException(e);
        }catch(ExecutionException e){throw new IOException(e.getCause());}
        finally{if(active.isDone())pending.remove(file,active);}
    }

    private synchronized void scheduleTrim(File folder,long added){
        Long previous=bytesSinceTrim.get(folder);
        long total=previous==null?0:previous+added;
        if(previous!=null&&total<Math.min(limit/8,4L*1024*1024)){
            bytesSinceTrim.put(folder,total);return;
        }
        bytesSinceTrim.put(folder,0L);
        maintenance.execute(()->{
            File[] files=folder.listFiles((dir,name)->name.endsWith(".jpg"));
            if(files==null)return;
            Arrays.sort(files,(a,b)->Long.compare(b.lastModified(),a.lastModified()));
            long used=0;
            for(File entry:files){
                used+=entry.length();
                if(used>limit&&!pending.containsKey(entry))entry.delete();
            }
        });
    }
}
