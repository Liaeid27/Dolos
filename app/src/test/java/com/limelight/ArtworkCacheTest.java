package com.limelight;

import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;
import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.util.concurrent.Callable;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import static org.junit.Assert.*;

public class ArtworkCacheTest {
    @Rule public TemporaryFolder temp=new TemporaryFolder();
    private final ArtworkCache cache=new ArtworkCache(1024,Runnable::run);

    @Test public void launchAndStoreCanReadTheSameImageWithOneDownload()throws Exception{
        File file=new File(temp.getRoot(),"cover.jpg");
        AtomicInteger downloads=new AtomicInteger();
        CountDownLatch started=new CountDownLatch(1),finish=new CountDownLatch(1);
        ExecutorService pool=Executors.newFixedThreadPool(3);
        Callable<Integer> reader=()->{
            try(InputStream image=cache.open(file,partial->{
                downloads.incrementAndGet();
                Files.write(partial.toPath(),new byte[]{42});
                started.countDown();
                if(!finish.await(5,TimeUnit.SECONDS))throw new IOException("timeout");
            })){return image.read();}
        };
        try{
            Future<Integer> first=pool.submit(reader);
            assertTrue(started.await(5,TimeUnit.SECONDS));
            assertFalse(file.exists());
            Future<Integer> second=pool.submit(reader);
            File other=new File(temp.getRoot(),"other.jpg");
            Future<Integer> independent=pool.submit(()->{
                try(InputStream image=cache.open(other,p->Files.write(p.toPath(),new byte[]{7}))){return image.read();}
            });
            assertEquals(7,independent.get(5,TimeUnit.SECONDS).intValue());
            finish.countDown();
            assertEquals(42,first.get(5,TimeUnit.SECONDS).intValue());
            assertEquals(42,second.get(5,TimeUnit.SECONDS).intValue());
            assertEquals(1,downloads.get());
        }finally{finish.countDown();pool.shutdownNow();}
    }

    @Test public void incompleteTransferCanRetryAndThenReadOffline()throws Exception{
        File file=new File(temp.getRoot(),"cover.jpg");
        try{
            cache.open(file,p->{Files.write(p.toPath(),new byte[]{9});throw new IOException("disconnected");});
            fail();
        }catch(IOException expected){assertFalse(file.exists());}
        try(InputStream image=cache.open(file,p->Files.write(p.toPath(),new byte[]{23}))){assertEquals(23,image.read());}
        try(InputStream image=cache.open(file,p->{throw new IOException("offline");})){assertEquals(23,image.read());}
        assertArrayEquals(new String[]{"cover.jpg"},temp.getRoot().list());
    }
}
