import React, { useState } from 'react';
import {
  Box,
  Typography,
  Button,
  Alert,
  CircularProgress,
  Stack,
  Fade,
  Grow,
  useTheme,
  useMediaQuery,
  FormControlLabel,
  Switch,
} from '@mui/material';
import { 
  Send as SendIcon,
  Phone as PhoneIcon,
  Description as DocumentIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  Schedule as ScheduleIcon,
} from '@mui/icons-material';
import { DateTimePicker } from '@mui/x-date-pickers/DateTimePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import dayjs, { Dayjs } from 'dayjs';
import AdminAPIClient from '../api/client';
import {
  ResponsiveTextField,
  ResponsiveFileUpload,
  ResponsiveFormSection,
} from './common/ResponsiveFormFields';

interface SendFaxProps {
  client: AdminAPIClient;
}

function SendFax({ client }: SendFaxProps) {
  const theme = useTheme();
  const isSmallMobile = useMediaQuery(theme.breakpoints.down('sm'));
  
  const [toNumber, setToNumber] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ type: 'success' | 'error'; message: string; jobId?: string } | null>(null);

  // Schedule state
  const [enableSchedule, setEnableSchedule] = useState(false);
  const [scheduleAt, setScheduleAt] = useState<Dayjs | null>(null);
  const [scheduleAtError, setScheduleAtError] = useState<string | null>(null);

  // Validation states
  const [toNumberError, setToNumberError] = useState(false);
  const [fileError, setFileError] = useState(false);

  const validatePhone = (number: string): boolean => {
    // Basic validation - allow digits, spaces, dashes, parentheses, and +
    const cleanNumber = number.replace(/[\s\-\(\)]/g, '');
    if (!cleanNumber) return false;
    if (cleanNumber.startsWith('+')) {
      return cleanNumber.length >= 11 && cleanNumber.length <= 15;
    }
    return cleanNumber.length >= 10 && cleanNumber.length <= 15;
  };

  const handleSend = async () => {
    // Reset errors
    setToNumberError(false);
    setFileError(false);
    setScheduleAtError(null);

    // Validate inputs
    let hasError = false;
    
    if (!toNumber.trim() || !validatePhone(toNumber)) {
      setToNumberError(true);
      hasError = true;
    }
    
    if (!file) {
      setFileError(true);
      hasError = true;
    }

    // Validate schedule_at: must not be in the past
    if (enableSchedule) {
      if (!scheduleAt || !scheduleAt.isValid()) {
        setScheduleAtError('Please select a valid date and time.');
        hasError = true;
      } else if (scheduleAt.isBefore(dayjs())) {
        setScheduleAtError('Scheduled time cannot be in the past.');
        hasError = true;
      }
    }

    if (hasError) {
      setResult({
        type: 'error',
        message: 'Please fix the errors above before sending.',
      });
      return;
    }

    setLoading(true);
    setResult(null);

    try {
      const scheduleAtISO = enableSchedule && scheduleAt ? scheduleAt.toISOString() : undefined;
      const response = await client.sendFax(toNumber, file!, scheduleAtISO);
      setResult({
        type: 'success',
        message: enableSchedule && scheduleAt
          ? `Fax scheduled for ${scheduleAt.format('MMM D, YYYY h:mm A')}!`
          : `Fax queued successfully!`,
        jobId: response.id,
      });
      
      // Clear form on success
      setToNumber('');
      setFile(null);
      setEnableSchedule(false);
      setScheduleAt(null);

    } catch (err) {
      setResult({
        type: 'error',
        message: err instanceof Error ? err.message : 'Failed to send fax',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !loading && toNumber && file) {
      handleSend();
    }
  };

  return (
    <LocalizationProvider dateAdapter={AdapterDayjs}>
    <Box onKeyPress={handleKeyPress}>
      <Typography variant="h4" component="h1" gutterBottom sx={{ mb: 3 }}>
        Send Fax
      </Typography>

      <Box sx={{ maxWidth: { xs: '100%', md: 800 } }}>
        <Fade in timeout={300}>
          <Box>
            <ResponsiveFormSection
              title="New Fax Transmission"
              subtitle="Send a fax to any phone number with PDF or TXT file attachment"
              icon={<SendIcon />}
            >
              <Stack spacing={2}>
                <ResponsiveTextField
                  label="Destination Number"
                  value={toNumber}
                  onChange={(value) => {
                    setToNumber(value);
                    if (toNumberError) setToNumberError(false);
                  }}
                  placeholder="+15551234567"
                  helperText="Enter in E.164 format (+1XXXXXXXXXX) or 10-digit US number"
                  type="tel"
                  required
                  error={toNumberError}
                  errorMessage="Please enter a valid phone number"
                  icon={<PhoneIcon />}
                />

                <ResponsiveFileUpload
                  label="Document to Fax"
                  value={file}
                  onFileSelect={(file) => {
                    setFile(file);
                    if (fileError) setFileError(false);
                  }}
                  accept=".pdf,.txt,application/pdf,text/plain"
                  helperText="PDF or TXT files only. Maximum size: 10MB"
                  maxSize={10 * 1024 * 1024}
                  required
                  error={fileError}
                  errorMessage="Please select a PDF or TXT file to send"
                  icon={<DocumentIcon />}
                />

                {/* Schedule section */}
                <Box>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={enableSchedule}
                        onChange={(e) => {
                          setEnableSchedule(e.target.checked);
                          if (!e.target.checked) {
                            setScheduleAt(null);
                            setScheduleAtError(null);
                          }
                        }}
                        color="primary"
                      />
                    }
                    label={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        <ScheduleIcon fontSize="small" sx={{ color: 'text.secondary' }} />
                        <Typography variant="subtitle2" fontWeight={600}>
                          Schedule for later
                        </Typography>
                      </Box>
                    }
                  />

                  {enableSchedule && (
                    <Box sx={{ mt: 1.5, ml: 0.5 }}>
                      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
                        Select a future date and time to schedule delivery
                      </Typography>
                      <DateTimePicker
                        label="Schedule At"
                        value={scheduleAt}
                        onChange={(newValue) => {
                          setScheduleAt(newValue);
                          setScheduleAtError(null);
                        }}
                        minDateTime={dayjs().add(1, 'minute')}
                        slotProps={{
                          textField: {
                            size: 'small',
                            fullWidth: true,
                            error: !!scheduleAtError,
                            helperText: scheduleAtError ?? undefined,
                            sx: {
                              '& .MuiOutlinedInput-root': { borderRadius: 2 },
                            },
                          },
                        }}
                      />
                    </Box>
                  )}
                </Box>

                <Box sx={{
                  display: 'flex', 
                  gap: 2, 
                  mt: 3,
                  flexDirection: { xs: 'column', sm: 'row' }
                }}>
                  <Button
                    variant="contained"
                    startIcon={loading ? <CircularProgress size={20} color="inherit" /> : enableSchedule ? <ScheduleIcon /> : <SendIcon />}
                    onClick={handleSend}
                    disabled={loading}
                    size="large"
                    fullWidth={isSmallMobile}
                    sx={{
                      minWidth: { xs: '100%', sm: 200 },
                      height: { xs: 48, sm: 42 },
                      borderRadius: 2,
                      textTransform: 'none',
                      fontSize: '1rem',
                      fontWeight: 500,
                    }}
                  >
                    {loading
                      ? (enableSchedule ? 'Scheduling...' : 'Sending...')
                      : (enableSchedule ? 'Schedule Fax' : 'Send Fax')}
                  </Button>

                  {(toNumber || file) && !loading && (
                    <Button
                      variant="outlined"
                      onClick={() => {
                        setToNumber('');
                        setFile(null);
                        setResult(null);
                        setToNumberError(false);
                        setFileError(false);
                        setEnableSchedule(false);
                        setScheduleAt(null);
                        setScheduleAtError(null);
                      }}
                      size="large"
                      fullWidth={isSmallMobile}
                      sx={{
                        minWidth: { xs: '100%', sm: 120 },
                        height: { xs: 48, sm: 42 },
                        borderRadius: 2,
                        textTransform: 'none',
                      }}
                    >
                      Clear
                    </Button>
                  )}
                </Box>
              </Stack>
            </ResponsiveFormSection>
          </Box>
        </Fade>

        {/* Result Alert */}
        {result && (
          <Grow in timeout={300}>
            <Alert 
              severity={result.type}
              icon={result.type === 'success' ? <SuccessIcon /> : <ErrorIcon />}
              sx={{ 
                mt: 3,
                borderRadius: 2,
                '& .MuiAlert-message': {
                  width: '100%'
                }
              }}
              onClose={() => setResult(null)}
            >
              <Box>
                <Typography variant="body1" fontWeight={500}>
                  {result.message}
                </Typography>
                {result.jobId && (
                  <Box sx={{ mt: 1 }}>
                    <Typography variant="body2" color="text.secondary">
                      Job ID: <strong>{result.jobId}</strong>
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      You can track the status in the Jobs tab
                    </Typography>
                  </Box>
                )}
              </Box>
            </Alert>
          </Grow>
        )}

        {/* Instructions */}
        <Fade in timeout={600}>
          <Box sx={{ mt: 4 }}>
            <ResponsiveFormSection
              title="Quick Tips"
              subtitle="Best practices for successful fax transmission"
            >
              <Stack spacing={2}>
                <Box>
                  <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 0.5 }}>
                    Phone Number Format
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    • Use E.164 format for international: +1 555 123 4567<br />
                    • US numbers can be entered as: (555) 123-4567 or 5551234567<br />
                    • Avoid extensions or special characters
                  </Typography>
                </Box>

                <Box>
                  <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 0.5 }}>
                    File Requirements
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    • PDF files: Standard documents, forms, letters<br />
                    • TXT files: Plain text will be converted to PDF automatically<br />
                    • Maximum file size: 10MB<br />
                    • Images: Convert to PDF first using a PDF creator
                  </Typography>
                </Box>

                <Box>
                  <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 0.5 }}>
                    Transmission Time
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    • Most faxes complete within 2-5 minutes<br />
                    • Large documents may take longer<br />
                    • Check the Jobs tab to monitor progress<br />
                    • You'll see real-time status updates there
                  </Typography>
                </Box>

                <Box>
                  <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 0.5 }}>
                    Scheduling
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    • Toggle "Schedule for later" to pick a future date &amp; time<br />
                    • Leave it off to send immediately<br />
                    • Scheduled time must be in the future<br />
                    • Scheduled faxes appear in the Jobs tab with a "scheduled" status
                  </Typography>
                </Box>
              </Stack>
            </ResponsiveFormSection>
          </Box>
        </Fade>
      </Box>
    </Box>
    </LocalizationProvider>
  );
}

export default SendFax;