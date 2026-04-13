import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Alert,
  CircularProgress
} from '@mui/material';
import { Lock, Unlock, Eye, Plus, Delete, Edit } from '@mui/icons-material';

interface Secret {
  secret_id: string;
  service: string;
  label: string;
  created_at: string;
  updated_at: string;
}

interface VaultStatus {
  initialized: boolean;
  unlocked: boolean;
  current_user: string;
}

const VaultPage: React.FC = () => {
  const [vaultStatus, setVaultStatus] = useState<VaultStatus | null>(null);
  const [secrets, setSecrets] = useState<Secret[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [unlockDialogOpen, setUnlockDialogOpen] = useState(false);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [unlockPassword, setUnlockPassword] = useState('');
  const [mounted, setMounted] = useState(false);
  const [newSecret, setNewSecret] = useState({
    service: '',
    label: '',
    data: '',
    description: ''
  });

  useEffect(() => {
    setMounted(true);
    fetchVaultStatus();
  }, []);

  const fetchVaultStatus = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/vault/status', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        setVaultStatus(data);
        if (data.unlocked) {
          fetchSecrets();
        }
      }
    } catch (error) {
      console.error('Error fetching vault status:', error);
    }
  };

  const fetchSecrets = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/vault/secrets', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        setSecrets(data.secrets || []);
      }
    } catch (error) {
      setError('Failed to fetch secrets');
    } finally {
      setLoading(false);
    }
  };

  const handleUnlockVault = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/vault/unlock', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          user_id: 'demo-user',
          password: unlockPassword
        }),
      });
      
      if (response.ok) {
        setUnlockDialogOpen(false);
        setUnlockPassword('');
        fetchVaultStatus();
      } else {
        setError('Failed to unlock vault');
      }
    } catch (error) {
      setError('Network error');
    }
  };

  const handleCreateSecret = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/vault/secrets', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(newSecret),
      });
      
      if (response.ok) {
        setCreateDialogOpen(false);
        setNewSecret({ service: '', label: '', data: '', description: '' });
        fetchSecrets();
      } else {
        setError('Failed to create secret');
      }
    } catch (error) {
      setError('Network error');
    }
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
            background: 'linear-gradient(90deg, #ff00ff, #00f5ff)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            letterSpacing: 4
          }}
        >
          VAULT MANAGER
        </Typography>
        <Box sx={{
          flex: 1,
          height: 2,
          background: 'linear-gradient(90deg, rgba(255, 0, 255, 0.5), transparent)'
        }} />
      </Box>

      {vaultStatus && (
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
            <Box display="flex" alignItems="center" justifyContent="space-between">
              <Box display="flex" alignItems="center">
                <Box sx={{
                  width: 48,
                  height: 48,
                  borderRadius: 2,
                  bgcolor: vaultStatus.unlocked ? 'rgba(0, 255, 136, 0.1)' : 'rgba(255, 51, 102, 0.1)',
                  border: `1px solid ${vaultStatus.unlocked ? '#00ff88' : '#ff3366'}`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  mr: 2
                }}>
                  {vaultStatus.unlocked ? (
                    <Unlock sx={{ color: '#00ff88' }} />
                  ) : (
                    <Lock sx={{ color: '#ff3366' }} />
                  )}
                </Box>
                <Box>
                  <Typography 
                    sx={{ 
                      fontFamily: 'Rajdhani',
                      fontSize: '0.8rem',
                      color: 'rgba(255,255,255,0.5)',
                      letterSpacing: 2
                    }}
                  >
                    STATUS
                  </Typography>
                  <Typography 
                    variant="h6" 
                    sx={{ 
                      fontFamily: 'Orbitron',
                      color: vaultStatus.unlocked ? '#00ff88' : '#ff3366',
                      textShadow: `0 0 10px ${vaultStatus.unlocked ? '#00ff88' : '#ff3366'}`
                    }}
                  >
                    {vaultStatus.unlocked ? 'UNLOCKED' : 'LOCKED'}
                  </Typography>
                </Box>
              </Box>
              
              {!vaultStatus.unlocked && (
                <Button
                  variant="contained"
                  startIcon={<Unlock />}
                  onClick={() => setUnlockDialogOpen(true)}
                  sx={{
                    fontFamily: 'Rajdhani',
                    fontWeight: 600,
                    bgcolor: 'rgba(0, 255, 136, 0.2)',
                    border: '1px solid #00ff88',
                    color: '#00ff88',
                    '&:hover': {
                      bgcolor: 'rgba(0, 255, 136, 0.3)',
                      boxShadow: '0 0 20px rgba(0, 255, 136, 0.5)'
                    }
                  }}
                >
                  Unlock Vault
                </Button>
              )}
            </Box>
            
            {vaultStatus.current_user && (
              <Typography 
                variant="body2" 
                sx={{ 
                  mt: 2,
                  fontFamily: 'Rajdhani',
                  color: 'rgba(255,255,255,0.5)'
                }}
              >
                Current User: <span style={{ color: '#00f5ff' }}>{vaultStatus.current_user}</span>
              </Typography>
            )}
          </CardContent>
        </Card>
      )}

      {error && (
        <Alert 
          severity="error" 
          sx={{ 
            mb: 2,
            bgcolor: 'rgba(255, 51, 102, 0.1)',
            border: '1px solid rgba(255, 51, 102, 0.3)',
            animation: 'slideInUp 0.3s ease'
          }} 
          onClose={() => setError(null)}
        >
          <Typography sx={{ fontFamily: 'Rajdhani' }}>{error}</Typography>
        </Alert>
      )}

      {vaultStatus?.unlocked && (
        <Card 
          className="cyber-card"
          sx={{ 
            opacity: mounted ? 1 : 0,
            transform: mounted ? 'translateY(0)' : 'translateY(20px)',
            transition: 'all 0.5s ease 0.2s'
          }}
        >
          <CardContent>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
              <Typography 
                variant="h6"
                sx={{ 
                  fontFamily: 'Rajdhani',
                  fontWeight: 600,
                  color: '#ff00ff',
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
                  bgcolor: '#ff00ff',
                  boxShadow: '0 0 10px #ff00ff'
                }} />
                STORED SECRETS
              </Typography>
              <Button
                variant="contained"
                startIcon={<Plus />}
                onClick={() => setCreateDialogOpen(true)}
                sx={{
                  fontFamily: 'Rajdhani',
                  fontWeight: 600,
                  background: 'linear-gradient(90deg, #00f5ff, #ff00ff)',
                  '&:hover': {
                    boxShadow: '0 0 30px rgba(0, 245, 255, 0.5)'
                  }
                }}
              >
                Create Secret
              </Button>
            </Box>

            {loading ? (
              <Box display="flex" justifyContent="center" p={4}>
                <CircularProgress sx={{ color: '#00f5ff' }} />
              </Box>
            ) : (
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
                      <TableCell sx={{ fontFamily: 'Rajdhani', color: '#00f5ff', fontWeight: 600 }}>Service</TableCell>
                      <TableCell sx={{ fontFamily: 'Rajdhani', color: '#00f5ff', fontWeight: 600 }}>Label</TableCell>
                      <TableCell sx={{ fontFamily: 'Rajdhani', color: '#00f5ff', fontWeight: 600 }}>Created</TableCell>
                      <TableCell sx={{ fontFamily: 'Rajdhani', color: '#00f5ff', fontWeight: 600 }}>Updated</TableCell>
                      <TableCell sx={{ fontFamily: 'Rajdhani', color: '#00f5ff', fontWeight: 600 }}>Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {secrets.map((secret, index) => (
                      <TableRow 
                        key={secret.secret_id}
                        sx={{
                          animation: `slideInUp 0.3s ease ${0.3 + index * 0.05}s both`,
                          '&:hover': { bgcolor: 'rgba(0, 245, 255, 0.05)' }
                        }}
                      >
                        <TableCell sx={{ fontFamily: 'Rajdhani' }}>{secret.service}</TableCell>
                        <TableCell sx={{ fontFamily: 'Rajdhani' }}>{secret.label}</TableCell>
                        <TableCell sx={{ fontFamily: 'Rajdhani' }}>
                          {new Date(secret.created_at).toLocaleDateString()}
                        </TableCell>
                        <TableCell sx={{ fontFamily: 'Rajdhani' }}>
                          {new Date(secret.updated_at).toLocaleDateString()}
                        </TableCell>
                        <TableCell>
                          <IconButton size="small" sx={{ color: '#00f5ff' }}>
                            <Eye sx={{ fontSize: 18 }} />
                          </IconButton>
                          <IconButton size="small" sx={{ color: '#ffaa00' }}>
                            <Edit sx={{ fontSize: 18 }} />
                          </IconButton>
                          <IconButton size="small" sx={{ color: '#ff3366' }}>
                            <Delete sx={{ fontSize: 18 }} />
                          </IconButton>
                        </TableCell>
                      </TableRow>
                    ))}
                    {secrets.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={5} align="center">
                          <Typography 
                            variant="body2" 
                            sx={{ 
                              fontFamily: 'Rajdhani',
                              color: 'rgba(255,255,255,0.4)',
                              py: 4
                            }}
                          >
                            No secrets stored yet
                          </Typography>
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </CardContent>
        </Card>
      )}

      <Dialog 
        open={unlockDialogOpen} 
        onClose={() => setUnlockDialogOpen(false)}
        PaperProps={{
          sx: {
            bgcolor: '#12121a',
            border: '1px solid rgba(0, 245, 255, 0.3)',
            backgroundImage: 'none'
          }
        }}
      >
        <DialogTitle sx={{ fontFamily: 'Orbitron', color: '#00ff88' }}>
          <Lock sx={{ mr: 1, verticalAlign: 'middle' }} />
          UNLOCK VAULT
        </DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Vault Password"
            type="password"
            fullWidth
            variant="outlined"
            value={unlockPassword}
            onChange={(e) => setUnlockPassword(e.target.value)}
            className="cyber-input"
            sx={{
              mt: 1,
              '& .MuiInputLabel-root': { fontFamily: 'Rajdhani', color: 'rgba(0, 245, 255, 0.7)' },
              '& .MuiOutlinedInput-root': {
                fontFamily: 'Rajdhani',
                '& fieldset': { borderColor: 'rgba(0, 245, 255, 0.3)' },
                '&:hover fieldset': { borderColor: 'rgba(0, 245, 255, 0.5)' },
                '&.Mui-focused fieldset': { borderColor: '#00f5ff' }
              }
            }}
          />
        </DialogContent>
        <DialogActions>
          <Button 
            onClick={() => setUnlockDialogOpen(false)}
            sx={{ fontFamily: 'Rajdhani', color: 'rgba(255,255,255,0.5)' }}
          >
            Cancel
          </Button>
          <Button 
            onClick={handleUnlockVault} 
            variant="contained"
            sx={{ 
              fontFamily: 'Rajdhani',
              bgcolor: '#00ff88',
              '&:hover': { bgcolor: '#00cc6a' }
            }}
          >
            Unlock
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog 
        open={createDialogOpen} 
        onClose={() => setCreateDialogOpen(false)} 
        maxWidth="sm" 
        fullWidth
        PaperProps={{
          sx: {
            bgcolor: '#12121a',
            border: '1px solid rgba(255, 0, 255, 0.3)',
            backgroundImage: 'none'
          }
        }}
      >
        <DialogTitle sx={{ fontFamily: 'Orbitron', color: '#ff00ff' }}>
          CREATE NEW SECRET
        </DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Service"
            fullWidth
            variant="outlined"
            value={newSecret.service}
            onChange={(e) => setNewSecret({ ...newSecret, service: e.target.value })}
            sx={{ mb: 2, mt: 1 }}
            className="cyber-input"
          />
          <TextField
            margin="dense"
            label="Label"
            fullWidth
            variant="outlined"
            value={newSecret.label}
            onChange={(e) => setNewSecret({ ...newSecret, label: e.target.value })}
            sx={{ mb: 2 }}
            className="cyber-input"
          />
          <TextField
            margin="dense"
            label="Secret Data"
            fullWidth
            variant="outlined"
            type="password"
            value={newSecret.data}
            onChange={(e) => setNewSecret({ ...newSecret, data: e.target.value })}
            sx={{ mb: 2 }}
            className="cyber-input"
          />
          <TextField
            margin="dense"
            label="Description"
            fullWidth
            variant="outlined"
            multiline
            rows={3}
            value={newSecret.description}
            onChange={(e) => setNewSecret({ ...newSecret, description: e.target.value })}
            className="cyber-input"
          />
        </DialogContent>
        <DialogActions>
          <Button 
            onClick={() => setCreateDialogOpen(false)}
            sx={{ fontFamily: 'Rajdhani', color: 'rgba(255,255,255,0.5)' }}
          >
            Cancel
          </Button>
          <Button 
            onClick={handleCreateSecret} 
            variant="contained"
            sx={{ 
              fontFamily: 'Rajdhani',
              background: 'linear-gradient(90deg, #00f5ff, #ff00ff)',
            }}
          >
            Create
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default VaultPage;
