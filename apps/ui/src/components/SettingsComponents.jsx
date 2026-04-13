/**
 * ALPHA OMEGA - Settings Components
 * Reusable UI components for settings pages
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Switch,
  Slider,
  Select,
  MenuItem,
  TextField,
  Button,
  IconButton,
  InputAdornment,
  Chip,
  Alert,
  Tooltip,
  FormControl,
  InputLabel,
  Paper,
  Divider,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Snackbar,
} from '@mui/material';
import {
  Visibility,
  VisibilityOff,
  Refresh,
  Save,
  Info,
  Warning,
  RestartAlt,
} from '@mui/icons-material';

const API_BASE = 'http://localhost:8000';

export function useSettings(category) {
  const [settings, setSettings] = useState({});
  const [schema, setSchema] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [hasChanges, setHasChanges] = useState(false);
  const [originalSettings, setOriginalSettings] = useState({});

  useEffect(() => {
    fetchSettings();
    fetchSchema();
  }, [category]);

  const fetchSettings = async () => {
    try {
      const response = await fetch(`${API_BASE}/settings/${category}`);
      if (!response.ok) throw new Error('Failed to fetch settings');
      const data = await response.json();
      setSettings(data);
      setOriginalSettings(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchSchema = async () => {
    try {
      const response = await fetch(`${API_BASE}/settings/schema/${category}`);
      if (!response.ok) throw new Error('Failed to fetch schema');
      const data = await response.json();
      setSchema(data.settings || []);
    } catch (err) {
      console.error('Schema fetch error:', err);
    }
  };

  const updateSetting = (key, value) => {
    setSettings(prev => ({ ...prev, [key]: value }));
    setHasChanges(true);
  };

  const saveSettings = async () => {
    setSaving(true);
    try {
      const response = await fetch(`${API_BASE}/settings/${category}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ settings }),
      });
      if (!response.ok) throw new Error('Failed to save');
      setHasChanges(false);
      setOriginalSettings(settings);
      return true;
    } catch (err) {
      setError(err.message);
      return false;
    } finally {
      setSaving(false);
    }
  };

  const resetSettings = async () => {
    try {
      await fetch(`${API_BASE}/settings/reset/${category}`, { method: 'POST' });
      fetchSettings();
      setHasChanges(false);
    } catch (err) {
      setError(err.message);
    }
  };

  const revertChanges = () => {
    setSettings(originalSettings);
    setHasChanges(false);
  };

  return {
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
    refresh: fetchSettings,
  };
}

export function SettingsHeader({ title, description, icon }) {
  return (
    <Box sx={{ mb: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
        {icon}
        <Typography variant="h5" sx={{ color: '#00e5ff' }}>
          {title}
        </Typography>
      </Box>
      <Typography variant="body2" sx={{ color: '#888' }}>
        {description}
      </Typography>
    </Box>
  );
}

export function SettingsSection({ title, children, defaultExpanded = true }) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  return (
    <Paper
      sx={{
        mb: 2,
        background: 'rgba(0, 20, 40, 0.6)',
        border: '1px solid rgba(0, 229, 255, 0.2)',
        borderRadius: 2,
      }}
    >
      <Box
        sx={{
          p: 2,
          cursor: 'pointer',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          '&:hover': { background: 'rgba(0, 229, 255, 0.05)' },
        }}
        onClick={() => setExpanded(!expanded)}
      >
        <Typography variant="subtitle1" sx={{ color: '#00e5ff' }}>
          {title}
        </Typography>
        <Typography sx={{ color: '#666' }}>
          {expanded ? '−' : '+'}
        </Typography>
      </Box>
      {expanded && (
        <Box sx={{ p: 2, pt: 0 }}>
          <Divider sx={{ mb: 2, borderColor: 'rgba(0, 229, 255, 0.1)' }} />
          {children}
        </Box>
      )}
    </Paper>
  );
}

export function ToggleSetting({ label, description, value, onChange, disabled = false, warning = null }) {
  return (
    <Box sx={{ mb: 2 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Box>
          <Typography sx={{ color: '#fff' }}>{label}</Typography>
          {description && (
            <Typography variant="caption" sx={{ color: '#888' }}>
              {description}
            </Typography>
          )}
        </Box>
        <Switch
          checked={value}
          onChange={(e) => onChange(e.target.checked)}
          disabled={disabled}
          sx={{
            '& .MuiSwitch-switchBase.Mui-checked': {
              color: '#00e5ff',
            },
            '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': {
              backgroundColor: '#00e5ff',
            },
          }}
        />
      </Box>
      {warning && value && (
        <Alert severity="warning" sx={{ mt: 1, fontSize: '0.75rem' }}>
          {warning}
        </Alert>
      )}
    </Box>
  );
}

export function SliderSetting({
  label,
  description,
  value,
  onChange,
  min = 0,
  max = 100,
  step = 1,
  unit = '',
  marks = null,
}) {
  return (
    <Box sx={{ mb: 2 }}>
      <Typography sx={{ color: '#fff', mb: 1 }}>
        {label}: <span style={{ color: '#00e5ff' }}>{value}{unit}</span>
      </Typography>
      {description && (
        <Typography variant="caption" sx={{ color: '#888', display: 'block', mb: 1 }}>
          {description}
        </Typography>
      )}
      <Slider
        value={value}
        onChange={(e, v) => onChange(v)}
        min={min}
        max={max}
        step={step}
        marks={marks}
        sx={{
          color: '#00e5ff',
          '& .MuiSlider-thumb': { backgroundColor: '#00e5ff' },
          '& .MuiSlider-track': { backgroundColor: '#00e5ff' },
          '& .MuiSlider-rail': { backgroundColor: '#333' },
        }}
      />
    </Box>
  );
}

export function DropdownSetting({
  label,
  description,
  value,
  onChange,
  options = [],
  disabled = false,
}) {
  return (
    <Box sx={{ mb: 2 }}>
      <FormControl fullWidth disabled={disabled}>
        <InputLabel sx={{ color: '#888' }}>{label}</InputLabel>
        <Select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          sx={{
            color: '#fff',
            '& .MuiOutlinedInput-notchedOutline': { borderColor: '#333' },
            '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: '#00e5ff' },
            '&.Mui-focused .MuiOutlinedInput-notchedOutline': { borderColor: '#00e5ff' },
          }}
          MenuProps={{
            PaperProps: {
              sx: {
                background: '#0a1929',
                border: '1px solid #00e5ff',
              },
            },
          }}
        >
          {options.map((opt) => (
            <MenuItem key={opt} value={opt} sx={{ color: '#fff' }}>
              {opt}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
      {description && (
        <Typography variant="caption" sx={{ color: '#888', mt: 0.5, display: 'block' }}>
          {description}
        </Typography>
      )}
    </Box>
  );
}

export function TextSetting({
  label,
  description,
  value,
  onChange,
  placeholder = '',
  multiline = false,
  disabled = false,
}) {
  return (
    <Box sx={{ mb: 2 }}>
      <TextField
        fullWidth
        label={label}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        multiline={multiline}
        rows={multiline ? 3 : 1}
        disabled={disabled}
        sx={{
          '& .MuiInputLabel-root': { color: '#888' },
          '& .MuiOutlinedInput-root': {
            color: '#fff',
            '& fieldset': { borderColor: '#333' },
            '&:hover fieldset': { borderColor: '#00e5ff' },
            '&.Mui-focused fieldset': { borderColor: '#00e5ff' },
          },
        }}
      />
      {description && (
        <Typography variant="caption" sx={{ color: '#888', mt: 0.5, display: 'block' }}>
          {description}
        </Typography>
      )}
    </Box>
  );
}

export function PasswordSetting({
  label,
  description,
  value,
  onChange,
  placeholder = '',
  onClear = null,
}) {
  const [showPassword, setShowPassword] = useState(false);
  const hasValue = value && value.length > 0;

  return (
    <Box sx={{ mb: 2 }}>
      <TextField
        fullWidth
        type={showPassword ? 'text' : 'password'}
        label={label}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        InputProps={{
          endAdornment: (
            <InputAdornment position="end">
              {hasValue && onClear && (
                <IconButton onClick={onClear} size="small" sx={{ color: '#888' }}>
                  <RestartAlt fontSize="small" />
                </IconButton>
              )}
              <IconButton
                onClick={() => setShowPassword(!showPassword)}
                size="small"
                sx={{ color: '#00e5ff' }}
              >
                {showPassword ? <VisibilityOff /> : <Visibility />}
              </IconButton>
            </InputAdornment>
          ),
        }}
        sx={{
          '& .MuiInputLabel-root': { color: '#888' },
          '& .MuiOutlinedInput-root': {
            color: '#fff',
            '& fieldset': { borderColor: hasValue ? '#00e5ff' : '#333' },
            '&:hover fieldset': { borderColor: '#00e5ff' },
            '&.Mui-focused fieldset': { borderColor: '#00e5ff' },
          },
        }}
      />
      {description && (
        <Typography variant="caption" sx={{ color: '#888', mt: 0.5, display: 'block' }}>
          {description}
        </Typography>
      )}
      {hasValue && (
        <Chip
          label="Configured"
          size="small"
          sx={{ mt: 1, background: '#00e5ff20', color: '#00e5ff', border: '1px solid #00e5ff' }}
        />
      )}
    </Box>
  );
}

export function ColorSetting({ label, description, value, onChange }) {
  return (
    <Box sx={{ mb: 2 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
        <Typography sx={{ color: '#fff' }}>{label}</Typography>
        <input
          type="color"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          style={{
            width: 60,
            height: 36,
            border: '2px solid #333',
            borderRadius: 4,
            cursor: 'pointer',
            background: 'transparent',
          }}
        />
        <Typography sx={{ color: '#00e5ff', fontFamily: 'monospace' }}>{value}</Typography>
      </Box>
      {description && (
        <Typography variant="caption" sx={{ color: '#888', mt: 0.5, display: 'block' }}>
          {description}
        </Typography>
      )}
    </Box>
  );
}

export function SettingsActions({ hasChanges, saving, onSave, onReset, onRevert }) {
  return (
    <Box
      sx={{
        position: 'sticky',
        bottom: 0,
        p: 2,
        background: 'linear-gradient(transparent, #0a1929)',
        display: 'flex',
        gap: 2,
        justifyContent: 'flex-end',
      }}
    >
      <Button
        variant="outlined"
        onClick={onReset}
        startIcon={<Refresh />}
        sx={{
          borderColor: '#666',
          color: '#888',
          '&:hover': { borderColor: '#fff', color: '#fff' },
        }}
      >
        Reset to Defaults
      </Button>
      {hasChanges && (
        <Button
          variant="outlined"
          onClick={onRevert}
          sx={{
            borderColor: '#666',
            color: '#888',
            '&:hover': { borderColor: '#fff', color: '#fff' },
          }}
        >
          Discard Changes
        </Button>
      )}
      <Button
        variant="contained"
        onClick={onSave}
        disabled={saving || !hasChanges}
        startIcon={saving ? null : <Save />}
        sx={{
          background: '#00e5ff',
          color: '#000',
          '&:hover': { background: '#00b8d4' },
          '&:disabled': { background: '#333', color: '#666' },
        }}
      >
        {saving ? 'Saving...' : 'Save Changes'}
      </Button>
    </Box>
  );
}

export function SettingWithTooltip({ setting, children }) {
  const requiresRestart = setting.requires_restart;
  
  return (
    <Box sx={{ position: 'relative' }}>
      <Tooltip
        title={
          <Box>
            <Typography variant="body2">{setting.description}</Typography>
            {requiresRestart && (
              <Typography variant="caption" sx={{ color: '#ffa500', display: 'block', mt: 1 }}>
                ⚠️ Requires restart to take effect
              </Typography>
            )}
          </Box>
        }
        arrow
        placement="right"
      >
        <Box>
          {children}
          {requiresRestart && (
            <Chip
              label="Restart Required"
              size="small"
              icon={<Warning sx={{ fontSize: 14 }} />}
              sx={{
                mt: 0.5,
                height: 20,
                fontSize: '0.65rem',
                background: 'rgba(255, 165, 0, 0.1)',
                color: '#ffa500',
                border: '1px solid #ffa500',
              }}
            />
          )}
        </Box>
      </Tooltip>
    </Box>
  );
}
