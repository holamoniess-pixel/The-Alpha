/**
 * ALPHA OMEGA - Voice Settings Page
 * Category: 🎙️ VOICE (~50 settings)
 */

import React from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
} from '@mui/material';
import {
  Mic,
  MicOff,
  RecordVoiceOver,
  VolumeUp,
  Settings as SettingsIcon,
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

export default function SettingsVoice() {
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
  } = useSettings('voice');

  const [enrollDialog, setEnrollDialog] = React.useState(false);
  const [recording, setRecording] = React.useState(false);

  const handleEnrollVoice = async () => {
    setRecording(true);
    try {
      const response = await fetch('http://localhost:8000/enroll', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: 'default' }),
      });
      const data = await response.json();
      alert(data.message || 'Voice enrolled successfully');
    } catch (err) {
      alert('Failed to enroll voice: ' + err.message);
    } finally {
      setRecording(false);
      setEnrollDialog(false);
    }
  };

  if (loading) {
    return <Typography sx={{ color: '#888', p: 3 }}>Loading voice settings...</Typography>;
  }

  return (
    <Box sx={{ p: 3, pb: 10 }}>
      <SettingsHeader
        title="Voice Settings"
        description="Configure voice recognition, text-to-speech, and wake word detection"
        icon={<Mic sx={{ color: '#00e5ff', fontSize: 32 }} />}
      />

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <SettingsSection title="Wake Word">
        <TextSetting
          label="Wake Word"
          description="Phrase to activate the assistant"
          value={settings.wake_word || 'hey alpha'}
          onChange={(v) => updateSetting('wake_word', v)}
        />

        <SliderSetting
          label="Wake Sensitivity"
          description="How sensitive the system is to detecting the wake word"
          value={settings.wake_sensitivity || 80}
          onChange={(v) => updateSetting('wake_sensitivity', v)}
          min={0}
          max={100}
          unit="%"
        />

        <ToggleSetting
          label="Barge-In"
          description="Interrupt TTS playback with voice command"
          value={settings.barge_in !== false}
          onChange={(v) => updateSetting('barge_in', v)}
        />
      </SettingsSection>

      <SettingsSection title="Voice Recognition">
        <DropdownSetting
          label="Voice Engine"
          description="Speech-to-text engine"
          value={settings.voice_engine || 'whisper-base'}
          onChange={(v) => updateSetting('voice_engine', v)}
          options={['whisper-tiny', 'whisper-base', 'whisper-small', 'whisper-medium', 'vosk']}
        />

        <DropdownSetting
          label="Language"
          description="Recognition language"
          value={settings.language || 'en-US'}
          onChange={(v) => updateSetting('language', v)}
          options={['en-US', 'en-GB', 'es-ES', 'fr-FR', 'de-DE', 'it-IT', 'pt-BR', 'ja-JP', 'ko-KR', 'zh-CN']}
        />

        <DropdownSetting
          label="Sample Rate"
          description="Audio sample rate (higher = better quality)"
          value={settings.sample_rate || '16000'}
          onChange={(v) => updateSetting('sample_rate', v)}
          options={['8000', '16000', '22050', '44100']}
        />

        <ToggleSetting
          label="Noise Reduction"
          description="Filter background noise for clearer recognition"
          value={settings.noise_reduction !== false}
          onChange={(v) => updateSetting('noise_reduction', v)}
        />

        <ToggleSetting
          label="Offline Voice"
          description="Use local models only (no cloud)"
          value={settings.offline_voice !== false}
          onChange={(v) => updateSetting('offline_voice', v)}
        />
      </SettingsSection>

      <SettingsSection title="Text-to-Speech">
        <SliderSetting
          label="Voice Speed"
          description="Speaking rate (1.0 = normal)"
          value={settings.voice_speed || 1.0}
          onChange={(v) => updateSetting('voice_speed', v)}
          min={0.5}
          max={2.0}
          step={0.1}
          unit="x"
        />

        <SliderSetting
          label="Voice Pitch"
          description="Voice pitch level"
          value={settings.voice_pitch || 50}
          onChange={(v) => updateSetting('voice_pitch', v)}
          min={0}
          max={100}
        />
      </SettingsSection>

      <SettingsSection title="Command Listening">
        <SliderSetting
          label="Command Timeout"
          description="Seconds to listen after wake word"
          value={settings.command_timeout || 10}
          onChange={(v) => updateSetting('command_timeout', v)}
          min={1}
          max={30}
          unit="s"
        />
      </SettingsSection>

      <SettingsSection title="Voice Authentication">
        <ToggleSetting
          label="Enable Voice Authentication"
          description="Verify speaker identity before executing commands"
          value={settings.voice_auth_enabled || false}
          onChange={(v) => updateSetting('voice_auth_enabled', v)}
          warning="Requires voice enrollment before activation"
        />

        {settings.voice_auth_enabled && (
          <Box sx={{ mt: 2 }}>
            <Button
              variant="outlined"
              startIcon={<RecordVoiceOver />}
              onClick={() => setEnrollDialog(true)}
              sx={{
                borderColor: '#00e5ff',
                color: '#00e5ff',
                '&:hover': { borderColor: '#00b8d4', background: 'rgba(0, 229, 255, 0.1)' },
              }}
            >
              Enroll Voice Profile
            </Button>
          </Box>
        )}
      </SettingsSection>

      <SettingsActions
        hasChanges={hasChanges}
        saving={saving}
        onSave={saveSettings}
        onReset={resetSettings}
        onRevert={revertChanges}
      />

      <Dialog open={enrollDialog} onClose={() => setEnrollDialog(false)}>
        <DialogTitle sx={{ color: '#00e5ff' }}>Voice Enrollment</DialogTitle>
        <DialogContent>
          <Typography sx={{ color: '#888', mb: 2 }}>
            Speak clearly for 5 seconds to create your voice profile.
          </Typography>
          {recording && (
            <Alert severity="info">
              Recording... Speak now!
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEnrollDialog(false)} sx={{ color: '#888' }}>
            Cancel
          </Button>
          <Button
            onClick={handleEnrollVoice}
            disabled={recording}
            sx={{ color: '#00e5ff' }}
          >
            {recording ? 'Recording...' : 'Start Recording'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
