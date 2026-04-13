/**
 * ALPHA OMEGA - Integrations Settings Page
 * Category: 🔌 INTEGRATIONS (~45 settings)
 */

import React from 'react';
import { Box, Typography, Alert, Grid, Button } from '@mui/material';
import {
  Extension,
  MusicNote,
  Cast,
  Home,
} from '@mui/icons-material';
import {
  SettingsHeader,
  SettingsSection,
  ToggleSetting,
  TextSetting,
  PasswordSetting,
  SettingsActions,
  useSettings,
} from '../components/SettingsComponents';

export default function SettingsIntegrations() {
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
  } = useSettings('integrations');

  if (loading) {
    return <Typography sx={{ color: '#888', p: 3 }}>Loading integrations settings...</Typography>;
  }

  return (
    <Box sx={{ p: 3, pb: 10 }}>
      <SettingsHeader
        title="Integrations Settings"
        description="Connect with apps, smart home, and external services"
        icon={<Extension sx={{ color: '#00e5ff', fontSize: 32 }} />}
      />

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <SettingsSection title="Apps">
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <ToggleSetting
              label="Discord"
              description="Discord controls and status"
              value={settings.discord_integration || false}
              onChange={(v) => updateSetting('discord_integration', v)}
            />
          </Grid>
          <Grid item xs={12} md={6}>
            <ToggleSetting
              label="Spotify"
              description="Music playback control"
              value={settings.spotify_integration !== false}
              onChange={(v) => updateSetting('spotify_integration', v)}
            />
          </Grid>
          <Grid item xs={12} md={6}>
            <ToggleSetting
              label="OBS"
              description="Streaming control"
              value={settings.obs_integration || false}
              onChange={(v) => updateSetting('obs_integration', v)}
            />
          </Grid>
          <Grid item xs={12} md={6}>
            <ToggleSetting
              label="Steam"
              description="Game library"
              value={settings.steam_integration !== false}
              onChange={(v) => updateSetting('steam_integration', v)}
            />
          </Grid>
          <Grid item xs={12} md={6}>
            <ToggleSetting
              label="VS Code"
              description="Code editor integration"
              value={settings.vscode_integration !== false}
              onChange={(v) => updateSetting('vscode_integration', v)}
            />
          </Grid>
          <Grid item xs={12} md={6}>
            <ToggleSetting
              label="Chrome"
              description="Browser control"
              value={settings.chrome_integration !== false}
              onChange={(v) => updateSetting('chrome_integration', v)}
            />
          </Grid>
        </Grid>
      </SettingsSection>

      <SettingsSection title="Smart Home">
        <ToggleSetting
          label="Home Assistant"
          description="Connect to Home Assistant"
          value={settings.home_assistant || false}
          onChange={(v) => updateSetting('home_assistant', v)}
        />

        {settings.home_assistant && (
          <>
            <TextSetting
              label="Home Assistant URL"
              description="e.g., http://homeassistant.local:8123"
              value={settings.ha_url || ''}
              onChange={(v) => updateSetting('ha_url', v)}
            />

            <PasswordSetting
              label="Home Assistant Token"
              description="Long-lived access token"
              value={settings.ha_token || ''}
              onChange={(v) => updateSetting('ha_token', v)}
            />
          </>
        )}

        <ToggleSetting
          label="Philips Hue"
          description="Light control"
          value={settings.philips_hue || false}
          onChange={(v) => updateSetting('philips_hue', v)}
        />
      </SettingsSection>

      <SettingsSection title="Calendar & Email">
        <ToggleSetting
          label="Google Calendar"
          description="Calendar access"
          value={settings.google_calendar || false}
          onChange={(v) => updateSetting('google_calendar', v)}
        />

        <ToggleSetting
          label="Outlook Calendar"
          description="Microsoft calendar"
          value={settings.outlook_calendar || false}
          onChange={(v) => updateSetting('outlook_calendar', v)}
        />

        <ToggleSetting
          label="Email Notifications"
          description="Email alerts"
          value={settings.email_notifications || false}
          onChange={(v) => updateSetting('email_notifications', v)}
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
