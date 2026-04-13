import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Button,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Alert
} from '@mui/material';
import { Check, Close } from '@mui/icons-material';

interface PendingIntent {
  intent_id: string;
  description: string;
  user_id: string;
  approval_method: string;
  created_at: string;
}

const Approvals: React.FC = () => {
  const [pendingIntents, setPendingIntents] = useState<PendingIntent[]>([]);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    loadPendingIntents();
  }, []);

  const loadPendingIntents = async () => {
    // Mock data for now
    setPendingIntents([
      {
        intent_id: '123',
        description: 'Execute automation script on system files',
        user_id: 'user1',
        approval_method: 'ui_confirm',
        created_at: new Date().toISOString()
      }
    ]);
  };

  const handleApproval = async (intentId: string, approved: boolean) => {
    try {
      // Mock API call
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      setPendingIntents(prev => prev.filter(intent => intent.intent_id !== intentId));
      setMessage({
        type: approved ? 'success' : 'error',
        text: approved ? 'Intent approved' : 'Intent denied'
      });
      
      setTimeout(() => setMessage(null), 3000);
    } catch (error) {
      setMessage({
        type: 'error',
        text: 'Failed to process approval'
      });
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Pending Approvals
      </Typography>

      {message && (
        <Alert severity={message.type} sx={{ mb: 2 }}>
          {message.text}
        </Alert>
      )}

      {pendingIntents.length === 0 ? (
        <Card sx={{ backgroundColor: '#1a1a1a', border: '1px solid #333' }}>
          <CardContent>
            <Typography color="text.secondary">
              No pending approvals at this time.
            </Typography>
          </CardContent>
        </Card>
      ) : (
        <List>
          {pendingIntents.map((intent) => (
            <ListItem key={intent.intent_id} sx={{ backgroundColor: '#1a1a1a', mb: 1, borderRadius: 1 }}>
              <ListItemText
                primary={intent.description}
                secondary={`Requested by: ${intent.user_id} | Approval: ${intent.approval_method}`}
              />
              <ListItemSecondaryAction>
                <Button
                  variant="contained"
                  color="success"
                  startIcon={<Check />}
                  onClick={() => handleApproval(intent.intent_id, true)}
                  sx={{ mr: 1 }}
                >
                  Approve
                </Button>
                <Button
                  variant="outlined"
                  color="error"
                  startIcon={<Close />}
                  onClick={() => handleApproval(intent.intent_id, false)}
                >
                  Deny
                </Button>
              </ListItemSecondaryAction>
            </ListItem>
          ))}
        </List>
      )}
    </Box>
  );
};

export default Approvals;
