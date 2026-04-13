/**
 * ALPHA OMEGA - Security Settings Page
 * Category: 🔒 SECURITY (~60 settings)
 */

import React from 'react';
import {
  Box,
  Typography,
  Alert,
  Grid,
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
  LinearProgress,
} from '@mui/material';
import {
  Security,
  Shield,
  Lock,
  Delete,
  Add,
  Refresh,
} from '@mui/icons-material';
import {
  SettingsHeader,
  SettingsSection,
  ToggleSetting,
  SliderSetting,
  SettingsActions,
  useSettings,
} from '../components/SettingsComponents';

export default function SettingsSecurity() {
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
    refresh,
  } = useSettings('security');

  const [enrollDialog, setEnrollDialog] = React.useState(false);
  const [profiles, setProfiles] = React.useState([]);
  const [quarantineFiles, setQuarantineFiles] = React.useState([]);

  React.useEffect(() => {
    fetchProfiles();
    fetchQuarantine();
  }, []);

  const fetchProfiles = async () => {
    try {
      const res = await fetch('http://localhost:8000/security/voice-profiles');
      const data = await res.json();
      setProfiles(data.profiles || []);
    } catch (err) {
      console.error('Failed to fetch profiles:', err);
    }
  };

  const fetchQuarantine = async () => {
    try {
      const res = await fetch('http://localhost:8000/security/quarantine');
      const data = await res.json();
      setQuarantineFiles(data.files || []);
    } catch (err) {
      console.error('Failed to fetch quarantine:', err);
    }
  };

  const handleDeleteProfile = async (userId) => {
    if (!confirm(`Delete voice profile for ${userId}?`)) return;
    try {
      await fetch(`http://localhost:8000/security/voice-profiles/${userId}`, {
        method: 'DELETE',
      });
      fetchProfiles();
    } catch (err) {
      alert('Failed to delete profile');
    }
  };

  const handleRestoreQuarantine = async (filename) => {
    try {
      await fetch(`http://localhost:8000/security/quarantine/restore`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename }),
      });
      fetchQuarantine();
    } catch (err) {
      alert('Failed to restore file');
    }
  };

  const handleClearQuarantine = async () => {
    if (!confirm('Delete all quarantined files?')) return;
    try {
      await fetch('http://localhost:8000/security/quarantine/clear', {
        method: 'POST',
      });
      setQuarantineFiles([]);
    } catch (err) {
      alert('Failed to clear quarantine');
    }
  };

  if (loading) {
    return <Typography sx={{ color: '#888', p: 3 }}>Loading security settings...</Typography>;
  }

  return (
    <Box sx={{ p: 3, pb: 10 }}>
      <SettingsHeader
        title="Security Settings"
        description="Configure threat protection, authentication, and access control"
        icon={<Security sx={{ color: '#00e5ff', fontSize: 32 }} />}
      />

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <SettingsSection title="Voice Authentication">
        <ToggleSetting
          label="Enable Voice Authentication"
          description="Verify speaker identity before executing commands"
          value={settings.voice_auth_enabled || false}
          onChange={(v) => updateSetting('voice_auth_enabled', v)}
        />

        <ToggleSetting
          label="Windows Login Bypass"
          description="Replace Windows password login with voice authentication"
          value={settings.windows_login_bypass || false}
          onChange={(v) => updateSetting('windows_login_bypass', v)}
          warning="Requires administrator privileges. Self-signed certificate will show security warning."
        />

        {settings.voice_auth_enabled && (
          <>
            <SliderSetting
              label="Authentication Threshold"
              description="Similarity threshold for voice verification"
              value={settings.auth_threshold || 65}
              onChange={(v) => updateSetting('auth_threshold', v)}
              min={50}
              max={99}
              unit="%"
            />

            <SliderSetting
              label="Max Authentication Attempts"
              description="Failed attempts before lockout"
              value={settings.max_auth_attempts || 3}
              onChange={(v) => updateSetting('max_auth_attempts', v)}
              min={1}
              max={10}
            />

            <Box sx={{ mt: 2 }}>
              <Typography variant="subtitle2" sx={{ color: '#00e5ff', mb: 1 }}>
                Voice Profiles
              </Typography>
              <List sx={{ background: 'rgba(0,0,0,0.3)', borderRadius: 1 }}>
                {profiles.length === 0 ? (
                  <ListItem>
                    <ListItemText
                      primary="No voice profiles enrolled"
                      primaryTypographyProps={{ sx: { color: '#666' } }}
                    />
                  </ListItem>
                ) : (
                  profiles.map((profile) => (
                    <ListItem key={profile.user_id}>
                      <ListItemText
                        primary={profile.user_id}
                        secondary={`Last used: ${new Date(profile.last_used * 1000).toLocaleDateString()}`}
                        primaryTypographyProps={{ sx: { color: '#fff' } }}
                        secondaryTypographyProps={{ sx: { color: '#666' } }}
                      />
                      <ListItemSecondaryAction>
                        <IconButton
                          edge="end"
                          onClick={() => handleDeleteProfile(profile.user_id)}
                          sx={{ color: '#f44336' }}
                        >
                          <Delete />
                        </IconButton>
                      </ListItemSecondaryAction>
                    </ListItem>
                  ))
                )}
              </List>
              <Button
                variant="outlined"
                startIcon={<Add />}
                onClick={() => setEnrollDialog(true)}
                sx={{
                  mt: 1,
                  borderColor: '#00e5ff',
                  color: '#00e5ff',
                  '&:hover': { borderColor: '#00b8d4' },
                }}
              >
                Enroll New Profile
              </Button>
            </Box>
          </>
        )}
      </SettingsSection>

      <SettingsSection title="Malware Protection">
        <ToggleSetting
          label="Malware Scanning"
          description="Automatically scan files for threats"
          value={settings.malware_scanning !== false}
          onChange={(v) => updateSetting('malware_scanning', v)}
        />

        <ToggleSetting
          label="Scan on Download"
          description="Check downloaded files automatically"
          value={settings.scan_on_download !== false}
          onChange={(v) => updateSetting('scan_on_download', v)}
        />

        <ToggleSetting
          label="Scan Before Execution"
          description="Scan executables before running"
          value={settings.scan_on_execute !== false}
          onChange={(v) => updateSetting('scan_on_execute', v)}
        />

        <ToggleSetting
          label="Quarantine Threats"
          description="Move detected threats to quarantine"
          value={settings.quarantine_threats !== false}
          onChange={(v) => updateSetting('quarantine_threats', v)}
        />

        <ToggleSetting
          label="Windows Defender Integration"
          description="Use Windows Defender engine for scanning"
          value={settings.defender_integration !== false}
          onChange={(v) => updateSetting('defender_integration', v)}
        />

        {quarantineFiles.length > 0 && (
          <Box sx={{ mt: 2 }}>
            <Typography variant="subtitle2" sx={{ color: '#ffa500', mb: 1 }}>
              Quarantined Files ({quarantineFiles.length})
            </Typography>
            <List sx={{ background: 'rgba(0,0,0,0.3)', borderRadius: 1 }}>
              {quarantineFiles.slice(0, 5).map((file) => (
                <ListItem key={file.quarantine_file}>
                  <ListItemText
                    primary={file.original_path}
                    secondary={`Quarantined: ${new Date(file.quarantine_time * 1000).toLocaleDateString()}`}
                    primaryTypographyProps={{ sx: { color: '#fff', fontSize: '0.85rem' } }}
                    secondaryTypographyProps={{ sx: { color: '#666' } }}
                  />
                  <ListItemSecondaryAction>
                    <Button
                      size="small"
                      onClick={() => handleRestoreQuarantine(file.quarantine_file)}
                      sx={{ color: '#00e5ff' }}
                    >
                      Restore
                    </Button>
                  </ListItemSecondaryAction>
                </ListItem>
              ))}
            </List>
            <Button
              size="small"
              startIcon={<Delete />}
              onClick={handleClearQuarantine}
              sx={{ mt: 1, color: '#f44336' }}
            >
              Clear All Quarantine
            </Button>
          </Box>
        )}
      </SettingsSection>

      <SettingsSection title="Access Control">
        <ToggleSetting
          label="Command Whitelist"
          description="Only allow pre-approved commands"
          value={settings.command_whitelist !== false}
          onChange={(v) => updateSetting('command_whitelist', v)}
        />

        <ToggleSetting
          label="Require Approval"
          description="Ask before executing dangerous actions"
          value={settings.require_approval !== false}
          onChange={(v) => updateSetting('require_approval', v)}
        />
      </SettingsSection>

      <SettingsSection title="Encryption & Audit">
        <ToggleSetting
          label="Vault Encryption"
          description="AES-256-GCM encryption for stored secrets"
          value={settings.vault_encryption !== false}
          onChange={(v) => updateSetting('vault_encryption', v)}
        />

        <ToggleSetting
          label="Activity Logging"
          description="Log all system actions"
          value={settings.activity_logging !== false}
          onChange={(v) => updateSetting('activity_logging', v)}
        />

        <ToggleSetting
          label="Tamper-Proof Logs"
          description="Blockchain-style audit trail"
          value={settings.tamper_proof_logs !== false}
          onChange={(v) => updateSetting('tamper_proof_logs', v)}
        />

        <SliderSetting
          label="Log Retention"
          description="Days to keep logs"
          value={settings.log_retention_days || 7}
          onChange={(v) => updateSetting('log_retention_days', v)}
          min={1}
          max={365}
          unit=" days"
        />
      </SettingsSection>

      <SettingsActions
        hasChanges={hasChanges}
        saving={saving}
        onSave={saveSettings}
        onReset={resetSettings}
        onRevert={revertChanges}
      />

      <Dialog open={enrollDialog} onClose={() => setEnrollDialog(false)}>
        <DialogTitle sx={{ color: '#00e5ff' }}>Enroll Voice Profile</DialogTitle>
        <DialogContent>
          <Typography sx={{ color: '#888' }}>
            Speak clearly for 5 seconds to create your voice profile.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEnrollDialog(false)}>Cancel</Button>
          <Button sx={{ color: '#00e5ff' }}>Start Recording</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
