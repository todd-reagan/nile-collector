import { useEffect } from 'react';
import { useRouter } from 'next/router';
import { useAuth } from '@/utils/auth';
import { Box, Typography, Button, Container, Paper } from '@mui/material';

export default function Home() {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    // If user is authenticated, redirect to dashboard
    if (isAuthenticated && !isLoading) {
      router.push('/dashboard');
    }
  }, [isAuthenticated, isLoading, router]);

  return (
    <Container maxWidth="lg">
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '100vh',
          textAlign: 'center',
          py: 4,
        }}
      >
        <Paper
          elevation={3}
          sx={{
            p: 4,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            maxWidth: 600,
            width: '100%',
          }}
        >
          <Typography variant="h2" component="h1" gutterBottom>
            Nile Collector
          </Typography>
          <Typography variant="h5" component="h2" gutterBottom>
            A serverless HTTP event collector for AWS
          </Typography>
          <Typography variant="body1" paragraph sx={{ mb: 4 }}>
            Collect, process, and analyze HTTP events using AWS Lambda, API Gateway, and DynamoDB.
          </Typography>

          <Box sx={{ mt: 2, display: 'flex', gap: 2 }}>
            <Button
              variant="contained"
              color="primary"
              size="large"
              onClick={() => router.push('/login')}
            >
              Login
            </Button>
            <Button
              variant="outlined"
              color="primary"
              size="large"
              onClick={() => router.push('/register')}
            >
              Register
            </Button>
          </Box>
        </Paper>
      </Box>
    </Container>
  );
}
