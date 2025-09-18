import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import dotenv from 'dotenv';
import { AppGenerator } from './generator';
import { AppGenerationRequest, ModuleDefinition } from './types';
import * as path from 'path';

dotenv.config();

const app = express();
const PORT = process.env.PORT || 3001;

// Middleware
app.use(helmet());
app.use(cors());
app.use(express.json());

// Initialize generator
const templatePath = path.join(__dirname, '../templates/expo-template');
const outputPath = process.env.APPS_OUTPUT_PATH || path.join(__dirname, '../generated-apps');
const generator = new AppGenerator(templatePath, outputPath);

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// Get available modules
app.get('/modules', (req, res) => {
  const modules: ModuleDefinition[] = [
    {
      id: 'rizz-text-bot',
      name: 'Rizz — Smart Reply',
      description: 'AI-powered text response generator',
      inputs: [
        { name: 'promptText', type: 'string', label: 'Enter your text', required: true }
      ],
      outputs: [
        { name: 'reply', type: 'string' }
      ],
      routes: [
        { screen: 'Home', component: 'RizzComponent' }
      ],
      dependencies: ['openai-client@^1.0.0'],
      api: {
        endpoint: 'https://api.jarvis.local/rizz',
        method: 'POST'
      }
    },
    {
      id: 'image-generator',
      name: 'AI Image Generator',
      description: 'Generate images from text descriptions',
      inputs: [
        { name: 'prompt', type: 'string', label: 'Image description', required: true },
        { name: 'style', type: 'string', label: 'Art style', required: false, defaultValue: 'realistic' }
      ],
      outputs: [
        { name: 'imageUrl', type: 'string' }
      ],
      routes: [
        { screen: 'Home', component: 'ImageGeneratorComponent' }
      ],
      dependencies: ['openai-client@^1.0.0'],
      api: {
        endpoint: 'https://api.jarvis.local/image-generate',
        method: 'POST'
      }
    }
  ];
  
  res.json(modules);
});

// Generate app endpoint
app.post('/generate', async (req, res) => {
  try {
    const request: AppGenerationRequest = req.body;
    
    // Validate required fields
    if (!request.appName || !request.appSlug || !request.module) {
      return res.status(400).json({
        success: false,
        error: 'Missing required fields: appName, appSlug, module'
      });
    }

    // Set defaults
    request.bundleId = request.bundleId || `com.jarvis.${request.appSlug}`;
    request.packageName = request.packageName || `com.jarvis.${request.appSlug}`;
    request.appScheme = request.appScheme || request.appSlug;

    const result = await generator.generateApp(request);
    
    if (result.success) {
      res.json(result);
    } else {
      res.status(500).json(result);
    }
  } catch (error) {
    console.error('Generation error:', error);
    res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

// Get app status
app.get('/apps/:appId/status', async (req, res) => {
  const { appId } = req.params;
  // In a real implementation, this would check build status, etc.
  res.json({
    appId,
    status: 'generated',
    buildStatus: 'pending'
  });
});

app.listen(PORT, () => {
  console.log(`Jarvis Generator Service running on port ${PORT}`);
  console.log(`Template path: ${templatePath}`);
  console.log(`Output path: ${outputPath}`);
});
