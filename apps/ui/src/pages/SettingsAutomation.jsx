/**
 * ALPHA OMEGA - Automation Settings Page
 * Category: ⚙️ AUTOMATION (~70 settings)
 */

import React from 'react';
import { Box, Typography, Alert, Grid } from '@mui/material';
import {
  Settings as SettingsIcon,
  Mouse,
  Power,
  Folder,
  Web,
} from '@mui/icons-material';
import {
  SettingsHeader,
  SettingsSection,
  ToggleSetting,
  SliderSetting,
  TextSetting,
  SettingsActions,
  useSettings,
} from '../components/SettingsComponents';

export default function SettingsAutomation() {
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
  } = useSettings('automation');

  if (loading) {
    return <Typography sx={{ color: '#888', p: 3 }}>Loading automation settings...</Typography>;
  }

  return (
    <Box sx={{ p: 3, pb: 10 }}>
      <SettingsHeader
        title="Automation Settings"
        description="Configure GUI automation, file operations, and system control"
        icon={<SettingsIcon sx={{ color: '#00e5ff', fontSize: 32 }} />}
      />

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <SettingsSection title="GUI Automation">
        <ToggleSetting
          label="Enable GUI Automation"
          description="Allow mouse and keyboard control"
          value={settings.gui_automation !== false}
          onChange={(v) => updateSetting('gui_automation', v)}
        />

        <Grid container spacing={2}>
          <Grid item xs={6}>
            <SliderSetting
              label="Type Speed"
              description="Delay between keystrokes (ms)"
              value={settings.type_speed || 10}
              onChange={(v) => updateSetting('type_speed', v)}
              min={0}
              max={100}
              unit="ms"
            />
          </Grid>
          <Grid item xs={6}>
            <SliderSetting
              label="Mouse Speed"
              description="Movement smoothness"
              value={settings.mouse_speed || 5}
              onChange={(v) => updateSetting('mouse_speed', v)}
              min={1}
              max={10}
            />
          </Grid>
        </Grid>
      </SettingsSection>

      <SettingsSection title="System Commands">
        <ToggleSetting
          label="Allow Shutdown"
          description="Can shut down the PC"
          value={settings.allow_shutdown || false}
          onChange={(v) => updateSetting('allow_shutdown', v)}
          warning="This allows the assistant to shut down your computer"
        />

        <ToggleSetting
          label="Allow Restart"
          description="Can restart the PC"
          value={settings.allow_restart !== false}
          onChange={(v) => updateSetting('allow_restart', v)}
        />

        <ToggleSetting
          label="Allow Sleep"
          description="Can put PC to sleep"
          value={settings.allow_sleep !== false}
          onChange={(v) => updateSetting('allow_sleep', v)}
        />

        <ToggleSetting
          label="Allow Lock"
          description="Can lock workstation"
          value={settings.allow_lock !== false}
          onChange={(v) => updateSetting('allow_lock', v)}
        />

        <SliderSetting
          label="Shutdown Timeout"
          description="Seconds before executing shutdown"
          value={settings.shutdown_timeout || 30}
          onChange={(v) => updateSetting('shutdown_timeout', v)}
          min={0}
          max={300}
          unit="s"
        />
      </SettingsSection>

      <SettingsSection title="File Operations">
        <ToggleSetting
          label="Allow Create"
          description="Create new files"
          value={settings.file_create !== false}
          onChange={(v) => updateSetting('file_create', v)}
        />

        <ToggleSetting
          label="Allow Modify"
          description="Modify existing files"
          value={settings.file_modify !== false}
          onChange={(v) => updateSetting('file_modify', v)}
        />

        <ToggleSetting
          label="Allow Delete"
          description="Delete files (dangerous)"
          value={settings.file_delete || false}
          onChange={(v) => updateSetting('file_delete', v)}
          warning="Deleted files cannot be recovered easily"
        />

        <ToggleSetting
          label="Auto Backup"
          description="Create backup before modifications"
          value={settings.auto_backup !== false}
          onChange={(v) => updateSetting('auto_backup', v)}
        />

        <TextSetting
          label="Backup Location"
          description="Where to store backups"
          value={settings.backup_location || './backups'}
          onChange={(v) => updateSetting('backup_location', v)}
        />
      </SettingsSection>

      <SettingsSection title="Web Automation">
        <ToggleSetting
          label="Browser Control"
          description="Control web browser"
          value={settings.browser_control !== false}
          onChange={(v) => updateSetting('browser_control', v)}
        />

        <ToggleSetting
          label="Form Filling"
          description="Auto-fill web forms"
          value={settings.form_filling !== false}
          onChange={(v) => updateSetting('form_filling', v)}
        />

        <ToggleSetting
          label="Screenshot Capture"
          description="Take screenshots"
          value={settings.screenshot_capture !== false}
          onChange={(v) => updateSetting('screenshot_capture', v)}
        />
      </SettingsSection>

      <SettingsSection title="Workflows">
        <SliderSetting
          label="Max Concurrent Tasks"
          description="Parallel workflow executions"
          value={settings.max_concurrent_tasks || 5}
          onChange={(v) => updateSetting('max_concurrent_tasks', v)}
          min={1}
          max={10}
        />

        <SliderSetting
          label="Workflow Timeout"
          description="Maximum execution time"
          value={settings.workflow_timeout || 10}
          onChange={(v) => updateSetting('workflow_timeout', v)}
          min={1}
          max={60}
          unit=" min"
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
