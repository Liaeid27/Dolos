package com.limelight;

import android.content.Context;
import android.webkit.WebResourceResponse;
import java.io.File;
import java.io.IOException;
import java.util.concurrent.TimeUnit;
import okhttp3.Cache;
import okhttp3.CacheControl;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.Response;

/** Disk-backed remote catalogue media. Trailers keep their own adaptive streaming transport. */
final class RemoteMedia {
    private static OkHttpClient client;
    private static synchronized OkHttpClient client(Context context){
        if(client==null)client=new OkHttpClient.Builder()
            .cache(new Cache(new File(context.getCacheDir(),"remote-store"),96L*1024*1024))
            .connectTimeout(6,TimeUnit.SECONDS).readTimeout(12,TimeUnit.SECONDS)
            .addNetworkInterceptor(chain->{
                Response res=chain.proceed(chain.request());
                if(!res.isSuccessful())return res;
                boolean metadata="store.steampowered.com".equals(chain.request().url().host());
                return res.newBuilder().removeHeader("Pragma")
                    .header("Cache-Control",metadata?"public, max-age=86400":"public, max-age=2592000").build();
            }).build();
        return client;
    }
    static WebResourceResponse hostArt(Context context,String uuid,String path)throws IOException{
        android.content.SharedPreferences studio=context.getSharedPreferences("studio",0);
        String host=studio.getString("lastHost","");
        android.content.SharedPreferences pair=context.getSharedPreferences("dolos-control-"+uuid,0);
        String pin=pair.getString("cert",null),token=pair.getString("token",null);
        if(pin==null||token==null||!uuid.equals(studio.getString("lastUuid","")))throw new IOException("Host unavailable");
        File folder=new File(context.getCacheDir(),"pc-art-"+uuid.replaceAll("[^a-zA-Z0-9-]",""));
        folder.mkdirs();File file=new File(folder,path.substring(9).replace('/','_')+".jpg");
        if(!file.isFile()){
            File tmp=File.createTempFile("partial",".tmp",folder);
            try{
                javax.net.ssl.HttpsURLConnection c=ControlLink.connection(host,path,pin);
                try{
                    c.setRequestProperty("Authorization","Bearer "+token);
                    if(c.getResponseCode()!=200)throw new IOException("No image");
                    try(java.io.InputStream in=c.getInputStream();java.io.OutputStream out=new java.io.FileOutputStream(tmp)){
                        byte[] buf=new byte[16384];int n,total=0;
                        while((n=in.read(buf))!=-1){total+=n;if(total>12*1024*1024)throw new IOException("Image too large");out.write(buf,0,n);}
                        if(total<4||total!=c.getContentLength())throw new IOException("Incomplete image");
                    }
                }finally{c.disconnect();}
                if(!tmp.renameTo(file)&&!file.isFile())throw new IOException("Cache unavailable");
                File[] files=folder.listFiles((dir,name)->name.endsWith(".jpg"));
                if(files!=null){java.util.Arrays.sort(files,(x,y)->Long.compare(y.lastModified(),x.lastModified()));long used=0;
                    for(File entry:files){used+=entry.length();if(used>96L*1024*1024&&!entry.equals(file))entry.delete();}}
            }catch(Exception e){throw new IOException(e);}finally{tmp.delete();}
        }
        return new WebResourceResponse("image/jpeg",null,new java.io.FileInputStream(file));
    }
    static WebResourceResponse fetch(Context context,String url,boolean metadata)throws IOException{
        OkHttpClient http=client(context);
        Request request=new Request.Builder().url(url).build();
        Response response;
        try{
            response=http.newCall(request).execute();
            if(!response.isSuccessful()){response.close();throw new IOException("Media unavailable");}
        }catch(IOException e){
            response=http.newCall(request.newBuilder().cacheControl(CacheControl.FORCE_CACHE).build()).execute();
            if(!response.isSuccessful()){response.close();throw e;}
        }
        String mime=response.header("Content-Type",metadata?"application/json":"image/jpeg").split(";")[0];
        if(!(metadata?mime.contains("json"):mime.startsWith("image/"))){response.close();throw new IOException("Unexpected media type");}
        return new WebResourceResponse(mime,metadata?"UTF-8":null,response.body().byteStream());
    }
}
