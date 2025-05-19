import React, { useState, useEffect } from 'react';
import { useAuth } from '@/utils/auth';
import {
  Box,
  Button,
  TextField,
  Typography,
  Paper,
  Alert,
  CircularProgress,
  Divider,
  Grid,
} from '@mui/material';

export default function UserProfilePanel() {
  const { user, changePassword, updateUserAttributes, isLoading: authLoading } = useAuth();

  // State for Change Password form
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmNewPassword, setConfirmNewPassword] = useState('');
  const [passwordChangeLoading, setPasswordChangeLoading] = useState(false);
  const [passwordChangeError, setPasswordChangeError] = useState('');
  const [passwordChangeSuccess, setPasswordChangeSuccess] = useState('');

  // State for Update Name form
  const [name, setName] = useState('');
  const [nameUpdateLoading, setNameUpdateLoading] = useState(false);
  const [nameUpdateError, setNameUpdateError] = useState('');
  const [nameUpdateSuccess, setNameUpdateSuccess] = useState('');

  useEffect(() => {
    if (user) {
      setName(user.name || '');
    }
  }, [user]);

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordChangeError('');
    setPasswordChangeSuccess('');

    if (newPassword !== confirmNewPassword) {
      setPasswordChangeError('New passwords do not match.');
      return;
    }
    if (newPassword.length < 8) { // Basic validation, align with Cognito policy
        setPasswordChangeError('New password must be at least 8 characters long.');
        return;
    }

    setPasswordChangeLoading(true);
    try {
      await changePassword(currentPassword, newPassword);
      setPasswordChangeSuccess('Password changed successfully!');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmNewPassword('');
    } catch (err: any) {
      console.error('Change password error:', err);
      setPasswordChangeError(err.message || 'Failed to change password.');
    } finally {
      setPasswordChangeLoading(false);
    }
  };

  const handleUpdateName = async (e: React.FormEvent) => {
    e.preventDefault();
    setNameUpdateError('');
    setNameUpdateSuccess('');

    if (!name.trim()) {
      setNameUpdateError('Name cannot be empty.');
      return;
    }

    setNameUpdateLoading(true);
    try {
      await updateUserAttributes([{ Name: 'name', Value: name }]);
      setNameUpdateSuccess('Name updated successfully!');
      // The user object in useAuth context will be updated automatically by updateUserAttributes
    } catch (err: any) {
      console.error('Update name error:', err);
      setNameUpdateError(err.message || 'Failed to update name.');
    } finally {
      setNameUpdateLoading(false);
    }
  };
  
  if (authLoading && !user) {
    return <CircularProgress />;
  }

  if (!user) {
    return <Alert severity="warning">User data not available. Please try logging in again.</Alert>;
  }

  return (
    <Box>
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Update Profile Information
        </Typography>
        <form onSubmit={handleUpdateName}>
          <Grid container spacing={2} alignItems="flex-end">
            <Grid item xs={12} sm={8}>
              <TextField
                fullWidth
                label="Full Name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                variant="outlined"
                size="small"
                required
                disabled={nameUpdateLoading || authLoading}
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <Button
                type="submit"
                variant="contained"
                color="primary"
                disabled={nameUpdateLoading || authLoading || name === user.name}
                startIcon={nameUpdateLoading ? <CircularProgress size={20} /> : null}
                fullWidth
              >
                Update Name
              </Button>
            </Grid>
          </Grid>
          {nameUpdateError && <Alert severity="error" sx={{ mt: 2 }}>{nameUpdateError}</Alert>}
          {nameUpdateSuccess && <Alert severity="success" sx={{ mt: 2 }}>{nameUpdateSuccess}</Alert>}
        </form>
      </Paper>

      <Divider sx={{ my: 3 }} />

      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Change Password
        </Typography>
        <form onSubmit={handleChangePassword}>
          <TextField
            margin="normal"
            required
            fullWidth
            name="currentPassword"
            label="Current Password"
            type="password"
            id="currentPassword"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            disabled={passwordChangeLoading || authLoading}
            size="small"
          />
          <TextField
            margin="normal"
            required
            fullWidth
            name="newPassword"
            label="New Password"
            type="password"
            id="newPassword"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            disabled={passwordChangeLoading || authLoading}
            size="small"
            helperText="Password must be at least 8 characters, include upper, lower, number, and symbol."
          />
          <TextField
            margin="normal"
            required
            fullWidth
            name="confirmNewPassword"
            label="Confirm New Password"
            type="password"
            id="confirmNewPassword"
            value={confirmNewPassword}
            onChange={(e) => setConfirmNewPassword(e.target.value)}
            disabled={passwordChangeLoading || authLoading}
            size="small"
          />
          {passwordChangeError && <Alert severity="error" sx={{ mt: 2 }}>{passwordChangeError}</Alert>}
          {passwordChangeSuccess && <Alert severity="success" sx={{ mt: 2 }}>{passwordChangeSuccess}</Alert>}
          <Box sx={{ mt: 2, display: 'flex', justifyContent: 'flex-end' }}>
            <Button
              type="submit"
              variant="contained"
              color="primary"
              disabled={passwordChangeLoading || authLoading}
              startIcon={passwordChangeLoading ? <CircularProgress size={20} /> : null}
            >
              Change Password
            </Button>
          </Box>
        </form>
      </Paper>
    </Box>
  );
}
