import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  TextField,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert
} from '@mui/material';
import { Search, Eye, Download, Shield } from '@mui/icons-material';

interface AuditEvent {
  entry_id: string;
  timestamp: string;
  event_type: string;
  user_id: string;
  action_type?: string;
  target_resource?: string;
  details: any;
}

const AuditPage: React.FC = () => {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedEvent, setSelectedEvent] = useState<AuditEvent | null>(null);
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    fetchAuditLogs();
  }, []);

  const fetchAuditLogs = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/audit/logs?limit=100', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        setEvents(data.events || []);
      } else {
        setError('Failed to fetch audit logs');
      }
    } catch (error) {
      setError('Network error');
    } finally {
      setLoading(false);
    }
  };

  const getEventTypeColor = (eventType: string) => {
    switch (eventType) {
      case 'action_request':
        return '#00f5ff';
      case 'action_execution':
        return '#00ff88';
      case 'action_denied':
        return '#ff3366';
      case 'system_pause':
        return '#ffaa00';
      case 'system_resume':
        return '#ff00ff';
      default:
        return '#888';
    }
  };

  const filteredEvents = events.filter(event =>
    event.event_type.toLowerCase().includes(searchTerm.toLowerCase()) ||
    event.user_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (event.action_type && event.action_type.toLowerCase().includes(searchTerm.toLowerCase())) ||
    (event.target_resource && event.target_resource.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  const handleViewDetails = (event: AuditEvent) => {
    setSelectedEvent(event);
    setDetailDialogOpen(true);
  };

  const handleExportLogs = () => {
    const dataStr = JSON.stringify(events, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
    
    const exportFileDefaultName = `raver-audit-${new Date().toISOString().split('T')[0]}.json`;
    
    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
  };

  return (
    <Box sx={{ flexGrow: 1, ml: '260px', p: 3 }}>
      <Box sx={{ 
        display: 'flex', 
        alignItems: 'center', 
        gap: 2,
        mb: 4,
        opacity: mounted ? 1 : 0,
        transform: mounted ? 'translateY(0)' : 'translateY(-20px)',
        transition: 'all 0.5s ease'
      }}>
        <Typography 
          variant="h3" 
          sx={{ 
            fontFamily: 'Orbitron',
            fontWeight: 700,
            background: 'linear-gradient(90deg, #ffaa00, #ff00ff)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            letterSpacing: 4
          }}
        >
          AUDIT LOGS
        </Typography>
        <Box sx={{
          flex: 1,
          height: 2,
          background: 'linear-gradient(90deg, rgba(255, 170, 0, 0.5), transparent)'
        }} />
      </Box>

      <Card 
        className="cyber-card"
        sx={{ 
          mb: 3,
          opacity: mounted ? 1 : 0,
          transform: mounted ? 'translateY(0)' : 'translateY(20px)',
          transition: 'all 0.5s ease 0.1s'
        }}
      >
        <CardContent>
          <Box display="flex" gap={2} alignItems="center" flexWrap="wrap">
            <TextField
              placeholder="Search events..."
              variant="outlined"
              size="small"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="cyber-input"
              InputProps={{
                startAdornment: <Search size={20} style={{ marginRight: 8, color: '#00f5ff' }} />
              }}
              sx={{ 
                minWidth: 300,
                '& .MuiOutlinedInput-root': {
                  fontFamily: 'Rajdhani'
                }
              }}
            />
            
            <Button
              variant="outlined"
              startIcon={<Download />}
              onClick={handleExportLogs}
              sx={{
                fontFamily: 'Rajdhani',
                borderColor: 'rgba(0, 245, 255, 0.5)',
                color: '#00f5ff',
                '&:hover': {
                  borderColor: '#00f5ff',
                  bgcolor: 'rgba(0, 245, 255, 0.1)',
                  boxShadow: '0 0 15px rgba(0, 245, 255, 0.3)'
                }
              }}
            >
              Export Logs
            </Button>
            
            <Button
              variant="outlined"
              onClick={fetchAuditLogs}
              disabled={loading}
              sx={{
                fontFamily: 'Rajdhani',
                borderColor: 'rgba(255, 255, 255, 0.3)',
                color: 'rgba(255,255,255,0.7)',
                '&:hover': {
                  borderColor: 'rgba(255, 255, 255, 0.5)',
                  bgcolor: 'rgba(255, 255, 255, 0.05)'
                }
              }}
            >
              Refresh
            </Button>
          </Box>
        </CardContent>
      </Card>

      {error && (
        <Alert 
          severity="error" 
          sx={{ 
            mb: 2,
            bgcolor: 'rgba(255, 51, 102, 0.1)',
            border: '1px solid rgba(255, 51, 102, 0.3)'
          }} 
          onClose={() => setError(null)}
        >
          <Typography sx={{ fontFamily: 'Rajdhani' }}>{error}</Typography>
        </Alert>
      )}

      <Card 
        className="cyber-card"
        sx={{ 
          opacity: mounted ? 1 : 0,
          transform: mounted ? 'translateY(0)' : 'translateY(20px)',
          transition: 'all 0.5s ease 0.2s'
        }}
      >
        <CardContent>
          <Typography 
            variant="h6" 
            sx={{ 
              mb: 3,
              fontFamily: 'Rajdhani',
              fontWeight: 600,
              color: '#ffaa00',
              letterSpacing: 2,
              display: 'flex',
              alignItems: 'center',
              gap: 1
            }}
          >
            <Box sx={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              bgcolor: '#ffaa00',
              boxShadow: '0 0 10px #ffaa00'
            }} />
            RECENT EVENTS
          </Typography>
          
          <TableContainer 
            component={Paper} 
            variant="outlined"
            sx={{
              bgcolor: 'rgba(0, 0, 0, 0.3)',
              border: '1px solid rgba(0, 245, 255, 0.2)'
            }}
          >
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontFamily: 'Rajdhani', color: '#00f5ff', fontWeight: 600 }}>Timestamp</TableCell>
                  <TableCell sx={{ fontFamily: 'Rajdhani', color: '#00f5ff', fontWeight: 600 }}>Event Type</TableCell>
                  <TableCell sx={{ fontFamily: 'Rajdhani', color: '#00f5ff', fontWeight: 600 }}>User</TableCell>
                  <TableCell sx={{ fontFamily: 'Rajdhani', color: '#00f5ff', fontWeight: 600 }}>Action</TableCell>
                  <TableCell sx={{ fontFamily: 'Rajdhani', color: '#00f5ff', fontWeight: 600 }}>Target</TableCell>
                  <TableCell sx={{ fontFamily: 'Rajdhani', color: '#00f5ff', fontWeight: 600 }}>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filteredEvents.map((event, index) => (
                  <TableRow 
                    key={event.entry_id}
                    sx={{
                      animation: `slideInUp 0.3s ease ${0.3 + index * 0.03}s both`,
                      '&:hover': { bgcolor: 'rgba(0, 245, 255, 0.05)' }
                    }}
                  >
                    <TableCell sx={{ fontFamily: 'Rajdhani', fontSize: '0.85rem' }}>
                      {new Date(event.timestamp).toLocaleString()}
                    </TableCell>
                    <TableCell>
                      <Chip 
                        label={event.event_type.replace('_', ' ')}
                        size="small"
                        sx={{
                          fontFamily: 'Rajdhani',
                          fontWeight: 600,
                          bgcolor: `${getEventTypeColor(event.event_type)}20`,
                          color: getEventTypeColor(event.event_type),
                          border: `1px solid ${getEventTypeColor(event.event_type)}`,
                          textTransform: 'uppercase',
                          fontSize: '0.7rem'
                        }}
                      />
                    </TableCell>
                    <TableCell sx={{ fontFamily: 'Rajdhani', color: '#00f5ff' }}>{event.user_id}</TableCell>
                    <TableCell sx={{ fontFamily: 'Rajdhani' }}>
                      {event.action_type || '-'}
                    </TableCell>
                    <TableCell sx={{ fontFamily: 'Rajdhani' }}>
                      {event.target_resource || '-'}
                    </TableCell>
                    <TableCell>
                      <Button
                        size="small"
                        startIcon={<Eye sx={{ fontSize: 16 }} />}
                        onClick={() => handleViewDetails(event)}
                        sx={{
                          fontFamily: 'Rajdhani',
                          color: '#ff00ff',
                          '&:hover': {
                            bgcolor: 'rgba(255, 0, 255, 0.1)'
                          }
                        }}
                      >
                        Details
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
                {filteredEvents.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={6} align="center">
                      <Typography 
                        variant="body2" 
                        sx={{ 
                          fontFamily: 'Rajdhani',
                          color: 'rgba(255,255,255,0.4)',
                          py: 4
                        }}
                      >
                        No events found
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      <Dialog 
        open={detailDialogOpen} 
        onClose={() => setDetailDialogOpen(false)}
        maxWidth="md"
        fullWidth
        PaperProps={{
          sx: {
            bgcolor: '#12121a',
            border: '1px solid rgba(255, 170, 0, 0.3)',
            backgroundImage: 'none'
          }
        }}
      >
        <DialogTitle sx={{ fontFamily: 'Orbitron', color: '#ffaa00' }}>
          <Shield sx={{ mr: 1, verticalAlign: 'middle' }} />
          EVENT DETAILS
        </DialogTitle>
        <DialogContent>
          {selectedEvent && (
            <Box>
              <Typography 
                variant="body2" 
                sx={{ 
                  fontFamily: 'Rajdhani',
                  color: 'rgba(255,255,255,0.5)',
                  mb: 2
                }}
              >
                Event ID: <span style={{ color: '#00f5ff' }}>{selectedEvent.entry_id}</span>
              </Typography>
              
              <Box sx={{ mb: 2 }}>
                <Typography variant="body2" sx={{ fontFamily: 'Rajdhani', mb: 0.5 }}>
                  <strong style={{ color: 'rgba(255,255,255,0.7)' }}>Timestamp:</strong>
                </Typography>
                <Typography variant="body2" sx={{ fontFamily: 'Rajdhani', color: '#00f5ff' }}>
                  {new Date(selectedEvent.timestamp).toLocaleString()}
                </Typography>
              </Box>
              
              <Box sx={{ mb: 2 }}>
                <Typography variant="body2" sx={{ fontFamily: 'Rajdhani', mb: 0.5 }}>
                  <strong style={{ color: 'rgba(255,255,255,0.7)' }}>Event Type:</strong>
                </Typography>
                <Chip 
                  label={selectedEvent.event_type}
                  size="small"
                  sx={{
                    fontFamily: 'Rajdhani',
                    bgcolor: `${getEventTypeColor(selectedEvent.event_type)}20`,
                    color: getEventTypeColor(selectedEvent.event_type),
                    border: `1px solid ${getEventTypeColor(selectedEvent.event_type)}`
                  }}
                />
              </Box>
              
              <Box sx={{ mb: 2 }}>
                <Typography variant="body2" sx={{ fontFamily: 'Rajdhani', mb: 0.5 }}>
                  <strong style={{ color: 'rgba(255,255,255,0.7)' }}>User:</strong>
                </Typography>
                <Typography variant="body2" sx={{ fontFamily: 'Rajdhani', color: '#00f5ff' }}>
                  {selectedEvent.user_id}
                </Typography>
              </Box>
              
              {selectedEvent.action_type && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="body2" sx={{ fontFamily: 'Rajdhani', mb: 0.5 }}>
                    <strong style={{ color: 'rgba(255,255,255,0.7)' }}>Action:</strong>
                  </Typography>
                  <Typography variant="body2" sx={{ fontFamily: 'Rajdhani' }}>
                    {selectedEvent.action_type}
                  </Typography>
                </Box>
              )}
              
              {selectedEvent.target_resource && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="body2" sx={{ fontFamily: 'Rajdhani', mb: 0.5 }}>
                    <strong style={{ color: 'rgba(255,255,255,0.7)' }}>Target:</strong>
                  </Typography>
                  <Typography variant="body2" sx={{ fontFamily: 'Rajdhani' }}>
                    {selectedEvent.target_resource}
                  </Typography>
                </Box>
              )}
              
              <Box sx={{ mb: 2 }}>
                <Typography variant="body2" sx={{ fontFamily: 'Rajdhani', mb: 1 }}>
                  <strong style={{ color: 'rgba(255,255,255,0.7)' }}>Details:</strong>
                </Typography>
                
                <Box 
                  sx={{ 
                    p: 2, 
                    bgcolor: 'rgba(0, 0, 0, 0.5)', 
                    borderRadius: 1,
                    border: '1px solid rgba(0, 245, 255, 0.2)',
                    fontFamily: 'monospace',
                    fontSize: '0.85rem',
                    maxHeight: 300,
                    overflow: 'auto',
                    color: 'rgba(255,255,255,0.8)'
                  }}
                >
                  {JSON.stringify(selectedEvent.details, null, 2)}
                </Box>
              </Box>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button 
            onClick={() => setDetailDialogOpen(false)}
            sx={{ 
              fontFamily: 'Rajdhani', 
              color: 'rgba(255,255,255,0.5)'
            }}
          >
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default AuditPage;
