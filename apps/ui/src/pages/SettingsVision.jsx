/**
 * ALPHA OMEGA - Vision Settings Page
 * Category: 👁️ VISION (~40 settings)
 */

import React from 'react';
import { Box, Typography, Alert, Grid } from '@mui/material';
import {
  Visibility,
  Camera,
  Ocr,
  Security,
} from '@mui/icons-material';
import {
  SettingsHeader,
  SettingsSection,
  ToggleSetting,
  SliderSetting,
  DropdownSetting,
  TextSetting,
  SettingsActions,
  useSettings,
} from '../components/SettingsComponents';

export default function SettingsVision() {
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
  } = useSettings('vision');

  if (loading) {
    return <Typography sx={{ color: '#888', p: 3 }}>Loading vision settings...</Typography>;
  }

  return (
    <Box sx={{ p: 3, pb: 10 }}>
      <SettingsHeader
        title="Vision Settings"
        description="Configure screen analysis, OCR, and object detection"
        icon={<Visibility sx={{ color: '#00e5ff', fontSize: 32 }} />}
      />

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <SettingsSection title="Screen Analysis">
        <ToggleSetting
          label="Enable Vision"
          description="Allow screen reading and analysis"
          value={settings.enable_vision !== false}
          onChange={(v) => updateSetting('enable_vision', v)}
        />

        <DropdownSetting
          label="OCR Engine"
          description="Text recognition engine"
          value={settings.ocr_engine || 'tesseract'}
          onChange={(v) => updateSetting('ocr_engine', v)}
          options={['tesseract', 'easyocr']}
        />

        <SliderSetting
          label="Screenshot Interval"
          description="Auto-capture rate (0 = disabled)"
          value={settings.screenshot_interval || 0}
          onChange={(v) => updateSetting('screenshot_interval', v)}
          min={0}
          max={60}
          unit="s"
        />

        <ToggleSetting
          label="Active Window Only"
          description="Only capture the active window"
          value={settings.active_window_only !== false}
          onChange={(v) => updateSetting('active_window_only', v)}
        />
      </SettingsSection>

      <SettingsSection title="Object Detection">
        <ToggleSetting
          label="Enable Object Detection"
          description="Recognize objects in screen"
          value={settings.object_detection || false}
          onChange={(v) => updateSetting('object_detection', v)}
        />

        <ToggleSetting
          label="Face Detection"
          description="Detect faces"
          value={settings.face_detection || false}
          onChange={(v) => updateSetting('face_detection', v)}
        />

        <ToggleSetting
          label="Gesture Recognition"
          description="Recognize hand gestures"
          value={settings.gesture_recognition || false}
          onChange={(v) => updateSetting('gesture_recognition', v)}
        />
      </SettingsSection>

      <SettingsSection title="Privacy">
        <ToggleSetting
          label="Blur Sensitive Content"
          description="Blur passwords and sensitive text"
          value={settings.blur_sensitive !== false}
          onChange={(v) => updateSetting('blur_sensitive', v)}
        />

        <TextSetting
          label="Excluded Apps"
          description="Apps to never capture (comma-separated)"
          value={settings.exclude_apps || ''}
          onChange={(v) => updateSetting('exclude_apps', v)}
          placeholder="Password Manager, Banking App"
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
