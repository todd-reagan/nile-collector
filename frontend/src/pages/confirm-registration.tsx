import { useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { useAuth } from '@/utils/auth';
import {
  Box,
  Button,
  Container,
  TextField,
  Typography,
  Paper,
  Alert,
  CircularProgress,
} from '@mui/material';

export default function ConfirmRegistration() {
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { confirmRegistration } = useAuth();
  const router = useRouter();

  // Pre-fill email if provided in query params
  useState(() => {
    if (router.query.email) {
      setEmail(router.query.email as string);
    }
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);

    try {
      await confirmRegistration(email, code);
      // Redirect is handled in the confirmRegistration function
    } catch (err: any) {
      setError(err.message || 'Failed to confirm registration. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Container maxWidth="sm">
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '100vh',
        }}
      >
        <Paper
          elevation={3}
          sx={{
            p: 4,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            width: '100%',
          }}
        >
          <Typography variant="h4" component="h1" gutterBottom>
            Confirm Registration
          </Typography>
          
          <Typography variant="body1" sx={{ mb: 3, textAlign: 'center' }}>
            Please enter the verification code sent to your email address.
          </Typography>

          {error && (
            <Alert severity="error" sx={{ width: '100%', mb: 2 }}>
              {error}
            </Alert>
          )}

          <Box component="form" onSubmit={handleSubmit} sx={{ width: '100%' }}>
            <TextField
              margin="normal"
              required
              fullWidth
              id="email"
              label="Email Address"
              name="email"
              autoComplete="email"
              autoFocus
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={isSubmitting}
            />
            <TextField
              margin="normal"
              required
              fullWidth
              name="code"
              label="Verification Code"
              id="code"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              disabled={isSubmitting}
            />
            <Button
              type="submit"
              fullWidth
              variant="contained"
              sx={{ mt: 3, mb: 2 }}
              disabled={isSubmitting}
            >
              {isSubmitting ? <CircularProgress size={24} /> : 'Verify'}
            </Button>
          </Box>

          <Box sx={{ mt: 2, display: 'flex', justifyContent: 'space-between', width: '100%' }}>
            <Link href="/login" passHref>
              <Typography variant="body2" component="a" sx={{ cursor: 'pointer' }}>
                Back to login
              </Typography>
            </Link>
            <Link href="/register" passHref>
              <Typography variant="body2" component="a" sx={{ cursor: 'pointer' }}>
                Register again
              </Typography>
            </Link>
          </Box>
        </Paper>
      </Box>
    </Container>
  );
}
