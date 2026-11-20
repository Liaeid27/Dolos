package com.limelight;

import android.app.Activity;
import android.app.AlertDialog;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.Robolectric;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.annotation.Config;
import org.robolectric.shadows.ShadowAlertDialog;
import static org.junit.Assert.*;

@RunWith(RobolectricTestRunner.class)
@Config(sdk=28)
public class ConsoleHomeTest {
    private final ConsoleHome.Actions actions = new ConsoleHome.Actions() {
        public void play(AppView.AppObject game) { }
        public void quit() { }
    };
    @Test public void profileChangeKeepsLibraryAndSeparatesAppearance() {
        Activity activity=Robolectric.buildActivity(Activity.class).setup().get();
        ConsoleHome home=new ConsoleHome(activity,"Wohnzimmer",actions);
        activity.setContentView(home);
        assertEquals(0,home.profile);
        home.chooseProfile();
        android.app.Dialog profiles=org.robolectric.shadows.ShadowDialog.getLatestDialog();
        java.util.ArrayList<View> buttons=new java.util.ArrayList<>();
        profiles.getWindow().getDecorView().findViewsWithText(buttons,"Spieler 2",View.FIND_VIEWS_WITH_TEXT);
        buttons.get(0).performClick();
        assertTrue(home.belongsToProfile(new AppView.AppObject(new com.limelight.nvstream.http.NvApp("Subnautica [AC:264710:installed]",12,false))));
        ConsoleHome.appearance(activity).edit().putString("theme","enhanced").commit();
        assertFalse(activity.getSharedPreferences("studio",0).contains("theme"));
        assertEquals(1,home.profile);
        assertEquals("Spieler 2",home.profileName(home.profile));
        assertEquals(1,new ConsoleHome(activity,"Wohnzimmer",actions).profile);
    }
    @Test public void catalogKeepsSteamIdentityAfterInstallation() {
        assertEquals("Terraria",Catalog.title("Terraria [AC:105600:owned]"));
        assertEquals(Catalog.steamId("Terraria [AC:105600:owned]"),Catalog.steamId("Terraria [AC:105600:installed]"));
        assertTrue(Catalog.remote("Terraria [AC:105600:owned]"));
        assertFalse(Catalog.remote("Terraria [AC:105600:installed]"));
        assertEquals("host",Catalog.state("Steam Big Picture"));
    }
    @Test public void installedTitleRequiresExplicitSelection() {
        Activity activity=Robolectric.buildActivity(Activity.class).setup().get();
        ConsoleHome home=new ConsoleHome(activity,"PC",actions);
        AppView.AppObject game=new AppView.AppObject(new com.limelight.nvstream.http.NvApp("Subnautica [AC:264710:installed]",12,false));
        assertFalse(home.onShelf(game,home.hiddenTiles(),home.extraPins()));
        home.setPinned(game,true);
        assertTrue(home.onShelf(game,home.hiddenTiles(),home.extraPins()));
        home.setPinned(game,false);
        assertFalse(home.onShelf(game,home.hiddenTiles(),home.extraPins()));
    }
    @Test @Config(qualifiers="port") public void firstConnectionUsesDolosControlsInPortrait(){
        Activity a=Robolectric.buildActivity(Activity.class).setup().get();
        a.setContentView(R.layout.activity_pc_view);
        assertEquals("IP eingeben",((Button)a.findViewById(R.id.manuallyAddPc)).getText());
        assertEquals("Einrichtung",((Button)a.findViewById(R.id.helpButton)).getText());
        assertNotNull(a.findViewById(R.id.pcFragmentContainer));
        assertTrue(a.findViewById(R.id.no_pc_found_layout).isShown());
    }
    private static android.widget.TextView text(View view,String title){
        if(view instanceof android.widget.TextView && title.contentEquals(((android.widget.TextView)view).getText()))return (android.widget.TextView)view;
        if(view instanceof ViewGroup){ViewGroup group=(ViewGroup)view;for(int i=0;i<group.getChildCount();i++){
            android.widget.TextView found=text(group.getChildAt(i),title);if(found!=null)return found;
        }}
        return null;
    }
    @Test @Config(qualifiers="port") public void setupAcceptsTouchAndCanDeferHost(){
        SetupGuide guide=Robolectric.buildActivity(SetupGuide.class).setup().get();
        View root=guide.getWindow().getDecorView();
        text(root,"Eingabe testen").performClick();
        assertNotNull(text(root,"Eingabe erkannt. Du kannst fortfahren."));
        text(root,"Weiter").performClick();assertNotNull(text(root,"PC verbinden"));
        text(root,"Später einrichten").performClick();assertNotNull(text(root,"Zur PC-Auswahl"));
        assertNull(text(root,"Konsole öffnen"));text(root,"Zur PC-Auswahl").performClick();assertTrue(guide.isFinishing());
    }
    @Test public void setupUnderstandsPastedAddressesAndExplainsManagementPort() throws Exception {
        assertEquals(47989,SetupGuide.parseHost(" http://192.168.1.8/ ").port);
        assertEquals(48089,SetupGuide.parseHost("gaming-pc:48089").port);
        try {SetupGuide.parseHost("192.168.1.8:47990");fail();}
        catch(Exception e){assertTrue(e.getMessage().contains("Verwaltung"));}
        try {SetupGuide.parseHost("localhost");fail();}
        catch(Exception e){assertTrue(e.getMessage().contains("Android"));}
    }
    @Test public void bootOverlayCanBeRemovedFromActivity() {
        Activity activity=Robolectric.buildActivity(Activity.class).setup().get();
        android.widget.FrameLayout layer=ConsoleBoot.curtain(activity,"ASTER");
        assertNotNull(layer.getParent());
        ConsoleBoot.remove(layer);
        assertNull(layer.getParent());
    }
}

