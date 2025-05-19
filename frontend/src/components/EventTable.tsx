import { useState } from 'react';
import {
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
} from '@mui/material';
import VisibilityIcon from '@mui/icons-material/Visibility';
// Removed JSONTree import

interface Event {
  id: string;
  timestamp: number;
  event_type: string;
  event_data: any;
  created_at: string;
}

interface EventTableProps {
  events: Event[];
}

export default function EventTable({ events }: EventTableProps) {
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [selectedEvent, setSelectedEvent] = useState<Event | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(false);

  const handleChangePage = (event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const handleViewDetails = (event: Event) => {
    setSelectedEvent(event);
    setDetailsOpen(true);
  };

  const handleCloseDetails = () => {
    setDetailsOpen(false);
  };

  // Format timestamp to readable date
  const formatDate = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleString();
  };

  // Get event type color
  const getEventTypeColor = (eventType: string) => {
    switch (eventType) {
      case 'audit_trail':
        return 'primary';
      case 'end_user_device_events':
        return 'secondary';
      case 'nile_alerts':
        return 'error';
      default:
        return 'default';
    }
  };

  return (
    <>
      <TableContainer component={Paper}>
        <Table sx={{ minWidth: 650 }} aria-label="events table">
          <TableHead>
            <TableRow>
              <TableCell>ID</TableCell>
              <TableCell>Timestamp</TableCell>
              <TableCell>Event Type</TableCell>
              <TableCell>Created At</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {events.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} align="center">
                  No events found
                </TableCell>
              </TableRow>
            ) : (
              events
                .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
                .map((event) => (
                  <TableRow 
                    key={event.id} 
                    hover 
                    onClick={() => handleViewDetails(event)}
                    sx={{ cursor: 'pointer' }}
                  >
                    <TableCell component="th" scope="row">
                      {event.id.substring(0, 8)}...
                    </TableCell>
                    <TableCell>{formatDate(event.timestamp)}</TableCell>
                    <TableCell>
                      <Chip
                        label={event.event_type}
                        color={getEventTypeColor(event.event_type) as any}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>{new Date(event.created_at).toLocaleString()}</TableCell>
                    <TableCell align="right">
                      <IconButton
                        aria-label="view details"
                        onClick={() => handleViewDetails(event)}
                        size="small"
                      >
                        <VisibilityIcon />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))
            )}
          </TableBody>
        </Table>
      </TableContainer>
      <TablePagination
        rowsPerPageOptions={[5, 10, 25]}
        component="div"
        count={events.length}
        rowsPerPage={rowsPerPage}
        page={page}
        onPageChange={handleChangePage}
        onRowsPerPageChange={handleChangeRowsPerPage}
      />

      {/* Event Details Dialog */}
      <Dialog
        open={detailsOpen}
        onClose={handleCloseDetails}
        maxWidth="md"
        fullWidth
        aria-labelledby="event-details-dialog"
      >
        <DialogTitle id="event-details-dialog">Event Details</DialogTitle>
        <DialogContent dividers>
          {selectedEvent && (
            <Box>
              <Typography variant="subtitle1" gutterBottom>
                ID: {selectedEvent.id}
              </Typography>
              <Typography variant="subtitle1" gutterBottom>
                Timestamp: {formatDate(selectedEvent.timestamp)}
              </Typography>
              <Typography variant="subtitle1" gutterBottom>
                Event Type: {selectedEvent.event_type}
              </Typography>
              <Typography variant="subtitle1" gutterBottom>
                Created At: {new Date(selectedEvent.created_at).toLocaleString()}
              </Typography>
              <Typography variant="subtitle1" gutterBottom>
                Event Data:
              </Typography>
              <Box sx={{ mt: 2, p: 2, bgcolor: 'background.paper', borderRadius: 1 }}>
                <Box 
                  sx={{ 
                    maxHeight: '400px', 
                    overflow: 'auto',
                    fontFamily: 'monospace',
                    whiteSpace: 'pre-wrap',
                    backgroundColor: '#272822',
                    color: '#f8f8f2',
                    padding: 2,
                    borderRadius: 1
                  }}
                >
                  {JSON.stringify(selectedEvent.event_data, null, 2)}
                </Box>
              </Box>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDetails}>Close</Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
