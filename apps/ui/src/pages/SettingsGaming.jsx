/**
 * ALPHA OMEGA - Gaming Settings Page
 * Category: 🎮 GAMING (~35 settings)
 */

import React from 'react';
import { Box, Typography, Alert, Grid } from '@mui/material';
import {
  SportsEsports,
  Speed,
  Keyboard,
  Monitor,
} from '@mui/icons-material';
import {
  SettingsHeader,
  SettingsSection,
  ToggleSetting,
  SliderSetting,
  SettingsActions,
  useSettings,
} from '../components/SettingsComponents';

export default function SettingsGaming() {
  const {
    settings,
    schema,
    loading,
    saving,
    error,
    hasChanges,
    updateSetting,
    saveSettings,
    resetSettings,
    revertChanges,
  } = useSettings('gaming');

  if (loading) {
    return <Typography sx={{ color: '#888', p: 3 }}>Loading gaming settings...</Typography>;
  }

  return (
    <Box sx={{ p: 3, pb: 10 }}>
      <SettingsHeader
        title="Gaming Settings"
        description="Configure game detection, performance mode, and in-game voice commands"
        icon={<SportsEsports sx={{ color: '#00e5ff', fontSize: 32 }} />}
      />

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <SettingsSection title="Game Detection">
        <ToggleSetting
          label="Auto Detect Games"
          description="Automatically recognize when gaming"
          value={settings.game_detection !== false}
          onChange={(v) => updateSetting('game_detection', v)}
        />

        <ToggleSetting
          label="Performance Mode"
          description="Boost performance when gaming"
          value={settings.performance_mode !== false}
          onChange={(v) => updateSetting('performance_mode', v)}
        />
      </SettingsSection>

      <SettingsSection title="Voice Commands">
        <ToggleSetting
          label="In-Game Voice"
          description="Voice commands during gameplay"
          value={settings.in_game_voice !== false}
          onChange={(v) => updateSetting('in_game_voice', v)}
        />

        <SliderSetting
          label="Noise Gate"
          description="Silence threshold for voice"
          value={settings.noise_gate || 50}
          onChange={(v) => updateSetting('noise_gate', v)}
          min={0}
          max={100}
        />
      </SettingsSection>

      <SettingsSection title="Macros">
        <ToggleSetting
          label="Enable Macros"
          description="Allow game macros"
          value={settings.enable_macros || false}
          onChange={(v) => updateSetting('enable_macros', v)}
          warning="Macros may violate anti-cheat in some games"
        />

        <ToggleSetting
          label="Anti-Cheat Safe"
          description="Only use safe macros"
          value={settings.anti_cheat_safe !== false}
          onChange={(v) => updateSetting('anti_cheat_safe', v)}
        />
      </SettingsSection>

      <SettingsSection title="Monitoring">
        <ToggleSetting
          label="FPS Overlay"
          description="Show FPS counter"
          value={settings.fps_overlay || false}
          onChange={(v) => updateSetting('fps_overlay', v)}
        />

        <ToggleSetting
          label="Temperature Monitor"
          description="Track GPU temperature"
          value={settings.temp_monitor !== false}
          onChange={(v) => updateSetting('temp_monitor', v)}
        />
      </SettingsSection>

      <SettingsActions
        hasChanges={hasChanges}
        saving={saving}
        onSave={saveSettings}
        onReset={resetSettings}
        onRevert={revertChanges}
      />
    </Box>
  );
}
