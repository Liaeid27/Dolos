package com.limelight;
import android.preference.*;
import com.limelight.preferences.*;
import org.json.*;

/** Uses the capability-filtered preferences and the same listeners used by streaming. */
public class StudioPreferences extends StreamSettings.SettingsFragment {
    JSONObject model() throws JSONException{
        JSONObject groups=new JSONObject();
        PreferenceScreen root=getPreferenceScreen();
        for(int i=0;i<root.getPreferenceCount();i++){
            PreferenceGroup category=(PreferenceGroup)root.getPreference(i);
            for(int n=0;n<category.getPreferenceCount();n++){
                Preference p=category.getPreference(n);String key=p.getKey();
                String group;
                if(key==null)group="controller";
                else if(key.equals("checkbox_host_audio")||category.getTitle().equals(getString(R.string.category_audio_settings)))group="audio";
                else if(category.getTitle().equals(getString(R.string.category_input_settings))||category.getTitle().equals(getString(R.string.category_gamepad_settings))||category.getTitle().equals(getString(R.string.category_on_screen_controls_settings)))group="controller";
                else if(category.getTitle().equals(getString(R.string.category_basic_settings))||"video_format".equals(key)||"checkbox_enable_hdr".equals(key)||"checkbox_full_range".equals(key))group="video";
                else group="advanced";
                JSONObject r=new JSONObject().put("key",key==null?"reset_osc":key).put("label",p.getTitle().toString()).put("enabled",p.isEnabled()).put("help",p.getSummary()==null?"":p.getSummary().toString());
                if(p instanceof ListPreference){
                    ListPreference list=(ListPreference)p;JSONArray choices=new JSONArray();
                    for(int k=0;k<list.getEntryValues().length;k++)choices.put(new JSONObject().put("id",list.getEntryValues()[k].toString()).put("title",list.getEntries()[k].toString()));
                    r.put("type","list").put("choices",choices).put("value",list.getValue());
                }else if(p instanceof CheckBoxPreference)r.put("type","switch").put("value",((CheckBoxPreference)p).isChecked());
                else if(p instanceof SeekBarPreference)((SeekBarPreference)p).describe(r);
                else if(p instanceof ConfirmDeleteOscPreference)r.put("type","reset");else continue;
                if(!groups.has(group))groups.put(group,new JSONArray());groups.getJSONArray(group).put(r);
            }
        }return groups;
    }
    void change(JSONObject row)throws Exception{
        String key=row.getString("key");if("reset_osc".equals(key)){
            ProfileSettings.group(getActivity(),"OSC").edit().clear().apply();return;
        }
        Preference p=findPreference(key);if(p==null||!p.isEnabled())return;
        if(p instanceof ListPreference){
            ListPreference list=(ListPreference)p;String value=row.getString("value");if(list.findIndexOfValue(value)>=0&&(p.getOnPreferenceChangeListener()==null||p.getOnPreferenceChangeListener().onPreferenceChange(p,value)))list.setValue(value);
        }else if(p instanceof CheckBoxPreference){boolean v=row.getBoolean("value");if((p.getOnPreferenceChangeListener()==null||p.getOnPreferenceChangeListener().onPreferenceChange(p,v)))((CheckBoxPreference)p).setChecked(v);}
        else if(p instanceof SeekBarPreference)((SeekBarPreference)p).setStudioValue(row.getInt("value"));
    }
}
