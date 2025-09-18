import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import dotenv from 'dotenv';
import axios from 'axios';
import multer from 'multer';
import * as path from 'path';

dotenv.config();

const app = express();
const PORT = process.env.PORT || 3000;
const GENERATOR_URL = process.env.GENERATOR_URL || 'http://localhost:3001';

// Middleware
app.use(helmet());
app.use(cors());
app.use(express.json());
app.use(express.static('public'));

// Multer for file uploads
const upload = multer({ dest: 'uploads/' });

// Serve static files
app.use(express.static(path.join(__dirname, '../public')));

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// Get available modules
app.get('/api/modules', async (req, res) => {
  try {
    const response = await axios.get(`${GENERATOR_URL}/modules`);
    res.json(response.data);
  } catch (error) {
    console.error('Failed to fetch modules:', error);
    res.status(500).json({ error: 'Failed to fetch modules' });
  }
});

// Generate app
app.post('/api/generate', async (req, res) => {
  try {
    const response = await axios.post(`${GENERATOR_URL}/generate`, req.body);
    res.json(response.data);
  } catch (error) {
    console.error('Failed to generate app:', error);
    res.status(500).json({ error: 'Failed to generate app' });
  }
});

// Get app status
app.get('/api/apps/:appId/status', async (req, res) => {
  try {
    const { appId } = req.params;
    const response = await axios.get(`${GENERATOR_URL}/apps/${appId}/status`);
    res.json(response.data);
  } catch (error) {
    console.error('Failed to fetch app status:', error);
    res.status(500).json({ error: 'Failed to fetch app status' });
  }
});

// Serve the main dashboard
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, '../public/index.html'));
});

app.listen(PORT, () => {
  console.log(`Jarvis Dashboard running on port ${PORT}`);
  console.log(`Generator URL: ${GENERATOR_URL}`);
});
