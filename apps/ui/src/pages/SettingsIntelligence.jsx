/**
 * ALPHA OMEGA - Intelligence Settings Page
 * Category: 🧠 INTELLIGENCE (~80 settings)
 */

import React from 'react';
import {
  Box,
  Typography,
  Tabs,
  Tab,
  Alert,
  Chip,
  Grid,
} from '@mui/material';
import {
  Psychology,
  Storage,
  Tune,
  Cloud,
} from '@mui/icons-material';
import {
  SettingsHeader,
  SettingsSection,
  ToggleSetting,
  SliderSetting,
  DropdownSetting,
  PasswordSetting,
  SettingsActions,
  useSettings,
} from '../components/SettingsComponents';

function TabPanel({ children, value, index }) {
  return value === index ? <Box sx={{ pt: 2 }}>{children}</Box> : null;
}

export default function SettingsIntelligence() {
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
  } = useSettings('intelligence');

  const [tab, setTab] = React.useState(0);

  const handleClearApiKey = async (provider) => {
    try {
      await fetch(`http://localhost:8000/settings/api-keys/${provider}`, {
        method: 'DELETE',
      });
      updateSetting(`${provider}_api_key`, '');
    } catch (err) {
      console.error('Failed to clear API key:', err);
    }
  };

  if (loading) {
    return <Typography sx={{ color: '#888', p: 3 }}>Loading intelligence settings...</Typography>;
  }

  const providerConfigured = settings.llm_provider && settings.llm_provider !== 'local';

  return (
    <Box sx={{ p: 3, pb: 10 }}>
      <SettingsHeader
        title="Intelligence Settings"
        description="Configure LLM providers, model selection, and AI behavior"
        icon={<Psychology sx={{ color: '#00e5ff', fontSize: 32 }} />}
      />

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Tabs
        value={tab}
        onChange={(e, v) => setTab(v)}
        sx={{
          mb: 2,
          '& .MuiTab-root': { color: '#888' },
          '& .MuiTab-root.Mui-selected': { color: '#00e5ff' },
          '& .MuiTabs-indicator': { backgroundColor: '#00e5ff' },
        }}
      >
        <Tab label="Provider" icon={<Cloud />} />
        <Tab label="Model" icon={<Psychology />} />
        <Tab label="Behavior" icon={<Tune />} />
        <Tab label="Memory" icon={<Storage />} />
      </Tabs>

      <TabPanel value={tab} index={0}>
        <SettingsSection title="LLM Provider">
          <DropdownSetting
            label="Primary Provider"
            description="Choose your AI provider"
            value={settings.llm_provider || 'local'}
            onChange={(v) => updateSetting('llm_provider', v)}
            options={['local', 'openai', 'anthropic', 'google', 'groq', 'openrouter']}
          />

          {settings.llm_provider === 'local' && (
            <Alert severity="info" sx={{ mt: 2 }}>
              Local mode runs entirely on your device. No internet required, but limited by your hardware.
            </Alert>
          )}
        </SettingsSection>

        <SettingsSection title="API Keys">
          <Typography variant="caption" sx={{ color: '#888', mb: 2, display: 'block' }}>
            API keys are stored encrypted in the vault
          </Typography>

          <Grid container spacing={2}>
            {settings.llm_provider === 'openai' || settings.llm_provider === 'all' ? (
              <Grid item xs={12} md={6}>
                <PasswordSetting
                  label="OpenAI API Key"
                  description="For GPT models"
                  value={settings.openai_api_key || ''}
                  onChange={(v) => updateSetting('openai_api_key', v)}
                  onClear={() => handleClearApiKey('openai')}
                />
              </Grid>
            ) : null}

            {settings.llm_provider === 'anthropic' || settings.llm_provider === 'all' ? (
              <Grid item xs={12} md={6}>
                <PasswordSetting
                  label="Anthropic API Key"
                  description="For Claude models"
                  value={settings.anthropic_api_key || ''}
                  onChange={(v) => updateSetting('anthropic_api_key', v)}
                  onClear={() => handleClearApiKey('anthropic')}
                />
              </Grid>
            ) : null}

            {settings.llm_provider === 'google' || settings.llm_provider === 'all' ? (
              <Grid item xs={12} md={6}>
                <PasswordSetting
                  label="Google API Key"
                  description="For Gemini models"
                  value={settings.google_api_key || ''}
                  onChange={(v) => updateSetting('google_api_key', v)}
                  onClear={() => handleClearApiKey('google')}
                />
              </Grid>
            ) : null}

            {settings.llm_provider === 'groq' || settings.llm_provider === 'all' ? (
              <Grid item xs={12} md={6}>
                <PasswordSetting
                  label="Groq API Key"
                  description="For fast inference"
                  value={settings.groq_api_key || ''}
                  onChange={(v) => updateSetting('groq_api_key', v)}
                  onClear={() => handleClearApiKey('groq')}
                />
              </Grid>
            ) : null}

            {settings.llm_provider === 'openrouter' || settings.llm_provider === 'all' ? (
              <Grid item xs={12} md={6}>
                <PasswordSetting
                  label="OpenRouter API Key"
                  description="Access multiple providers"
                  value={settings.openrouter_api_key || ''}
                  onChange={(v) => updateSetting('openrouter_api_key', v)}
                  onClear={() => handleClearApiKey('openrouter')}
                />
              </Grid>
            ) : null}
          </Grid>
        </SettingsSection>
      </TabPanel>

      <TabPanel value={tab} index={1}>
        <SettingsSection title="Model Selection">
          <DropdownSetting
            label="Primary Model"
            description="Main model for responses"
            value={settings.primary_model || 'phi-3-mini'}
            onChange={(v) => updateSetting('primary_model', v)}
            options={['phi-3-mini', 'llama-3.1-8b', 'mistral-7b', 'gpt-4o-mini', 'claude-3-haiku', 'gemini-2.0-flash']}
          />

          <DropdownSetting
            label="Fallback Model"
            description="Backup when primary fails"
            value={settings.fallback_model || 'tinyllama'}
            onChange={(v) => updateSetting('fallback_model', v)}
            options={['tinyllama', 'phi-3-mini', 'gpt-3.5-turbo']}
          />
        </SettingsSection>

        <SettingsSection title="Context Settings">
          <SliderSetting
            label="Context Window"
            description="Conversation memory size (tokens)"
            value={settings.context_window || 4096}
            onChange={(v) => updateSetting('context_window', v)}
            min={1024}
            max={32768}
            step={1024}
            unit=" tokens"
          />

          <SliderSetting
            label="Max Tokens"
            description="Maximum response length"
            value={settings.max_tokens || 512}
            onChange={(v) => updateSetting('max_tokens', v)}
            min={50}
            max={4096}
            step={50}
            unit=" tokens"
          />
        </SettingsSection>
      </TabPanel>

      <TabPanel value={tab} index={2}>
        <SettingsSection title="Response Behavior">
          <SliderSetting
            label="Temperature"
            description="Creativity level (0 = deterministic, 2 = very creative)"
            value={settings.temperature || 0.7}
            onChange={(v) => updateSetting('temperature', v)}
            min={0}
            max={2}
            step={0.1}
          />

          <SliderSetting
            label="Top P"
            description="Nucleus sampling (0.9 = balanced)"
            value={settings.top_p || 0.9}
            onChange={(v) => updateSetting('top_p', v)}
            min={0}
            max={1}
            step={0.05}
          />
        </SettingsSection>

        <SettingsSection title="Reasoning">
          <ToggleSetting
            label="Chain of Thought"
            description="Show reasoning steps"
            value={settings.reasoning_enabled || false}
            onChange={(v) => updateSetting('reasoning_enabled', v)}
          />

          <ToggleSetting
            label="Multi-Step Reasoning"
            description="Break complex tasks into steps"
            value={settings.multi_step !== false}
            onChange={(v) => updateSetting('multi_step', v)}
          />

          <SliderSetting
            label="Confidence Threshold"
            description="Minimum confidence to act autonomously"
            value={settings.confidence_threshold || 70}
            onChange={(v) => updateSetting('confidence_threshold', v)}
            min={0}
            max={100}
            unit="%"
          />
        </SettingsSection>
      </TabPanel>

      <TabPanel value={tab} index={3}>
        <SettingsSection title="Memory Settings">
          <ToggleSetting
            label="Long-Term Memory"
            description="Persist conversations across sessions"
            value={settings.long_term_memory !== false}
            onChange={(v) => updateSetting('long_term_memory', v)}
          />

          <SliderSetting
            label="Memory Retention"
            description="Days to keep memories"
            value={settings.memory_retention_days || 30}
            onChange={(v) => updateSetting('memory_retention_days', v)}
            min={1}
            max={365}
            unit=" days"
          />
        </SettingsSection>
      </TabPanel>

      <SettingsActions
        hasChanges={hasChanges}
        saving={saving}
        onSave={saveSettings}
        onReset={resetSettings}
        onRevert={revertChanges}
      />
    </Box>
  );
}
