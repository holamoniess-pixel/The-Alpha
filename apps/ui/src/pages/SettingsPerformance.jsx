/**
 * ALPHA OMEGA - Performance Settings Page
 * Category: ⚡ PERFORMANCE (~45 settings)
 */

import React from 'react';
import { Box, Typography, Alert, Grid, LinearProgress, Chip } from '@mui/material';
import {
  Speed,
  Memory,
  BatteryChargingFull,
  SettingsSuggest,
} from '@mui/icons-material';
import {
  SettingsHeader,
  SettingsSection,
  ToggleSetting,
  SliderSetting,
  DropdownSetting,
  SettingsActions,
  useSettings,
} from '../components/SettingsComponents';

export default function SettingsPerformance() {
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
  } = useSettings('performance');

  const [systemInfo, setSystemInfo] = React.useState(null);

  React.useEffect(() => {
    fetchSystemInfo();
  }, []);

  const fetchSystemInfo = async () => {
    try {
      const res = await fetch('http://localhost:8000/status');
      const data = await res.json();
      setSystemInfo(data);
    } catch (err) {
      console.error('Failed to fetch system info:', err);
    }
  };

  if (loading) {
    return <Typography sx={{ color: '#888', p: 3 }}>Loading performance settings...</Typography>;
  }

  return (
    <Box sx={{ p: 3, pb: 10 }}>
      <SettingsHeader
        title="Performance Settings"
        description="Configure resource limits, power management, and caching"
        icon={<Speed sx={{ color: '#00e5ff', fontSize: 32 }} />}
      />

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {systemInfo && (
        <SettingsSection title="Current System Status">
          <Grid container spacing={2}>
            <Grid item xs={6}>
              <Box sx={{ mb: 2 }}>
                <Typography variant="caption" sx={{ color: '#888' }}>CPU Usage</Typography>
                <LinearProgress
                  variant="determinate"
                  value={systemInfo.cpu_percent || 0}
                  sx={{
                    mt: 0.5,
                    height: 8,
                    borderRadius: 4,
                    backgroundColor: '#333',
                    '& .MuiLinearProgress-bar': { backgroundColor: '#00e5ff' },
                  }}
                />
                <Typography variant="caption" sx={{ color: '#00e5ff' }}>
                  {systemInfo.cpu_percent || 0}%
                </Typography>
              </Box>
            </Grid>
            <Grid item xs={6}>
              <Box sx={{ mb: 2 }}>
                <Typography variant="caption" sx={{ color: '#888' }}>Memory Usage</Typography>
                <LinearProgress
                  variant="determinate"
                  value={systemInfo.memory_percent || 0}
                  sx={{
                    mt: 0.5,
                    height: 8,
                    borderRadius: 4,
                    backgroundColor: '#333',
                    '& .MuiLinearProgress-bar': { backgroundColor: '#00e5ff' },
                  }}
                />
                <Typography variant="caption" sx={{ color: '#00e5ff' }}>
                  {systemInfo.memory_percent || 0}%
                </Typography>
              </Box>
            </Grid>
          </Grid>
        </SettingsSection>
      )}

      <SettingsSection title="Resource Limits">
        <SliderSetting
          label="CPU Limit"
          description="Maximum CPU usage"
          value={settings.cpu_limit || 80}
          onChange={(v) => updateSetting('cpu_limit', v)}
          min={10}
          max={100}
          unit="%"
        />

        <SliderSetting
          label="Memory Limit"
          description="Maximum RAM allocation"
          value={settings.memory_limit || 2048}
          onChange={(v) => updateSetting('memory_limit', v)}
          min={512}
          max={8192}
          step={256}
          unit=" MB"
        />

        <ToggleSetting
          label="GPU Acceleration"
          description="Use GPU for AI processing"
          value={settings.gpu_acceleration || false}
          onChange={(v) => updateSetting('gpu_acceleration', v)}
        />

        <ToggleSetting
          label="Background Tasks"
          description="Run when minimized"
          value={settings.background_tasks !== false}
          onChange={(v) => updateSetting('background_tasks', v)}
        />
      </SettingsSection>

      <SettingsSection title="Sleep Mode">
        <ToggleSetting
          label="Work in Sleep"
          description="Continue tasks while PC is sleeping"
          value={settings.work_in_sleep || false}
          onChange={(v) => updateSetting('work_in_sleep', v)}
          warning="Requires system permissions"
        />

        <ToggleSetting
          label="Wake for Tasks"
          description="Wake PC for scheduled tasks"
          value={settings.wake_for_tasks || false}
          onChange={(v) => updateSetting('wake_for_tasks', v)}
        />

        <ToggleSetting
          label="Network in Sleep"
          description="Keep network active"
          value={settings.network_in_sleep || false}
          onChange={(v) => updateSetting('network_in_sleep', v)}
        />

        <DropdownSetting
          label="Power Priority"
          description="Task priority when on battery"
          value={settings.power_priority || 'normal'}
          onChange={(v) => updateSetting('power_priority', v)}
          options={['low', 'normal', 'high']}
        />
      </SettingsSection>

      <SettingsSection title="Caching">
        <ToggleSetting
          label="Enable Caching"
          description="Cache AI responses"
          value={settings.enable_caching !== false}
          onChange={(v) => updateSetting('enable_caching', v)}
        />

        <SliderSetting
          label="Cache Size"
          description="Memory for cache"
          value={settings.cache_size || 512}
          onChange={(v) => updateSetting('cache_size', v)}
          min={100}
          max={2000}
          unit=" MB"
        />
      </SettingsSection>

      <SettingsSection title="Optimization">
        <ToggleSetting
          label="Auto Optimize"
          description="Automatically tune settings"
          value={settings.auto_optimize !== false}
          onChange={(v) => updateSetting('auto_optimize', v)}
        />

        <ToggleSetting
          label="Low Power Mode"
          description="Reduce resource usage"
          value={settings.low_power_mode || false}
          onChange={(v) => updateSetting('low_power_mode', v)}
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
