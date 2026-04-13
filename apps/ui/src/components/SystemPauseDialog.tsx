import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Typography,
  Box,
  Alert,
  List,
  ListItem,
  ListItemText,
  ListItemIcon
} from '@mui/material';
import { Pause, AlertTriangle, Clock, Shield } from 'lucide-react';

interface SystemPauseDialogProps {
  open: boolean;
  onClose: () => void;
  onPause: (reason: string) => void;
}

const SystemPauseDialog: React.FC<SystemPauseDialogProps> = ({ open, onClose, onPause }) => {
  const [reason, setReason] = useState('');
  const [loading, setLoading] = useState(false);

  const handlePause = () => {
    setLoading(true);
    onPause(reason || 'Manual pause by user');
    setLoading(false);
    setReason('');
  };

  const effects = [
    {
      icon: <Pause size={16} />,
      primary: 'Stop All Operations',
      secondary: 'All active requests and automation will be paused'
    },
    {
      icon: <Clock size={16} />,
      primary: 'Queue New Requests',
      secondary: 'New requests will be queued until system is resumed'
    },
    {
      icon: <Shield size={16} />,
      primary: 'Maintain Security',
      secondary: 'Security monitoring and audit logging continue'
    }
  ];

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        <Box display="flex" alignItems="center" gap={1}>
          <Pause color="warning" />
          Pause System Operations
        </Box>
      </DialogTitle>
      
      <DialogContent>
        <Alert severity="warning" sx={{ mb: 3 }}>
          <AlertTriangle size={16} style={{ marginRight: 8 }} />
          Pausing the system will stop all automated operations and new requests.
        </Alert>

        <Typography variant="body2" gutterBottom>
          The following will occur when you pause the system:
        </Typography>

        <List dense>
          {effects.map((effect, index) => (
            <ListItem key={index}>
              <ListItemIcon>
                {effect.icon}
              </ListItemIcon>
              <ListItemText
                primary={effect.primary}
                secondary={effect.secondary}
              />
            </ListItem>
          ))}
        </List>

        <TextField
          fullWidth
          label="Reason for pause (optional)"
          variant="outlined"
          margin="normal"
          multiline
          rows={3}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Enter the reason for pausing the system..."
        />
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose} disabled={loading}>
          Cancel
        </Button>
        <Button
          onClick={handlePause}
          variant="contained"
          color="warning"
          disabled={loading}
          startIcon={<Pause />}
        >
          {loading ? 'Pausing...' : 'Pause System'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default SystemPauseDialog;
