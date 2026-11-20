package com.limelight;

import android.app.Activity;
import android.content.*;
import android.os.*;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.view.*;
import android.widget.*;
import com.limelight.binding.PlatformBinding;
import com.limelight.computers.ComputerManagerService;
import com.limelight.nvstream.http.*;
import com.limelight.utils.ServerHelper;
import org.json.JSONObject;
import java.net.*;
import com.limelight.nvstream.mdns.*;
import java.util.concurrent.*;

public final class SetupGuide extends Activity {
    private final ExecutorService tasks=Executors.newSingleThreadExecutor();
    private volatile ComputerManagerService.ComputerManagerBinder manager;
    private final ServiceConnection connection=new ServiceConnection(){
        public void onServiceConnected(ComponentName n,IBinder b){manager=(ComputerManagerService.ComputerManagerBinder)b;}
        public void onServiceDisconnected(ComponentName n){manager=null;}
    };
    private boolean bound,busy,dead;
    private int step;
    private com.limelight.utils.HomeNetwork setupNetwork;
    private String address="",fingerprint="";
    private ComputerDetails pc;
    private LinearLayout page;
    private TextView feedback;
    private SharedPreferences prefs;
    private final String[] titles={"Eingabe","Spiel-PC","PC-Verwaltung","Deine Konsole"};
    @Override public void onCreate(Bundle saved){
        super.onCreate(saved);prefs=getSharedPreferences("console",0);
        address=prefs.getString("setupAddress","");step=getIntent().getBooleanExtra("connectNow",false)?1:0;
        getWindow().getDecorView().setSystemUiVisibility(5894);
        getWindow().setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE);
        bound=bindService(new Intent(this,ComputerManagerService.class),connection,BIND_AUTO_CREATE);
        draw();
    }
    private int dp(float v){return Math.round(v*getResources().getDisplayMetrics().density);}
    private TextView label(String s,int size,int color){
        TextView v=new TextView(this);v.setText(s);v.setTextSize(size);v.setTextColor(color);v.setPadding(0,dp(4),0,dp(5));page.addView(v);return v;
    }
    private void button(String name,Runnable fn){
        Button b=new Button(this);b.setText(name);b.setAllCaps(false);b.setGravity(Gravity.CENTER_VERTICAL|Gravity.LEFT);
        android.graphics.drawable.StateListDrawable states=new android.graphics.drawable.StateListDrawable();
        for(int state:new int[]{android.R.attr.state_pressed,android.R.attr.state_focused,0}){
            GradientDrawable tile=new GradientDrawable();tile.setColor(state==0?0xff212b38:0xff435265);tile.setCornerRadius(dp(9));
            if(state!=0)tile.setStroke(dp(2),0xfff4eccc);
            states.addState(state==0?new int[]{}:new int[]{state},tile);
        }
        b.setTextColor(0xfffff4df);b.setPadding(dp(15),0,dp(15),0);b.setBackground(states);
        LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(-1,dp(46));lp.topMargin=dp(5);
        b.setOnClickListener(v->{if(!busy)fn.run();});page.addView(b,lp);
    }
    private EditText field(String hint,String value,int type){
        EditText e=new EditText(this);e.setSingleLine(true);e.setInputType(type);e.setTextColor(-1);e.setHintTextColor(0xffb4bce1);
        e.setHint(hint);e.setText(value);page.addView(e);return e;
    }
    private void move(int next){step=next;draw();}
    private void draw(){
        ScrollView sc=new ScrollView(this);sc.setFillViewport(true);
        sc.setBackground(new GradientDrawable(GradientDrawable.Orientation.TL_BR,new int[]{0xff263344,0xff141d29,0xff0c111a}));
        LinearLayout frame=new LinearLayout(this);frame.setGravity(Gravity.CENTER);sc.addView(frame);
        page=new LinearLayout(this);page.setOrientation(LinearLayout.VERTICAL);page.setPadding(dp(22),dp(12),dp(22),dp(18));
        int width=Math.min(getResources().getDisplayMetrics().widthPixels,dp(580));frame.addView(page,new LinearLayout.LayoutParams(width,-2));
        setContentView(sc);label("D O L O S      /      "+(step+1)+"  VON  4",13,0xffcad3fb);
        label(titles[step],34,0xffeef2f7).setTypeface(Typeface.create("sans-serif-light",Typeface.NORMAL));
        feedback=label("",16,0xffeef0ff);
        if(step==0){
            feedback.setText("Teste die Bestätigungstaste oder verwende den Touchscreen.");
            button("Eingabe testen",()->feedback.setText("Eingabe erkannt. Du kannst fortfahren."));
            button("Bluetooth öffnen",()->{try{startActivity(new Intent(android.provider.Settings.ACTION_BLUETOOTH_SETTINGS));}catch(ActivityNotFoundException e){startActivity(new Intent(android.provider.Settings.ACTION_SETTINGS));}});
            button("Weiter",()->move(1));
        }else if(step==1){
            feedback.setText("Am PC: Dolos-PC → Verbindung öffnen. Sobald „Apollo bereit“ erscheint, lies die Adresse ab.\nHier: Mit demselben Router verbinden. „PC suchen“ wählen oder die Adresse unten eingeben.");
            if(BuildConfig.REMOTE_BUILD)feedback.setText("Tailscale auf PC und Android öffnen und mit demselben Netz verbinden. Am PC in Tailscale die Adresse des Spiel-PCs kopieren.");else button("PC suchen",this::discover);
            label("Manuell verbinden",18,0xfff1e9d8);
            label(BuildConfig.REMOTE_BUILD?"Gib die Tailscale-IP des PCs (100.x.x.x) oder seinen vollständigen Tailscale-Namen ein.":"Öffne Dolos-PC → Verbindung. Verwende die angezeigte Ethernet- oder WLAN-Adresse (z. B. 192.168.1.10).",15,0xffcad3fb);
            EditText host=field("PC-Adresse",address,17);
            button("PC verbinden",()->{address=host.getText().toString().trim();connect();});
        }else if(step==2){
            feedback.setText("Der Spielstream ist gekoppelt. Am PC: Dolos-PC → Einrichtung → TV-Code anzeigen. Hier: Prüfzeichen vergleichen und den sechsstelligen Code eingeben.");
            if(fingerprint.isEmpty())button("Prüfzeichen abrufen",()->network(()->{
                fingerprint=ControlLink.request(endpoint(),"/ping",null,null,null).getString("pin");ui(this::draw);
            }));
            else{
                label(fingerprint.substring(0,4)+"   "+fingerprint.substring(4,8)+"   "+fingerprint.substring(8,12),24,0xffffebc4);
                EditText pin=field("TV-Code","",2);
                button("Prüfzeichen stimmt · koppeln",()->{
                    String code=pin.getText().toString().trim();if(!code.matches("[0-9]{6}")){feedback.setText("Gib alle sechs Ziffern ein.");return;}
                    network(()->{
                        String token=ControlLink.request(endpoint(),"/pair",new JSONObject().put("pin",code),fingerprint,null).getString("token");
                        control().edit().putString("cert",fingerprint).putString("token",token).apply();
                        verifyControl();
                    });
                });
            }
            if(control().contains("token"))button("Gespeicherte Verbindung prüfen",()->network(this::verifyControl));
        }else{
            feedback.setText(pc==null?"Der Spiel-PC ist noch offen. Du kannst die Einrichtung später fortsetzen.":"Spiel-PC verbunden: "+pc.name);
            for(String[] x:new String[][]{{"wake","PC beim Öffnen wecken"},{"sound","Systemklänge"},{"music","Menümusik"}}){
                SharedPreferences options="wake".equals(x[0])?prefs:com.limelight.preferences.ProfileSettings.group(this,"console");CheckBox c=new CheckBox(this);c.setTextColor(-1);c.setText(x[1]);c.setChecked(options.getBoolean(x[0],true));c.setOnCheckedChangeListener((v,on)->options.edit().putBoolean(x[0],on).apply());page.addView(c);
            }
            if(BuildConfig.REMOTE_BUILD){
                SharedPreferences remote=getSharedPreferences("remote",0);
                label("PC unterwegs wecken · optional",18,-1);
                label("Bei PC Control die Tailscale-Adresse des Pi mit Port und /api/wake eingeben. Der Schlüssel bleibt dafür leer.",15,0xffcad3fb);
                EditText url=field("https://pi.…ts.net:8443/wake",remote.getString("wakeUrl",""),17);
                EditText token=field("Weckschlüssel · nur für eigenen HTTPS-Dienst",remote.getString("wakeToken",""),129);
                button(pc==null?"Zur PC-Auswahl":"Konsole öffnen",()->{
                    String u=url.getText().toString().trim(),t=token.getText().toString().trim();
                    if(!u.isEmpty()&&(!RemoteWake.valid(u)||(!RemoteWake.pi(u)&&t.isEmpty()))){feedback.setText("Pi-Weckadresse verwenden oder private HTTPS-Adresse mit .ts.net und Schlüssel eingeben.");return;}
                    remote.edit().putString("wakeUrl",u).putString("wakeToken",u.isEmpty()?"":t).apply();complete();
                });
            }else button(pc==null?"Zur PC-Auswahl":"Konsole öffnen",this::complete);
        }
        if(step==1||step==2)button("Später einrichten",()->move(3));
        if(step>0)button("Zurück",()->move(step==3?(pc==null?1:2):step-1));
        page.setAlpha(.65f);page.animate().alpha(1).setDuration(250);
    }
    private SharedPreferences control(){return getSharedPreferences("dolos-control-"+pc.uuid,0);}
    private String endpoint()throws Exception{return BuildConfig.REMOTE_BUILD?parseHost(address).address:ServerHelper.getCurrentAddressFromComputer(pc).address;}
    private void verifyControl()throws Exception{
        getSharedPreferences("studio",0).edit().putString("lastUuid",pc.uuid).putString("lastHost",endpoint()).apply();
        ControlLink.request(endpoint(),"/status",null,control().getString("cert",null),control().getString("token",null));
        ui(()->move(3));
    }
    private void ui(Runnable r){runOnUiThread(()->{if(!dead&&!isFinishing())r.run();});}
    private interface Job{void run()throws Exception;}
    private void network(Job j){
        busy=true;feedback.setText("Verbindung wird geprüft …");
        tasks.execute(()->{try{j.run();}catch(Exception e){ui(()->feedback.setText("Verbindung fehlgeschlagen. "+(e.getMessage()==null?"PC-Adresse, Code und Heimnetz prüfen.":e.getMessage())));}finally{ui(()->busy=false);}});
    }
    private void discover(){
        network(()->{
            ui(()->feedback.setText("Suche nach Spiel-PCs im Heimnetz …"));
            MdnsDiscoveryListener listener=new MdnsDiscoveryListener(){
                public void notifyComputerAdded(MdnsComputer computer){}
                public void notifyDiscoveryFailure(Exception e){}
            };
            MdnsDiscoveryAgent search=Build.VERSION.SDK_INT>=34?new NsdManagerDiscoveryAgent(this,listener):new JmDNSDiscoveryAgent(this,listener);
            java.util.List<MdnsComputer> found;
            try{search.startDiscovery(1500);Thread.sleep(4500);found=search.getComputerSet();}
            finally{search.stopDiscovery();}
            java.util.List<String> labels=new java.util.ArrayList<>(),addresses=new java.util.ArrayList<>();
            for(MdnsComputer pc:found){
                InetAddress ip=pc.getLocalAddress()!=null?pc.getLocalAddress():pc.getIpv6Address();
                if(ip==null)continue;
                String addr=new ComputerDetails.AddressTuple(ip.getHostAddress(),pc.getPort()).toString();
                addresses.add(addr);labels.add(pc.getName()+"  ·  "+addr);
            }
            if(labels.isEmpty())throw new Exception("Kein Spiel-PC gefunden. Übernimm die Adresse aus Dolos-PC und tippe auf „PC verbinden“.");
            ui(()->new android.app.AlertDialog.Builder(this).setTitle("Spiel-PC wählen")
                .setItems(labels.toArray(new String[0]),(d,i)->{address=addresses.get(i);draw();connect();})
                .setNegativeButton("Abbrechen",null).show());
        });
    }
    static ComputerDetails.AddressTuple parseHost(String value)throws Exception{
        String text=value.trim();if(text.endsWith("/"))text=text.substring(0,text.length()-1);
        if(text.startsWith("https://")||text.contains("/pin"))throw new Exception("Das ist die Apollo-Webseite. Kopiere die Adresse aus Dolos-PC → Verbindung.");
        if(text.startsWith("http://"))text=text.substring(7);
        URI u;
        try{u=new URI("http://"+text);}catch(URISyntaxException e){throw new Exception("Übernimm nur die Heimnetzadresse aus Dolos-PC.");}
        if(u.getHost()==null||u.getUserInfo()!=null||!u.getPath().isEmpty()||u.getQuery()!=null||u.getFragment()!=null||u.getPort()>65535||u.getPort()==0)
            throw new Exception("Übernimm nur die Heimnetzadresse aus Dolos-PC.");
        if(u.getPort()==47990||u.getPort()==48291)throw new Exception("Dieser Port gehört zur Verwaltung. Verwende die Spiel-PC-Adresse aus Dolos-PC.");
        if("localhost".equalsIgnoreCase(u.getHost())||u.getHost().startsWith("127."))throw new Exception("Diese Adresse zeigt auf dein Android-Gerät. Verwende die Heimnetzadresse des PCs.");
        return new ComputerDetails.AddressTuple(u.getHost(),u.getPort()<0?NvHTTP.DEFAULT_HTTP_PORT:u.getPort());
    }
    private static void explainUnreachable(ComputerDetails.AddressTuple addr)throws Exception{
        try(Socket probe=new Socket()){probe.connect(new InetSocketAddress(addr.address,addr.port),2400);}
        catch(UnknownHostException e){throw new Exception("PC-Name unbekannt. Verwende die Zahlenadresse aus Dolos-PC.");}
        catch(ConnectException e){throw new Exception("Verbindung abgelehnt. Öffne am PC Dolos-PC → Verbindung → Erneut prüfen. Steht dort „Apollo bereit“, vergleiche die angezeigte Adresse.");}
        catch(java.io.IOException e){if(BuildConfig.REMOTE_BUILD)throw new Exception("PC nicht erreichbar. Ist er eingeschaltet und in Tailscale auf dem Handy online? Prüfe am PC Apollo und die Firewall-Freigabe für Tailscale.");throw new Exception("Keine Verbindung zu "+addr.address+". Prüfe zuerst das WLAN: Handy oder TV und PC müssen am selben Router sein. Gast-WLAN und mobile Daten trennen die Geräte. Steht am PC „Apollo bereit“, prüfe die Freigabe für Apollo im privaten Windows-Netz.");}
        throw new Exception("Der Port ist erreichbar, die Apollo-Spielverbindung kam nicht zustande. Vergleiche die Adresse mit Dolos-PC → Verbindung und prüfe dort erneut.");
    }
    private void connect(){
        network(()->{
            ComputerManagerService.ComputerManagerBinder service=manager;
            if(service==null)throw new Exception("PC-Dienst startet. Bitte erneut versuchen.");
            service.waitForReady();
            ComputerDetails d=new ComputerDetails();d.manualAddress=parseHost(address);
            if(setupNetwork!=null){setupNetwork.release(this);setupNetwork=null;}
            if(!BuildConfig.REMOTE_BUILD && (d.manualAddress.address.matches("[0-9.]+")||d.manualAddress.address.contains(":"))){
                com.limelight.utils.HomeNetwork lan=com.limelight.utils.HomeNetwork.select(this,d.manualAddress.address);
                if(lan==null||!lan.bind(this))throw new Exception("Kein direkter WLAN- oder Ethernet-Pfad zu dieser Adresse. Die Adresse aus Dolos-PC verwenden und das Gerät mit dem Heimnetz des PCs verbinden.");
                setupNetwork=lan;
            }
            ui(()->feedback.setText("Verbinde mit "+d.manualAddress.address+" …"));
            ComputerDetails.AddressTuple entered=d.manualAddress;
            if(!service.addComputerBlocking(d)){d.manualAddress=entered;if(!service.addComputerBlocking(d))explainUnreachable(entered);}
            NvHTTP http=new NvHTTP(BuildConfig.REMOTE_BUILD?entered:ServerHelper.getCurrentAddressFromComputer(d),d.httpsPort,service.getUniqueId(),d.serverCert,PlatformBinding.getCryptoProvider(this));
            if(http.getPairState()!=PairingManager.PairState.PAIRED || d.serverCert==null){
                String code=PairingManager.generatePinString();
                ui(()->feedback.setText("Deine vierstellige PIN: "+code+"\nLass diese Seite offen. Öffne am PC Dolos-PC → Verbindung → Apollo-PIN eingeben, trage die vier Ziffern ein und bestätige."));
                PairingManager pairing=http.getPairingManager();
                PairingManager.PairState result=pairing.pair(http.getServerInfo(true),code);
                if(result==PairingManager.PairState.PIN_WRONG)throw new Exception("PIN stimmt nicht. Erneut verbinden und die neue vierstellige PIN am PC eingeben.");
                if(result==PairingManager.PairState.ALREADY_IN_PROGRESS)throw new Exception("Apollo wartet auf eine andere Kopplung. Diese zuerst am PC abschließen.");
                if(result!=PairingManager.PairState.PAIRED)throw new Exception("Apollo hat die Kopplung nicht bestätigt. Am PC im Reiter PIN die Ziffern vom Android-Gerät bestätigen.");
                d.serverCert=pairing.getPairedCert();service.getComputer(d.uuid).serverCert=d.serverCert;
                service.invalidateStateForComputer(d.uuid);
                d.manualAddress=parseHost(address);
                if(!service.addComputerBlocking(d))throw new Exception("Gekoppelten PC erneut verbinden.");
            }
            if(BuildConfig.REMOTE_BUILD)getSharedPreferences("remote",0).edit().putString("host."+d.uuid,entered.address).putInt("port."+d.uuid,entered.port).apply();
            prefs.edit().putString("setupAddress",address).putString("host",d.uuid).apply();
            ui(()->{pc=d;fingerprint="";move(2);});
        });
    }
    private void complete(){
        prefs.edit().putBoolean("setup",true).apply();
        if(setupNetwork!=null){setupNetwork.release(this);setupNetwork=null;}
        if(pc!=null){Intent i=new Intent(this,AppView.class);i.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP);
            i.putExtra(AppView.UUID_EXTRA,pc.uuid);i.putExtra(AppView.NAME_EXTRA,pc.name);startActivity(i);overridePendingTransition(android.R.anim.fade_in,android.R.anim.fade_out);}
        finish();
    }
    @Override public void onBackPressed(){if(!busy&&step>0)move(step==3?(pc==null?1:2):step-1);else super.onBackPressed();}
    @Override public void onDestroy(){dead=true;tasks.shutdownNow();if(setupNetwork!=null){setupNetwork.release(this);setupNetwork=null;}if(bound)unbindService(connection);super.onDestroy();}
}
