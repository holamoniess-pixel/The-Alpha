import React, { useState } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  TextField,
  Button,
  Switch,
  FormControlLabel,
  Divider,
  Alert
} from '@mui/material';
import { useAuth } from '../contexts/AuthContext';

const SettingsPage: React.FC = () => {
  const { user } = useAuth();
  const [settings, setSettings] = useState({
    notifications: true,
    autoApprove: false,
    sessionTimeout: 30,
    logLevel: 'INFO'
  });
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const handleSave = async () => {
    try {
      // Mock save operation
      await new Promise(resolve => setTimeout(resolve, 1000));
      setMessage({
        type: 'success',
        text: 'Settings saved successfully'
      });
      setTimeout(() => setMessage(null), 3000);
    } catch (error) {
      setMessage({
        type: 'error',
        text: 'Failed to save settings'
      });
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Settings
      </Typography>

      {message && (
        <Alert severity={message.type} sx={{ mb: 2 }}>
          {message.text}
        </Alert>
      )}

      <Card sx={{ backgroundColor: '#1a1a1a', border: '1px solid #333', mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            User Settings
          </Typography>
          
          <TextField
            fullWidth
            label="Current User"
            value={user || ''}
            disabled
            sx={{ mb: 2 }}
          />
          
          <FormControlLabel
            control={
              <Switch
                checked={settings.notifications}
                onChange={(e) => setSettings({ ...settings, notifications: e.target.checked })}
              />
            }
            label="Enable Notifications"
            sx={{ mb: 2 }}
          />
          
          <FormControlLabel
            control={
              <Switch
                checked={settings.autoApprove}
                onChange={(e) => setSettings({ ...settings, autoApprove: e.target.checked })}
              />
            }
            label="Auto-approve Low Risk Actions"
            sx={{ mb: 2 }}
          />
        </CardContent>
      </Card>

      <Card sx={{ backgroundColor: '#1a1a1a', border: '1px solid #333', mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Security Settings
          </Typography>
          
          <TextField
            fullWidth
            label="Session Timeout (minutes)"
            type="number"
            value={settings.sessionTimeout}
            onChange={(e) => setSettings({ ...settings, sessionTimeout: parseInt(e.target.value) || 30 })}
            sx={{ mb: 2 }}
          />
          
          <TextField
            fullWidth
            label="Log Level"
            select
            value={settings.logLevel}
            onChange={(e) => setSettings({ ...settings, logLevel: e.target.value })}
            sx={{ mb: 2 }}
            SelectProps={{
              native: true
            }}
          >
            <option value="DEBUG">DEBUG</option>
            <option value="INFO">INFO</option>
            <option value="WARNING">WARNING</option>
            <option value="ERROR">ERROR</option>
            <option value="CRITICAL">CRITICAL</option>
          </TextField>
        </CardContent>
      </Card>

      <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
        <Button variant="contained" onClick={handleSave}>
          Save Settings
        </Button>
      </Box>
    </Box>
  );
};

export default SettingsPage;
