package com.limelight;

import android.app.Activity;
import android.app.Dialog;
import android.content.ActivityNotFoundException;
import android.content.Context;
import android.content.Intent;
import android.hardware.input.InputManager;
import android.provider.Settings;
import android.view.InputDevice;
import android.widget.TextView;
import android.widget.Toast;

final class ControllerPairing {
    static InputDevice connected() {
        InputDevice first = null;
        for (int id : InputDevice.getDeviceIds()) {
            InputDevice device = InputDevice.getDevice(id);
            if (device == null || device.isVirtual()) continue;
            int sources = device.getSources();
            if ((sources & InputDevice.SOURCE_GAMEPAD) != InputDevice.SOURCE_GAMEPAD &&
                    (sources & InputDevice.SOURCE_JOYSTICK) != InputDevice.SOURCE_JOYSTICK) continue;
            if (device.getName().toLowerCase(java.util.Locale.ROOT).contains("stadia")) return device;
            if (first == null) first = device;
        }
        return first;
    }

    static void show(Activity activity) {
        if (android.os.Build.VERSION.SDK_INT < 17) { openSettings(activity, false); return; }
        InputManager manager = (InputManager) activity.getSystemService(Context.INPUT_SERVICE);
        TextView details = new TextView(activity);
        Runnable refresh = () -> {
            InputDevice device = connected();
            String status = device == null ? "Android erkennt noch kein Gamepad." : "Als Gamepad erkannt: " + device.getName();
            details.setText(status + "\n\nStadia-Controller: Stadia + Y etwa 2 Sekunden halten, bis die Taste orange blinkt. Unter „Zubehör koppeln“ den Stadia Controller auswählen und die Kopplung bestätigen."
                    + "\n\nSchon gekoppelt? Zum Wiederverbinden die Stadia-Taste halten, bis sie weiß blinkt. Bleibt die Verbindung aus, unter „Gekoppelte Geräte“ den alten Stadia-Eintrag entfernen und erneut koppeln.");
        };
        refresh.run();
        Dialog guide = ConsoleDock.panel(activity, "Controller verbinden", details,
                new String[]{"Zubehör koppeln", "Gekoppelte Geräte", "Fertig"}, index -> {
                    if (index < 2) openSettings(activity, index == 0);
                }, 2);
        if (manager == null) return;
        InputManager.InputDeviceListener listener = new InputManager.InputDeviceListener() {
            public void onInputDeviceAdded(int id) { refresh.run(); }
            public void onInputDeviceChanged(int id) { refresh.run(); }
            public void onInputDeviceRemoved(int id) { refresh.run(); }
        };
        manager.registerInputDeviceListener(listener, new android.os.Handler(activity.getMainLooper()));
        guide.setOnDismissListener(d -> manager.unregisterInputDeviceListener(listener));
    }

    private static void openSettings(Activity activity, boolean pair) {
        String[] actions = pair && ConsoleDock.isTV(activity)
                ? new String[]{"com.google.android.intent.action.CONNECT_INPUT", Settings.ACTION_BLUETOOTH_SETTINGS, Settings.ACTION_SETTINGS}
                : new String[]{Settings.ACTION_BLUETOOTH_SETTINGS, Settings.ACTION_SETTINGS};
        for (String action : actions) {
            try { activity.startActivity(new Intent(action)); return; }
            catch (ActivityNotFoundException | SecurityException ignored) { }
        }
        Toast.makeText(activity, "In den Einstellungen der Box „Fernbedienungen und Zubehör“ öffnen.", Toast.LENGTH_LONG).show();
    }
}
