package com.limelight;
import android.content.*;
import android.database.*;
import android.net.Uri;
import android.os.ParcelFileDescriptor;
import android.provider.OpenableColumns;
import java.io.*;

public class UpdateProvider extends ContentProvider {
    public boolean onCreate(){return true;}
    private File target(Uri uri){
        String name=uri.getLastPathSegment();
        if(name==null || !uri.getPath().matches("/[a-f0-9]{64}\\.apk"))throw new IllegalArgumentException("APK");
        return new File(new File(getContext().getCacheDir(),"releases"),name);
    }
    public String getType(Uri u){return "application/vnd.android.package-archive";}
    public ParcelFileDescriptor openFile(Uri u,String mode)throws FileNotFoundException{
        if(!"r".equals(mode))throw new FileNotFoundException();
        return ParcelFileDescriptor.open(target(u),ParcelFileDescriptor.MODE_READ_ONLY);
    }
    public Cursor query(Uri u,String[] fields,String s,String[] args,String order){
        File f=target(u);String[] cols=fields!=null?fields:new String[]{OpenableColumns.DISPLAY_NAME,OpenableColumns.SIZE};
        MatrixCursor c=new MatrixCursor(cols);Object[] values=new Object[cols.length];
        for(int i=0;i<cols.length;i++){if(OpenableColumns.SIZE.equals(cols[i]))values[i]=f.length();if(OpenableColumns.DISPLAY_NAME.equals(cols[i]))values[i]="Dolos.apk";}c.addRow(values);return c;
    }
    public Uri insert(Uri u,ContentValues v){throw new UnsupportedOperationException();}
    public int update(Uri u,ContentValues v,String s,String[] a){throw new UnsupportedOperationException();}
    public int delete(Uri u,String s,String[] a){throw new UnsupportedOperationException();}
}
