# Jarvis App Builder - Setup Guide

This guide will help you set up the complete Jarvis App Builder system on your local machine.

## Prerequisites

### Required Software
- **Node.js 18+** - [Download here](https://nodejs.org/)
- **Python 3.8+** - [Download here](https://python.org/)
- **Git** - [Download here](https://git-scm.com/)
- **Expo CLI** - `npm install -g @expo/cli`
- **EAS CLI** - `npm install -g eas-cli`

### Optional (for mobile development)
- **Android Studio** - For Android development
- **Xcode** - For iOS development (macOS only)

## Quick Setup (Windows)

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd jarvis-app-builder
   ```

2. **Run the startup script**
   ```bash
   start-jarvis.bat
   ```

3. **Open the dashboard**
   - Go to http://localhost:3000
   - Start creating apps!

## Manual Setup

### 1. Backend API (JarvisOne)

```bash
cd JarvisOne
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

### 2. Generator Service

```bash
cd generator
npm install
npm run build
npm run dev
```

### 3. Dashboard

```bash
cd dashboard
npm install
npm run dev
```

## Environment Configuration

Create a `.env` file in the root directory:

```env
# Generator Service
GENERATOR_PORT=3001
APPS_OUTPUT_PATH=./generated-apps

# Dashboard
DASHBOARD_PORT=3000
GENERATOR_URL=http://localhost:3001

# Backend API
BACKEND_PORT=8000

# Expo/EAS (for production builds)
EXPO_TOKEN=your_expo_token_here
APPLE_ID=your_apple_id
ASC_APP_ID=your_asc_app_id
APPLE_TEAM_ID=your_apple_team_id
```

## Testing the Setup

Run the integration test:

```bash
node test-integration.js
```

This will verify that all services are running and can communicate with each other.

## Creating Your First App

1. **Open the Dashboard**
   - Go to http://localhost:3000

2. **Choose a Module**
   - Select from available modules (Rizz Text Bot, Image Generator, etc.)

3. **Fill App Details**
   - App Name: "My Awesome App"
   - App Slug: "my-awesome-app"
   - Description: "A cool app that does X"

4. **Generate App**
   - Click "Generate App"
   - Wait for generation to complete

5. **Download and Test**
   - Click "Download" to get the app folder
   - Navigate to the app folder
   - Run `npm install` and `npm start`

## Adding New Modules

1. **Create Module Directory**
   ```bash
   mkdir modules/my-new-module
   ```

2. **Add Module Definition**
   Create `modules/my-new-module/module.json`:
   ```json
   {
     "id": "my-new-module",
     "name": "My New Module",
     "description": "What this module does",
     "inputs": [...],
     "outputs": [...],
     "api": {...}
   }
   ```

3. **Update Generator**
   Add the module to the generator's module list

4. **Test**
   Restart the generator service and test via dashboard

## Troubleshooting

### Common Issues

**"Cannot connect to generator service"**
- Make sure the generator service is running on port 3001
- Check if the port is already in use

**"Module not found" errors**
- Run `npm install` in the generator directory
- Check if the module.json file is valid

**"App generation failed"**
- Check the generator service logs
- Verify the template files exist
- Ensure output directory is writable

### Logs

- **Generator Service**: Check console output in the generator terminal
- **Dashboard**: Check browser console and network tab
- **Backend API**: Check the uvicorn output

### Reset Everything

```bash
# Stop all services (Ctrl+C in each terminal)
# Clear generated apps
rm -rf generated-apps/*
# Reinstall dependencies
cd generator && npm install
cd ../dashboard && npm install
cd ../JarvisOne && pip install -r requirements.txt
```

## Production Deployment

### 1. Environment Setup
- Set up proper environment variables
- Configure Expo/EAS credentials
- Set up GitHub Actions secrets

### 2. Build Process
- Apps are automatically built via GitHub Actions
- EAS handles the build and submission process
- Monitor builds in the Expo dashboard

### 3. App Store Submission
- Configure Apple Developer account
- Set up Google Play Console
- Add required secrets to GitHub

## Support

If you encounter issues:
1. Check the logs for error messages
2. Verify all services are running
3. Test individual components
4. Check the GitHub Issues page

---

**Happy building! 🚀**
