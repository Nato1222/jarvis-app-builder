import * as fs from 'fs-extra';
import * as path from 'path';
import { v4 as uuidv4 } from 'uuid';
import Handlebars from 'handlebars';
import { AppGenerationRequest, AppGenerationResponse } from './types';

export class AppGenerator {
  private templatePath: string;
  private outputPath: string;

  constructor(templatePath: string, outputPath: string) {
    this.templatePath = templatePath;
    this.outputPath = outputPath;
  }

  async generateApp(request: AppGenerationRequest): Promise<AppGenerationResponse> {
    try {
      const appId = uuidv4();
      const appDir = path.join(this.outputPath, `app-${appId}`);
      
      // Create app directory
      await fs.ensureDir(appDir);
      
      // Copy template files
      await this.copyTemplateFiles(appDir, request);
      
      // Generate module files
      await this.generateModuleFiles(appDir, request);
      
      // Update package.json with dependencies
      await this.updatePackageJson(appDir, request);
      
      // Update app.json with app details
      await this.updateAppJson(appDir, request);
      
      // Generate README
      await this.generateReadme(appDir, request);
      
      return {
        success: true,
        appId,
        repoUrl: `file://${appDir}`,
      };
    } catch (error) {
      console.error('App generation failed:', error);
      return {
        success: false,
        appId: '',
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }

  private async copyTemplateFiles(appDir: string, request: AppGenerationRequest): Promise<void> {
    const filesToCopy = [
      'package.json',
      'app.json',
      'App.tsx',
      'tsconfig.json',
      'babel.config.js',
    ];

    for (const file of filesToCopy) {
      const srcPath = path.join(this.templatePath, file);
      const destPath = path.join(appDir, file);
      
      if (await fs.pathExists(srcPath)) {
        await fs.copy(srcPath, destPath);
      }
    }

    // Copy src directory structure
    const srcDir = path.join(this.templatePath, 'src');
    const destSrcDir = path.join(appDir, 'src');
    
    if (await fs.pathExists(srcDir)) {
      await fs.copy(srcDir, destSrcDir);
    }
  }

  private async generateModuleFiles(appDir: string, request: AppGenerationRequest): Promise<void> {
    const module = request.module;
    const moduleDir = path.join(appDir, 'src', 'modules', module.id);
    
    await fs.ensureDir(moduleDir);
    
    // Generate module component
    const componentTemplate = await this.loadTemplate('module-component.hbs');
    const componentContent = componentTemplate({
      MODULE_NAME: module.id,
      MODULE_COMPONENT: this.toPascalCase(module.id),
      API_ENDPOINT: module.api.endpoint,
      INPUTS: module.inputs,
      OUTPUTS: module.outputs,
    });
    
    await fs.writeFile(
      path.join(moduleDir, `${this.toPascalCase(module.id)}.tsx`),
      componentContent
    );
    
    // Generate module service
    const serviceTemplate = await this.loadTemplate('module-service.hbs');
    const serviceContent = serviceTemplate({
      MODULE_NAME: module.id,
      API_ENDPOINT: module.api.endpoint,
      API_METHOD: module.api.method,
      INPUTS: module.inputs,
      OUTPUTS: module.outputs,
    });
    
    await fs.writeFile(
      path.join(moduleDir, `${module.id}Service.ts`),
      serviceContent
    );
  }

  private async updatePackageJson(appDir: string, request: AppGenerationRequest): Promise<void> {
    const packageJsonPath = path.join(appDir, 'package.json');
    const packageJson = await fs.readJson(packageJsonPath);
    
    // Update app name and add module dependencies
    packageJson.name = request.appSlug;
    packageJson.dependencies = {
      ...packageJson.dependencies,
      ...this.getDependencyMap(request.module.dependencies),
    };
    
    await fs.writeJson(packageJsonPath, packageJson, { spaces: 2 });
  }

  private async updateAppJson(appDir: string, request: AppGenerationRequest): Promise<void> {
    const appJsonPath = path.join(appDir, 'app.json');
    const appJson = await fs.readJson(appJsonPath);
    
    // Update app details
    appJson.expo.name = request.appName;
    appJson.expo.slug = request.appSlug;
    appJson.expo.ios.bundleIdentifier = request.bundleId;
    appJson.expo.android.package = request.packageName;
    appJson.expo.scheme = request.appScheme;
    
    await fs.writeJson(appJsonPath, appJson, { spaces: 2 });
  }

  private async generateReadme(appDir: string, request: AppGenerationRequest): Promise<void> {
    const readmeTemplate = await this.loadTemplate('readme.hbs');
    const readmeContent = readmeTemplate({
      APP_NAME: request.appName,
      APP_DESCRIPTION: request.description || `A ${request.module.name} app`,
      MODULE_NAME: request.module.name,
      MODULE_DESCRIPTION: request.module.description,
    });
    
    await fs.writeFile(path.join(appDir, 'README.md'), readmeContent);
  }

  private async loadTemplate(templateName: string): Promise<HandlebarsTemplateDelegate> {
    const templatePath = path.join(__dirname, 'templates', templateName);
    const templateContent = await fs.readFile(templatePath, 'utf-8');
    return Handlebars.compile(templateContent);
  }

  private getDependencyMap(dependencies: string[]): Record<string, string> {
    const depMap: Record<string, string> = {};
    dependencies.forEach(dep => {
      const [name, version] = dep.split('@');
      depMap[name] = version || 'latest';
    });
    return depMap;
  }

  private toPascalCase(str: string): string {
    return str
      .split('-')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join('');
  }
}
