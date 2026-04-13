import React, { useState, useEffect } from 'react';
import {
  Container,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  TextField,
  Box,
  Alert,
  Chip,
  List,
  ListItem,
  ListItemText,
  Divider,
  IconButton,
  Paper,
} from '@mui/material';
import {
  PlayArrow,
  Pause,
  Security,
  VpnKey,
  Terminal,
  Warning,
  CheckCircle,
  Error,
} from '@mui/icons-material';
import { raverApi } from '../services/api';
import { WebSocketService } from '../services/websocket';
import { SystemStatus, Intent, Secret } from '../types';

const Dashboard: React.FC = () => {
  const [systemStatus, setSystemStatus] = useState<SystemStatus>({
    paused: false,
    active_intents: 0,
    connected_clients: 0,
  });
  const [intents, setIntents] = useState<Intent[]>([]);
  const [secrets, setSecrets] = useState<Secret[]>([]);
  const [command, setCommand] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Mock user ID - in real app this would come from auth
  const userId = '550e8400-e29b-41d4-a716-446655440000';
  const userRoles = ['user'];

  const wsService = new WebSocketService();

  useEffect(() => {
    // Load initial data
    loadSystemStatus();
    loadSecrets();

    // Setup WebSocket
    wsService.connect(userId, (message) => {
      switch (message.type) {
        case 'system_paused':
          setSystemStatus(prev => ({ ...prev, paused: true }));
          setSuccess('System paused by user request');
          break;
        case 'system_resumed':
          setSystemStatus(prev => ({ ...prev, paused: false }));
          setSuccess('System resumed');
          break;
        case 'status_update':
          if (message.data) {
            setSystemStatus(message.data);
          }
          break;
        case 'intent_processed':
          if (message.data) {
            const newIntent: Intent = {
              intent_id: message.data.intent_id,
              user_id: userId,
              command: command,
              status: message.data.approved ? 'approved' : 'rejected',
              risk_level: message.data.risk_level,
              risk_score: 0, // Would be included in real implementation
              requires_approval: message.data.requires_approval,
              reason: message.data.reason,
              timestamp: new Date().toISOString(),
            };
            setIntents(prev => [newIntent, ...prev.slice(0, 9)]);
          }
          break;
      }
    });

    return () => {
      wsService.disconnect();
    };
  }, []);

  const loadSystemStatus = async () => {
    try {
      const status = await raverApi.getSystemStatus();
      setSystemStatus(status);
    } catch (err) {
      setError('Failed to load system status');
    }
  };

  const loadSecrets = async () => {
    try {
      const data = await raverApi.listSecrets(userId, userRoles);
      setSecrets(data.secrets);
    } catch (err) {
      setError('Failed to load secrets');
    }
  };

  const handleCommandSubmit = async () => {
    if (!command.trim()) return;

    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const result = await raverApi.processIntent(userId, command);
      setSuccess(`Command processed: ${result.approved ? 'Approved' : 'Rejected'}`);
      setCommand('');
      loadSystemStatus();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to process command');
    } finally {
      setLoading(false);
    }
  };

  const handlePauseSystem = async () => {
    try {
      await raverApi.pauseSystem(userId);
      setSuccess('System pause requested');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to pause system');
    }
  };

  const handleResumeSystem = async () => {
    try {
      await raverApi.resumeSystem(userId);
      setSuccess('System resume requested');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to resume system');
    }
  };

  const getRiskLevelColor = (level: string) => {
    switch (level) {
      case 'low': return 'success';
      case 'medium': return 'warning';
      case 'high': return 'error';
      case 'critical': return 'error';
      default: return 'default';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'approved': return <CheckCircle color="success" />;
      case 'rejected': return <Error color="error" />;
      case 'pending': return <Warning color="warning" />;
      default: return <Terminal />;
    }
  };

  return (
    <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
      {/* System Status Bar */}
      <Paper sx={{ p: 2, mb: 3, bgcolor: systemStatus.paused ? 'warning.light' : 'background.paper' }}>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="h6" component="div">
            RAVER System Status
          </Typography>
          <Box display="flex" alignItems="center" gap={2}>
            <Chip 
              icon={systemStatus.paused ? <Pause /> : <PlayArrow />}
              label={systemStatus.paused ? 'PAUSED' : 'RUNNING'}
              color={systemStatus.paused ? 'warning' : 'success'}
            />
            <Typography variant="body2">
              Active Intents: {systemStatus.active_intents} | 
              Connected: {systemStatus.connected_clients}
            </Typography>
            {systemStatus.paused ? (
              <Button
                variant="contained"
                startIcon={<PlayArrow />}
                onClick={handleResumeSystem}
                size="small"
              >
                Resume
              </Button>
            ) : (
              <Button
                variant="outlined"
                startIcon={<Pause />}
                onClick={handlePauseSystem}
                size="small"
              >
                Pause
              </Button>
            )}
          </Box>
        </Box>
      </Paper>

      {/* Alerts */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
      {success && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* Command Input */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <Terminal sx={{ mr: 1, verticalAlign: 'middle' }} />
                Command Interface
              </Typography>
              <Box display="flex" gap={1}>
                <TextField
                  fullWidth
                  variant="outlined"
                  placeholder="Enter command (e.g., 'pause', 'list processes', 'get secret from vault')"
                  value={command}
                  onChange={(e) => setCommand(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleCommandSubmit()}
                  disabled={loading || systemStatus.paused}
                />
                <Button
                  variant="contained"
                  onClick={handleCommandSubmit}
                  disabled={loading || systemStatus.paused || !command.trim()}
                >
                  Execute
                </Button>
              </Box>
              {systemStatus.paused && (
                <Alert severity="warning" sx={{ mt: 2 }}>
                  System is paused. Resume to execute commands.
                </Alert>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Recent Intents */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <Security sx={{ mr: 1, verticalAlign: 'middle' }} />
                Recent Intents
              </Typography>
              <List dense>
                {intents.length === 0 ? (
                  <ListItem>
                    <ListItemText primary="No intents processed yet" />
                  </ListItem>
                ) : (
                  intents.map((intent, index) => (
                    <React.Fragment key={intent.intent_id}>
                      <ListItem>
                        <Box display="flex" alignItems="center" width="100%">
                          {getStatusIcon(intent.status)}
                          <Box flexGrow={1} ml={1}>
                            <Typography variant="body2" noWrap>
                              {intent.command}
                            </Typography>
                            <Typography variant="caption" color="textSecondary">
                              {intent.reason}
                            </Typography>
                          </Box>
                          <Chip
                            label={intent.risk_level}
                            size="small"
                            color={getRiskLevelColor(intent.risk_level) as any}
                          />
                        </Box>
                      </ListItem>
                      {index < intents.length - 1 && <Divider />}
                    </React.Fragment>
                  ))
                )}
              </List>
            </CardContent>
          </Card>
        </Grid>

        {/* Vault Secrets */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <VpnKey sx={{ mr: 1, verticalAlign: 'middle' }} />
                Vault Secrets
              </Typography>
              <Grid container spacing={2}>
                {secrets.length === 0 ? (
                  <Grid item xs={12}>
                    <Typography color="textSecondary">
                      No secrets stored yet
                    </Typography>
                  </Grid>
                ) : (
                  secrets.map((secret) => (
                    <Grid item xs={12} sm={6} md={4} lg={3} key={secret.secret_id}>
                      <Paper variant="outlined" sx={{ p: 2 }}>
                        <Typography variant="subtitle2" noWrap>
                          {secret.service}
                        </Typography>
                        <Typography variant="body2" color="textSecondary" noWrap>
                          {secret.label}
                        </Typography>
                        <Typography variant="caption" color="textSecondary">
                          Created: {new Date(secret.created_at).toLocaleDateString()}
                        </Typography>
                      </Paper>
                    </Grid>
                  ))
                )}
              </Grid>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Container>
  );
};

export default Dashboard;
