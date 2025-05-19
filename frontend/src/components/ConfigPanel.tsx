import { useState, useEffect } from 'react';
import {
  Box,
  Button,
  TextField,
  Switch,
  FormControlLabel,
  Typography,
  Paper,
  Alert,
  CircularProgress,
  IconButton,
  Tooltip,
} from '@mui/material';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import RefreshIcon from '@mui/icons-material/Refresh'; // For the new generate button
import apiService from '@/utils/api';

// Simplified Config interface
interface Config {
  splunk_hec_token: string; // User's unique HEC token (will be raw token)
  allow_anything: boolean;
  summary_mode: boolean;
}

export default function ConfigPanel() {
  const [config, setConfig] = useState<Config | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false); // For general settings save
  const [generatingToken, setGeneratingToken] = useState(false); // For HEC token generation
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [splunkTokenCopied, setSplunkTokenCopied] = useState(false);
  const [systemHecUrl, setSystemHecUrl] = useState('');
  const [systemHecUrlCopied, setSystemHecUrlCopied] = useState(false);

  useEffect(() => {
    const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL;
    if (apiBaseUrl) {
      const normalizedApiBaseUrl = apiBaseUrl.endsWith('/') ? apiBaseUrl.slice(0, -1) : apiBaseUrl;
      setSystemHecUrl(normalizedApiBaseUrl);
    } else {
      console.warn("NEXT_PUBLIC_API_URL is not set. System HEC URL cannot be displayed.");
      setSystemHecUrl("Error: API Base URL not configured in your frontend environment.");
    }

    const fetchConfig = async () => {
      try {
        setLoading(true);
        const data = await apiService.getConfig(); // This should return splunk_hec_token, allow_anything, summary_mode
        const fullConfig: Config = {
          splunk_hec_token: data.splunk_hec_token || '',
          allow_anything: data.allow_anything || false,
          summary_mode: data.summary_mode || false,
        };
        setConfig(fullConfig);
        setError('');
      } catch (err: any) {
        console.error('Error fetching configuration:', err);
        setError(err.response?.data?.message || 'Failed to load configuration. Please try again later.');
      } finally {
        setLoading(false);
      }
    };

    fetchConfig();
  }, []);

  // Handles saving of general settings (allow_anything, summary_mode)
  const handleSubmitSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!config) return;
    try {
      setSaving(true);
      setError('');
      setSuccess('');
      const payloadToSave = {
        allow_anything: config.allow_anything,
        summary_mode: config.summary_mode,
      };
      await apiService.updateConfig(payloadToSave); // updateConfig now only sends these settings
      setSuccess('Settings saved successfully!');
    } catch (err: any) {
      console.error('Error saving settings:', err);
      setError(err.response?.data?.message || 'Failed to save settings. Please try again later.');
    } finally {
      setSaving(false);
    }
  };

  const handleGenerateHecToken = async () => {
    try {
      setGeneratingToken(true);
      setError('');
      setSuccess('');
      const response = await apiService.regenerateSplunkHecToken(); // Calls the new backend endpoint
      if (config && response.splunk_hec_token) {
        setConfig({
          ...config,
          splunk_hec_token: response.splunk_hec_token, // Update with the new raw token
        });
        setSuccess('New Splunk HEC Token generated and saved successfully!');
      } else {
        throw new Error("Failed to retrieve new HEC token from server response.");
      }
    } catch (err: any) {
      console.error('Error generating Splunk HEC Token:', err);
      setError(err.response?.data?.message || 'Failed to generate Splunk HEC Token.');
    } finally {
      setGeneratingToken(false);
    }
  };

  const handleToggleChange = (field: 'allow_anything' | 'summary_mode') => {
    if (!config) return;
    setConfig((prevConfig) => prevConfig ? { ...prevConfig, [field]: !prevConfig[field] } : null);
  };
  
  const handleCopy = (textToCopy: string, setCopiedState: React.Dispatch<React.SetStateAction<boolean>>) => {
    if (!textToCopy) return;
    navigator.clipboard.writeText(textToCopy);
    setCopiedState(true);
    setTimeout(() => setCopiedState(false), 2000);
  };

  if (loading) return <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}><CircularProgress /></Box>;
  
  // Display error prominently if config couldn't be loaded at all
  if (!config && error) {
    return <Alert severity="error" sx={{ m: 2 }}>{error}</Alert>;
  }
  // If config is still null after loading and no error (should not happen if fetchConfig sets error), show generic message
  if (!config) {
     return <Alert severity="info" sx={{ m: 2 }}>Loading configuration...</Alert>;
  }


  return (
    <Box>
      {error && !success && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>{error}</Alert>}
      {success && <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess('')}>{success}</Alert>}

      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>Splunk HEC Configuration</Typography>
        <Typography variant="body2" color="text.secondary" paragraph>
          Your system's Splunk HEC Base URL is displayed below. Enter your unique Splunk HEC Token.
          This token will be used by external systems to send data to this collector on your behalf.
          The HEC Token must be unique across all users of this system.
          Refer to the helper text below the HEC Base URL field for the specific path to use.
        </Typography>
        
        <Box sx={{ mb: 2 }}>
          <Typography variant="subtitle1" gutterBottom sx={{ fontWeight: 'medium' }}>
            HEC Base URL (Read-only):
          </Typography>
          <TextField
            fullWidth
            value={systemHecUrl || 'Loading API Base URL...'}
            InputProps={{
              readOnly: true,
              endAdornment: (
                <Tooltip title={systemHecUrlCopied ? 'Copied!' : 'Copy Base URL'}>
                  <span>
                    <IconButton onClick={() => handleCopy(systemHecUrl, setSystemHecUrlCopied)} disabled={!systemHecUrl || systemHecUrl.startsWith('Error')} size="small" edge="end">
                      <ContentCopyIcon />
                    </IconButton>
                  </span>
                </Tooltip>
              )
            }}
            variant="outlined"
            size="small"
            helperText="External systems should append /services/collector/event to this URL for HEC data."
          />
        </Box>

        <Box sx={{ mb: 1 }}>
           <Typography variant="subtitle1" gutterBottom sx={{ fontWeight: 'medium', mt: 2 }}>
            Your Unique Splunk HEC Token:
          </Typography>
          <TextField
            fullWidth
            value={config.splunk_hec_token ? '********' : 'Not set - Click Generate'} // Masked display
            InputProps={{
              readOnly: true,
              endAdornment: (
                <Tooltip title={splunkTokenCopied ? 'Copied!' : 'Copy Full HEC Authorization Value'}>
                  <span>
                    <IconButton 
                      onClick={() => {
                        if (config.splunk_hec_token) {
                          handleCopy(`Splunk ${config.splunk_hec_token}`, setSplunkTokenCopied);
                        }
                      }} 
                      disabled={!config.splunk_hec_token} 
                      size="small"
                      edge="end"
                      sx={{ mr: 1 }}
                    >
                      <ContentCopyIcon />
                    </IconButton>
                  </span>
                </Tooltip>
              )
            }}
            variant="outlined"
            size="small"
            helperText='Click "Generate Token" to create or replace your HEC token. Copy includes "Splunk " prefix.'
          />
        </Box>
        <Button
            onClick={handleGenerateHecToken}
            variant="outlined"
            size="small"
            startIcon={generatingToken ? <CircularProgress size={16} /> : <RefreshIcon />}
            disabled={generatingToken || loading}
            sx={{ mt: 1, mb:1 }}
        >
            {config.splunk_hec_token ? 'Regenerate HEC Token' : 'Generate HEC Token'}
        </Button>
        {config.splunk_hec_token && (
             <Typography variant="caption" color="text.secondary" sx={{ml:1, mt: 0, display: 'block'}}>
             Last token: "{config.splunk_hec_token.substring(0,4)}...{config.splunk_hec_token.slice(-4)}" (raw value)
           </Typography>
        )}
      </Paper>
      
      <Paper component="form" onSubmit={handleSubmitSettings} sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>Event Processing Settings</Typography>
        <FormControlLabel
          control={<Switch checked={config.allow_anything} onChange={() => handleToggleChange('allow_anything')} name="allow_anything" disabled={saving || loading} />}
          label="Allow any event format (skip schema validation)"
        />
        <FormControlLabel
          control={<Switch checked={config.summary_mode} onChange={() => handleToggleChange('summary_mode')} name="summary_mode" disabled={saving || loading} />}
          label="Summary mode (log summarized events instead of full payloads)"
        />
         <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 2 }}>
            <Button
            type="submit" // This button now only saves allow_anything and summary_mode
            variant="contained"
            color="primary"
            disabled={saving || loading || generatingToken}
            startIcon={saving ? <CircularProgress size={20} /> : null}
            >
            Save Processing Settings
            </Button>
        </Box>
      </Paper>
    </Box>
  );
}
