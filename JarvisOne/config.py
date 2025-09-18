import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from both root and package .env files
# This ensures keys load whether you run from repo root or inside the package
THIS_DIR = Path(__file__).resolve().parent
PKG_DIR = THIS_DIR
REPO_ROOT = PKG_DIR.parent
# Load .env from the workspace root (e.g., F:\New - JarvisOne\.env)
ROOT_ENV = REPO_ROOT / '.env'
PKG_ENV = PKG_DIR / '.env'
load_dotenv(dotenv_path=str(ROOT_ENV), override=True)
load_dotenv(dotenv_path=str(PKG_ENV), override=True)

# Do NOT hardcode secrets. Expect GROQ_API_KEY to come from environment.
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
# Optional DeepSeek API key for alternate code generation backend
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
# Optional OpenAI key (used only if explicitly selected or as last-resort)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# Board planning provider/model (for Market/CPO/Lead planning)
# PLANNER_PROVIDER: 'auto' | 'groq' | 'deepseek' | 'openai' | 'mock'
PLANNER_PROVIDER = os.environ.get("PLANNER_PROVIDER", "auto").lower().strip()
# If set, overrides per-agent model in prompts for planning phase
PLANNER_MODEL = os.environ.get("PLANNER_MODEL", "").strip()

# Project root (one level up from this file's directory)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

def _compute_default_apps_root():
	# If explicitly configured, honor it
	env_path = os.environ.get("JARVIS_APPS_ROOT")
	if env_path:
		return env_path
	# On Windows, default to F:\Apps per project requirement
	if os.name == "nt":
		return r"F:\\Apps"
	# Else fall back to a folder under the project
	return os.path.join(PROJECT_ROOT, "Apps")

# Root folder where generated apps/workspaces will live
APPS_ROOT = _compute_default_apps_root()

