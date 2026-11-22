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
    private static final ArtworkCache artwork=new ArtworkCache(96L*1024*1024,
        java.util.concurrent.Executors.newSingleThreadExecutor());
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
        if(pin==null||token==null)throw new IOException("Host unavailable");
        String address=pair.getString("artHost",uuid.equals(studio.getString("lastUuid",""))?host:"");
        final String endpoint=BuildConfig.REMOTE_BUILD?context.getSharedPreferences("remote",0).getString("host."+uuid,address):address;
        File folder=new File(context.getCacheDir(),"pc-art-"+uuid.replaceAll("[^a-zA-Z0-9-]",""));
        File file=new File(folder,path.substring(9).replace('/','_')+".jpg");
        return new WebResourceResponse("image/jpeg",null,artwork.open(file,tmp->{
                if(endpoint.isEmpty())throw new IOException("Host unavailable");
                javax.net.ssl.HttpsURLConnection c=ControlLink.connection(endpoint,path,pin);
                try{
                    c.setRequestProperty("Authorization","Bearer "+token);
                    if(c.getResponseCode()!=200)throw new IOException("No image");
                    try(java.io.InputStream in=c.getInputStream();java.io.OutputStream out=new java.io.FileOutputStream(tmp)){
                        byte[] buf=new byte[16384];int n,total=0;
                        while((n=in.read(buf))!=-1){total+=n;if(total>12*1024*1024)throw new IOException("Image too large");out.write(buf,0,n);}
                        if(total<4||total!=c.getContentLength())throw new IOException("Incomplete image");
                    }
                }finally{c.disconnect();}
        }));
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
