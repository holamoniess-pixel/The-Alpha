/**
 * ALPHA OMEGA - Learning Settings Page
 * Category: 📚 LEARNING (~50 settings)
 */

import React from 'react';
import { Box, Typography, Alert, Grid, Button, Dialog, DialogTitle, DialogContent, DialogActions, List, ListItem, ListItemText, ListItemSecondaryAction, IconButton } from '@mui/material';
import {
  School,
  PlayCircle,
  Download,
  Delete,
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

export default function SettingsLearning() {
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
  } = useSettings('learning');

  const [skillsDialog, setSkillsDialog] = React.useState(false);
  const [skills, setSkills] = React.useState([]);

  React.useEffect(() => {
    fetchSkills();
  }, []);

  const fetchSkills = async () => {
    try {
      const res = await fetch('http://localhost:8000/learning/skills');
      const data = await res.json();
      setSkills(data.skills || []);
    } catch (err) {
      console.error('Failed to fetch skills:', err);
    }
  };

  const handleDeleteSkill = async (skillId) => {
    if (!confirm('Delete this learned skill?')) return;
    try {
      await fetch(`http://localhost:8000/learning/skills/${skillId}`, { method: 'DELETE' });
      fetchSkills();
    } catch (err) {
      alert('Failed to delete skill');
    }
  };

  if (loading) {
    return <Typography sx={{ color: '#888', p: 3 }}>Loading learning settings...</Typography>;
  }

  return (
    <Box sx={{ p: 3, pb: 10 }}>
      <SettingsHeader
        title="Learning Settings"
        description="Configure pattern recognition, watch & learn, and skill management"
        icon={<School sx={{ color: '#00e5ff', fontSize: 32 }} />}
      />

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <SettingsSection title="Pattern Recognition">
        <ToggleSetting
          label="Enable Learning"
          description="Learn from your actions and preferences"
          value={settings.enable_learning !== false}
          onChange={(v) => updateSetting('enable_learning', v)}
        />

        <ToggleSetting
          label="Learn Commands"
          description="Remember command patterns"
          value={settings.learn_commands !== false}
          onChange={(v) => updateSetting('learn_commands', v)}
        />

        <ToggleSetting
          label="Learn Workflows"
          description="Create workflows from habits"
          value={settings.learn_workflows !== false}
          onChange={(v) => updateSetting('learn_workflows', v)}
        />

        <ToggleSetting
          label="Prediction"
          description="Predict your next action"
          value={settings.prediction_enabled !== false}
          onChange={(v) => updateSetting('prediction_enabled', v)}
        />
      </SettingsSection>

      <SettingsSection title="Watch & Learn">
        <ToggleSetting
          label="Watch Mode"
          description="Observe your screen actions"
          value={settings.watch_mode || false}
          onChange={(v) => updateSetting('watch_mode', v)}
          warning="Screen content will be recorded for learning"
        />

        <ToggleSetting
          label="Learn from Tutorials"
          description="Process video tutorials"
          value={settings.learn_from_tutorials || false}
          onChange={(v) => updateSetting('learn_from_tutorials', v)}
        />

        <ToggleSetting
          label="Screen Recording"
          description="Record screen for learning"
          value={settings.screen_recording || false}
          onChange={(v) => updateSetting('screen_recording', v)}
        />

        <ToggleSetting
          label="Auto-Recreate"
          description="Create scripts from observed actions"
          value={settings.auto_recreate || false}
          onChange={(v) => updateSetting('auto_recreate', v)}
        />

        <DropdownSetting
          label="Tutorial Source"
          description="Where to learn from"
          value={settings.tutorial_source || 'youtube'}
          onChange={(v) => updateSetting('tutorial_source', v)}
          options={['youtube', 'local', 'all']}
        />

        <SliderSetting
          label="Learning Depth"
          description="How detailed to learn"
          value={settings.learning_depth || 5}
          onChange={(v) => updateSetting('learning_depth', v)}
          min={1}
          max={10}
        />
      </SettingsSection>

      <SettingsSection title="Behavior Analysis">
        <ToggleSetting
          label="Time Patterns"
          description="Learn time-based habits"
          value={settings.time_patterns !== false}
          onChange={(v) => updateSetting('time_patterns', v)}
        />

        <ToggleSetting
          label="App Usage Tracking"
          description="Track app usage patterns"
          value={settings.app_usage_tracking !== false}
          onChange={(v) => updateSetting('app_usage_tracking', v)}
        />
      </SettingsSection>

      <SettingsSection title="Skill Library">
        <Button
          variant="outlined"
          onClick={() => setSkillsDialog(true)}
          sx={{ borderColor: '#00e5ff', color: '#00e5ff' }}
        >
          View Learned Skills ({skills.length})
        </Button>
      </SettingsSection>

      <SettingsActions
        hasChanges={hasChanges}
        saving={saving}
        onSave={saveSettings}
        onReset={resetSettings}
        onRevert={revertChanges}
      />

      <Dialog open={skillsDialog} onClose={() => setSkillsDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle sx={{ color: '#00e5ff' }}>Learned Skills Library</DialogTitle>
        <DialogContent>
          {skills.length === 0 ? (
            <Typography sx={{ color: '#666', py: 2 }}>
              No skills learned yet. Enable Watch & Learn to start.
            </Typography>
          ) : (
            <List>
              {skills.map((skill) => (
                <ListItem key={skill.id} sx={{ borderBottom: '1px solid #333' }}>
                  <ListItemText
                    primary={skill.name}
                    secondary={`Created: ${new Date(skill.created_at).toLocaleDateString()} | Used: ${skill.use_count} times`}
                    primaryTypographyProps={{ sx: { color: '#fff' } }}
                    secondaryTypographyProps={{ sx: { color: '#666' } }}
                  />
                  <ListItemSecondaryAction>
                    <Button size="small" sx={{ color: '#00e5ff', mr: 1 }}>Export</Button>
                    <IconButton onClick={() => handleDeleteSkill(skill.id)} sx={{ color: '#f44336' }}>
                      <Delete />
                    </IconButton>
                  </ListItemSecondaryAction>
                </ListItem>
              ))}
            </List>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSkillsDialog(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
