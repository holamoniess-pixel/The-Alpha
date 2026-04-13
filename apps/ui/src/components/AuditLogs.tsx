import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  List,
  ListItem,
  ListItemText,
  Chip,
  TextField,
  Button
} from '@mui/material';

interface AuditEvent {
  event_id: string;
  event_type: string;
  timestamp: string;
  description: string;
  user_id: string;
  severity: string;
}

const AuditLogs: React.FC = () => {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [filter, setFilter] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadAuditLogs();
  }, []);

  const loadAuditLogs = async () => {
    setLoading(true);
    try {
      // Mock data for now
      const mockEvents: AuditEvent[] = [
        {
          event_id: '1',
          event_type: 'intent_received',
          timestamp: new Date().toISOString(),
          description: 'User requested system automation',
          user_id: 'admin',
          severity: 'INFO'
        },
        {
          event_id: '2',
          event_type: 'action_executed',
          timestamp: new Date(Date.now() - 60000).toISOString(),
          description: 'Automation script executed successfully',
          user_id: 'user1',
          severity: 'INFO'
        },
        {
          event_id: '3',
          event_type: 'system_paused',
          timestamp: new Date(Date.now() - 120000).toISOString(),
          description: 'System paused by administrator',
          user_id: 'admin',
          severity: 'WARNING'
        }
      ];
      setEvents(mockEvents);
    } catch (error) {
      console.error('Failed to load audit logs:', error);
    } finally {
      setLoading(false);
    }
  };

  const filteredEvents = events.filter(event =>
    event.description.toLowerCase().includes(filter.toLowerCase()) ||
    event.user_id.toLowerCase().includes(filter.toLowerCase()) ||
    event.event_type.toLowerCase().includes(filter.toLowerCase())
  );

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'CRITICAL': return '#f44336';
      case 'ERROR': return '#ff9800';
      case 'WARNING': return '#ff9800';
      case 'INFO': return '#4caf50';
      default: return '#9e9e9e';
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Audit Logs
      </Typography>

      <Box sx={{ mb: 3, display: 'flex', gap: 2, alignItems: 'center' }}>
        <TextField
          label="Filter events"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          sx={{ minWidth: 300 }}
        />
        <Button variant="outlined" onClick={loadAuditLogs}>
          Refresh
        </Button>
      </Box>

      <Card sx={{ backgroundColor: '#1a1a1a', border: '1px solid #333' }}>
        <CardContent>
          <List>
            {filteredEvents.map((event) => (
              <ListItem key={event.event_id} sx={{ 
                backgroundColor: '#0a0a0a', 
                mb: 1, 
                borderRadius: 1,
                borderLeft: `4px solid ${getSeverityColor(event.severity)}`
              }}>
                <ListItemText
                  primary={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography variant="body1">
                        {event.description}
                      </Typography>
                      <Chip
                        label={event.severity}
                        size="small"
                        sx={{
                          backgroundColor: getSeverityColor(event.severity),
                          color: 'white'
                        }}
                      />
                    </Box>
                  }
                  secondary={
                    <Box sx={{ mt: 1 }}>
                      <Typography variant="body2" color="text.secondary">
                        Type: {event.event_type} | User: {event.user_id}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {new Date(event.timestamp).toLocaleString()}
                      </Typography>
                    </Box>
                  }
                />
              </ListItem>
            ))}
          </List>
          
          {filteredEvents.length === 0 && (
            <Typography color="text.secondary" sx={{ textAlign: 'center', py: 3 }}>
              No events found matching the filter criteria.
            </Typography>
          )}
        </CardContent>
      </Card>
    </Box>
  );
};

export default AuditLogs;
