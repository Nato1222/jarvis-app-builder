export interface ModuleInput {
  name: string;
  type: string;
  label: string;
  required?: boolean;
  defaultValue?: any;
}

export interface ModuleOutput {
  name: string;
  type: string;
}

export interface ModuleRoute {
  screen: string;
  component: string;
}

export interface ModuleAPI {
  endpoint: string;
  method: string;
  headers?: Record<string, string>;
}

export interface ModuleDefinition {
  id: string;
  name: string;
  description?: string;
  inputs: ModuleInput[];
  outputs: ModuleOutput[];
  routes: ModuleRoute[];
  dependencies: string[];
  api: ModuleAPI;
}

export interface AppGenerationRequest {
  appName: string;
  appSlug: string;
  bundleId: string;
  packageName: string;
  appScheme: string;
  module: ModuleDefinition;
  iconUrl?: string;
  description?: string;
}

export interface AppGenerationResponse {
  success: boolean;
  appId: string;
  repoUrl?: string;
  buildUrl?: string;
  error?: string;
}
