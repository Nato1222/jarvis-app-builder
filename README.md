# Jarvis App Builder

> A system that generates mobile apps (Android + iOS) with single features automatically, using AI-powered modules and automated CI/CD pipelines.

## 🎯 What We're Building

Jarvis App Builder is a system where users can:
1. **Choose a feature module** (AI text generation, image creation, weather checking, etc.)
2. **Configure app details** (name, icon, description)
3. **Generate a complete mobile app** (React Native + Expo)
4. **Automatically build and deploy** to TestFlight/Play Store

Each app focuses on **one core feature** and is production-ready.

## 🏗️ Architecture

```
jarvis-root/
├── generator/           # Node.js/TypeScript generator service
├── templates/          # Expo app templates
│   └── expo-template/  # Base React Native template
├── modules/            # Feature module registry
│   ├── rizz-text-bot/  # AI text generation
│   ├── image-generator/# AI image creation
│   └── weather-checker/# Weather API integration
├── dashboard/          # Web UI for app generation
├── ci/                 # GitHub Actions + EAS workflows
└── docs/              # Documentation
```

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Install Node.js 18+
# Install Expo CLI
npm install -g @expo/cli eas-cli

# Clone and setup
git clone <repo-url>
cd jarvis-app-builder
```

### 2. Start Generator Service

```bash
cd generator
npm install
npm run dev
# Runs on http://localhost:3001
```

### 3. Start Dashboard

```bash
cd dashboard
npm install
npm run dev
# Runs on http://localhost:3000
```

### 4. Generate Your First App

1. Open http://localhost:3000
2. Choose a module (e.g., "Rizz — Smart Reply")
3. Fill in app details
4. Click "Generate App"
5. Download the generated app folder

## 📱 Module System

Each module defines:
- **Inputs**: What data the user provides
- **Outputs**: What the module returns
- **API**: Backend endpoint for processing
- **UI**: React Native component template

Example module definition:
```json
{
  "id": "rizz-text-bot",
  "name": "Rizz — Smart Reply",
  "inputs": [
    {"name": "promptText", "type": "string", "label": "Enter your text"}
  ],
  "outputs": [
    {"name": "reply", "type": "string"}
  ],
  "api": {
    "endpoint": "https://api.jarvis.local/rizz",
    "method": "POST"
  }
}
```

## 🔧 Development

### Adding New Modules

1. Create module folder in `modules/`
2. Add `module.json` with module definition
3. Update generator to include new module
4. Test with dashboard

### Customizing Templates

Edit files in `templates/expo-template/`:
- `App.tsx` - Main app component
- `src/modules/{{MODULE_NAME}}/` - Module-specific code
- `package.json` - Dependencies
- `app.json` - Expo configuration

## 🚀 Deployment

### CI/CD Pipeline

1. **GitHub Actions** triggers on push to `apps/*` branches
2. **EAS Build** creates production builds
3. **EAS Submit** publishes to stores

### Required Secrets

Add to GitHub Secrets:
- `EXPO_TOKEN` - Expo authentication
- `APPLE_ID` - Apple Developer account
- `ASC_APP_ID` - App Store Connect app ID
- `APPLE_TEAM_ID` - Apple Developer team ID
- `GOOGLE_SERVICE_ACCOUNT_KEY` - Google Play service account

## 📋 Current Modules

- **Rizz Text Bot** 💬 - AI-powered text responses
- **Image Generator** 🎨 - AI image creation from text
- **Weather Checker** 🌤️ - Current weather information

## 🎯 Roadmap

- [ ] More AI modules (translation, summarization)
- [ ] Database modules (notes, todos, contacts)
- [ ] Social modules (sharing, comments)
- [ ] Payment integration modules
- [ ] Custom module marketplace

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Add your module or improvement
4. Submit pull request

## 📄 License

MIT License - see LICENSE file for details

---

**Built with ❤️ by the Jarvis team**
