import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/router';
import { useAuth } from '@/utils/auth';
import apiService from '@/utils/api';
import {
  Box,
  Container,
  Typography,
  Paper,
  Tabs,
  Tab,
  Button, // Keep if used elsewhere, or remove
  CircularProgress,
  Alert,
  AppBar,
  Toolbar,
  IconButton,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Grid, // For layout
  SelectChangeEvent,
} from '@mui/material';
import LogoutIcon from '@mui/icons-material/Logout';
import SettingsIcon from '@mui/icons-material/Settings';
import AccountCircleIcon from '@mui/icons-material/AccountCircle'; // For User Profile tab
import RefreshIcon from '@mui/icons-material/Refresh';
import EventTable from '@/components/EventTable';
import ConfigPanel from '@/components/ConfigPanel';
import UserProfilePanel from '@/components/UserProfilePanel'; // Import the new component

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`tabpanel-${index}`}
      aria-labelledby={`tab-${index}`}
      {...other}
      style={{ padding: '20px 0' }}
    >
      {value === index && <Box>{children}</Box>}
    </div>
  );
}

const REFRESH_INTERVALS = [
  { label: 'Off', value: 0 },
  { label: '10 seconds', value: 10000 },
  { label: '30 seconds', value: 30000 },
  { label: '1 minute', value: 60000 },
  { label: '5 minutes', value: 300000 },
];

export default function Dashboard() {
  const [tabValue, setTabValue] = useState(0);
  const [events, setEvents] = useState<any[]>([]);
  const [initialLoading, setInitialLoading] = useState(true); // For the very first load
  const [isRefreshing, setIsRefreshing] = useState(false); // For manual or auto-refresh loads
  const [error, setError] = useState('');
  const { user, isAuthenticated, isLoading: authIsLoading, logout } = useAuth();
  const router = useRouter();
  const [refreshInterval, setRefreshInterval] = useState<number>(0); // 0 means 'Off'

  // Check authentication
  useEffect(() => {
    if (!authIsLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, authIsLoading, router]);

  // Memoized fetchEvents function
  const fetchEvents = useCallback(async (isManualOrAutoRefresh = false) => {
    if (!isAuthenticated) return;

    if (isManualOrAutoRefresh) {
      setIsRefreshing(true);
    } else {
      setInitialLoading(true);
    }
    setError('');

    try {
      const data = await apiService.getEvents();
      setEvents(data.events || []);
    } catch (err: any) {
      console.error('Error fetching events:', err);
      setError(err.response?.data?.message || 'Failed to load events. Please try again later.');
    } finally {
      if (isManualOrAutoRefresh) {
        setIsRefreshing(false);
      } else {
        setInitialLoading(false);
      }
    }
  }, [isAuthenticated]); // Add any other dependencies if fetchEvents uses them from component scope

  // Initial fetch of events
  useEffect(() => {
    if (isAuthenticated) {
      fetchEvents(false); // Initial load
    }
  }, [isAuthenticated, fetchEvents]);

  // Auto-refresh timer effect
  useEffect(() => {
    if (refreshInterval > 0 && isAuthenticated) {
      const intervalId = setInterval(() => {
        fetchEvents(true); // Auto-refresh
      }, refreshInterval);
      return () => clearInterval(intervalId); // Cleanup interval on unmount or when interval changes
    }
  }, [refreshInterval, isAuthenticated, fetchEvents]);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleRefreshIntervalChange = (event: SelectChangeEvent<number>) => {
    setRefreshInterval(Number(event.target.value));
  };

  const handleManualRefresh = () => {
    fetchEvents(true); // Manual refresh
  };

  if (authIsLoading || (initialLoading && tabValue === 0)) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Nile Collector Dashboard
          </Typography>
          {user && (
            <Typography variant="body1" sx={{ mr: 2 }} title={`User ID: ${user.id}\nUsername: ${user.username}\nEmail: ${user.email}`}>
              {user.name || user.email || user.username} {/* Display name, fallback to email/username */}
            </Typography>
          )}
          {/* Settings icon now navigates to User Profile tab (index 2) */}
          <IconButton color="inherit" onClick={() => setTabValue(2)} title="User Profile & Settings" aria-label="user profile and settings">
            <AccountCircleIcon /> 
          </IconButton>
          <IconButton color="inherit" onClick={logout} title="Logout" aria-label="logout">
            <LogoutIcon />
          </IconButton>
        </Toolbar>
      </AppBar>

      <Container maxWidth="lg" sx={{ flexGrow: 1, py: 4 }}>
        <Paper elevation={3} sx={{ p: 3 }}>
          <Tabs value={tabValue} onChange={handleTabChange} aria-label="dashboard tabs">
            <Tab label="Events" id="tab-0" aria-controls="tabpanel-0" />
            <Tab label="Collector Configuration" id="tab-1" aria-controls="tabpanel-1" />
            <Tab label="User Profile" id="tab-2" aria-controls="tabpanel-2" />
          </Tabs>

          {error && tabValue === 0 && ( // Only show event fetch error on events tab
            <Alert severity="error" sx={{ mt: 2 }} onClose={() => setError('')}>
              {error}
            </Alert>
          )}

          <TabPanel value={tabValue} index={0}>
            <Grid container justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
              <Grid item>
                <Typography variant="h5" gutterBottom>
                  Collected Events
                </Typography>
              </Grid>
              <Grid item sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <FormControl size="small" sx={{ minWidth: 120 }}>
                  <InputLabel id="refresh-interval-label">Refresh</InputLabel>
                  <Select
                    labelId="refresh-interval-label"
                    id="refresh-interval-select"
                    value={refreshInterval}
                    label="Refresh"
                    onChange={handleRefreshIntervalChange}
                  >
                    {REFRESH_INTERVALS.map((item) => (
                      <MenuItem key={item.value} value={item.value}>
                        {item.label}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
                <IconButton onClick={handleManualRefresh} disabled={isRefreshing} color="primary" aria-label="refresh events">
                  {isRefreshing ? <CircularProgress size={24} /> : <RefreshIcon />}
                </IconButton>
              </Grid>
            </Grid>
            
            {(initialLoading && !isRefreshing) ? ( // Show initial loading spinner only if not also a refresh
              <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                <CircularProgress />
              </Box>
            ) : events.length === 0 && !error ? (
                <Typography sx={{mt: 2}}>No events found.</Typography>
            ) : !error ? (
              <EventTable events={events} />
            ) : null}
          </TabPanel>

          <TabPanel value={tabValue} index={1}>
            <Typography variant="h5" gutterBottom>
              Collector Configuration
            </Typography>
            <ConfigPanel />
          </TabPanel>

          <TabPanel value={tabValue} index={2}>
            <Typography variant="h5" gutterBottom>
              User Profile
            </Typography>
            <UserProfilePanel />
          </TabPanel>
        </Paper>
      </Container>
    </Box>
  );
}
