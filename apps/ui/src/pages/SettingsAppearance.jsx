/**
 * ALPHA OMEGA - Appearance Settings Page
 * Category: 🎨 APPEARANCE (~55 settings)
 */

import React from 'react';
import { Box, Typography, Alert, Grid } from '@mui/material';
import {
  Palette,
  Brush,
  Animation,
  DesktopWindows,
} from '@mui/icons-material';
import {
  SettingsHeader,
  SettingsSection,
  ToggleSetting,
  SliderSetting,
  DropdownSetting,
  ColorSetting,
  SettingsActions,
  useSettings,
} from '../components/SettingsComponents';

export default function SettingsAppearance() {
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
  } = useSettings('appearance');

  if (loading) {
    return <Typography sx={{ color: '#888', p: 3 }}>Loading appearance settings...</Typography>;
  }

  return (
    <Box sx={{ p: 3, pb: 10 }}>
      <SettingsHeader
        title="Appearance Settings"
        description="Customize the visual interface, animations, and notifications"
        icon={<Palette sx={{ color: '#00e5ff', fontSize: 32 }} />}
      />

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <SettingsSection title="Theme">
        <DropdownSetting
          label="Theme Preset"
          description="Built-in theme selection"
          value={settings.theme || 'cyberpunk'}
          onChange={(v) => updateSetting('theme', v)}
          options={['cyberpunk', 'dark', 'light', 'midnight', 'neon', 'forest']}
        />

        <ToggleSetting
          label="Dark Mode"
          description="Use dark color scheme"
          value={settings.dark_mode !== false}
          onChange={(v) => updateSetting('dark_mode', v)}
        />

        <ColorSetting
          label="Accent Color"
          description="Primary color for UI elements"
          value={settings.accent_color || '#00e5ff'}
          onChange={(v) => updateSetting('accent_color', v)}
        />

        <DropdownSetting
          label="Background"
          description="Background style"
          value={settings.background || 'particles'}
          onChange={(v) => updateSetting('background', v)}
          options={['particles', 'gradient', 'solid', 'image']}
        />
      </SettingsSection>

      <SettingsSection title="Animations">
        <ToggleSetting
          label="Enable Animations"
          description="UI animations and transitions"
          value={settings.enable_animations !== false}
          onChange={(v) => updateSetting('enable_animations', v)}
        />

        <ToggleSetting
          label="Particle Effects"
          description="Background particle system"
          value={settings.particle_effects !== false}
          onChange={(v) => updateSetting('particle_effects', v)}
        />

        <ToggleSetting
          label="Parallax Effect"
          description="Mouse-based parallax movement"
          value={settings.parallax_effect !== false}
          onChange={(v) => updateSetting('parallax_effect', v)}
        />

        <SliderSetting
          label="Animation Speed"
          description="Speed multiplier"
          value={settings.animation_speed || 1.0}
          onChange={(v) => updateSetting('animation_speed', v)}
          min={0.5}
          max={2.0}
          step={0.1}
          unit="x"
        />
      </SettingsSection>

      <SettingsSection title="Interface">
        <ToggleSetting
          label="Always On Top"
          description="Keep window above others"
          value={settings.always_on_top || false}
          onChange={(v) => updateSetting('always_on_top', v)}
        />

        <SliderSetting
          label="Transparency"
          description="Window opacity"
          value={settings.transparency || 80}
          onChange={(v) => updateSetting('transparency', v)}
          min={0}
          max={100}
          unit="%"
        />

        <SliderSetting
          label="Font Size"
          description="Text size"
          value={settings.font_size || 14}
          onChange={(v) => updateSetting('font_size', v)}
          min={8}
          max={24}
          unit="px"
        />
      </SettingsSection>

      <SettingsSection title="Notifications">
        <ToggleSetting
          label="Sound Effects"
          description="UI sounds and feedback"
          value={settings.sound_effects !== false}
          onChange={(v) => updateSetting('sound_effects', v)}
        />

        <ToggleSetting
          label="Desktop Notifications"
          description="System notifications"
          value={settings.desktop_notifications !== false}
          onChange={(v) => updateSetting('desktop_notifications', v)}
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
