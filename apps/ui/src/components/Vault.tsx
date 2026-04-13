import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  List,
  ListItem,
  ListItemText,
  IconButton
} from '@mui/material';
import { Add, Visibility, Edit, Delete } from '@mui/icons-material';
import axios from 'axios';

interface Secret {
  secret_id: string;
  service: string;
  label: string;
  description: string;
  tags: string[];
  created_at: string;
  updated_at: string;
}

const Vault: React.FC = () => {
  const [secrets, setSecrets] = useState<Secret[]>([]);
  const [open, setOpen] = useState(false);
  const [editingSecret, setEditingSecret] = useState<Secret | null>(null);
  const [formData, setFormData] = useState({
    service: '',
    label: '',
    data: '',
    description: '',
    tags: ''
  });

  useEffect(() => {
    loadSecrets();
  }, []);

  const loadSecrets = async () => {
    try {
      const response = await axios.get('/vault/secrets');
      setSecrets(response.data.secrets);
    } catch (error) {
      console.error('Failed to load secrets:', error);
    }
  };

  const handleSubmit = async () => {
    try {
      const secretData = {
        ...formData,
        tags: formData.tags.split(',').map(tag => tag.trim()).filter(tag => tag)
      };

      if (editingSecret) {
        await axios.put(`/vault/secrets/${editingSecret.secret_id}`, secretData);
      } else {
        await axios.post('/vault/secrets', secretData);
      }

      setOpen(false);
      setEditingSecret(null);
      setFormData({ service: '', label: '', data: '', description: '', tags: '' });
      loadSecrets();
    } catch (error) {
      console.error('Failed to save secret:', error);
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Secure Vault
      </Typography>

      <Button
        variant="contained"
        startIcon={<Add />}
        onClick={() => setOpen(true)}
        sx={{ mb: 3 }}
      >
        Add Secret
      </Button>

      <List>
        {secrets.map((secret) => (
          <ListItem key={secret.secret_id} sx={{ backgroundColor: '#1a1a1a', mb: 1, borderRadius: 1 }}>
            <ListItemText
              primary={`${secret.service} - ${secret.label}`}
              secondary={secret.description}
            />
            <IconButton>
              <Visibility />
            </IconButton>
            <IconButton>
              <Edit />
            </IconButton>
            <IconButton>
              <Delete />
            </IconButton>
          </ListItem>
        ))}
      </List>

      <Dialog open={open} onClose={() => setOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editingSecret ? 'Edit Secret' : 'Add Secret'}</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            label="Service"
            margin="normal"
            value={formData.service}
            onChange={(e) => setFormData({ ...formData, service: e.target.value })}
          />
          <TextField
            fullWidth
            label="Label"
            margin="normal"
            value={formData.label}
            onChange={(e) => setFormData({ ...formData, label: e.target.value })}
          />
          <TextField
            fullWidth
            label="Secret Data"
            margin="normal"
            type="password"
            value={formData.data}
            onChange={(e) => setFormData({ ...formData, data: e.target.value })}
          />
          <TextField
            fullWidth
            label="Description"
            margin="normal"
            multiline
            rows={3}
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
          />
          <TextField
            fullWidth
            label="Tags (comma separated)"
            margin="normal"
            value={formData.tags}
            onChange={(e) => setFormData({ ...formData, tags: e.target.value })}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Cancel</Button>
          <Button onClick={handleSubmit} variant="contained">
            {editingSecret ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Vault;
