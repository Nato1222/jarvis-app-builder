# JarvisOne Backend

This document provides instructions for setting up and running the JarvisOne backend.

## Setup

1.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    ```
    On Windows:
    ```powershell
    .\venv\Scripts\Activate.ps1
    ```
    On macOS/Linux:
    ```bash
    source venv/bin/activate
    ```

2.  **Install dependencies:**
    ```powershell
    # Windows PowerShell
    .\venv\Scripts\Activate.ps1
    python -m pip install -U pip
    pip install -r requirements.txt
    ```

3.  **Set up environment variables:**
    Copy `.env.example` to `.env` and fill in the required values (set `SECRET_KEY`; optional `GROQ_API_KEY` for code generation; optional `DEEPSEEK_API_KEY` for the DeepSeek backend). For Board planning you can control the provider/model:
    - `PLANNER_PROVIDER=auto|groq|deepseek|openai` (default `auto` prefers free-tier Groq, then DeepSeek, then OpenAI)
    - `PLANNER_MODEL=<modelName>` (optional override, e.g., `deepseek-coder-v2`)
    - `OPENAI_API_KEY` (optional; only used if `PLANNER_PROVIDER=openai` or auto selects it)
    - `JARVIS_APPS_ROOT` (optional; Windows default is `F:\Apps`)
    ```powershell
    Copy-Item .env.example .env
    notepad .env  # add GROQ_API_KEY=...
    ```

## Database

To create the SQLite database and tables, run the following command:
```powershell
python JarvisOne/database/create_tables.py
```
This will create a `jarvisone.db` file in the project directory.

## Running the Server

To run the FastAPI development server:
```powershell
uvicorn JarvisOne.main:app --reload --port 8001
```
The server will be available at `http://localhost:8001`.

## Testing the Backend

Once the server is running, you can test the basic flow:

1.  (Optional) **Test code generator (Groq):**
    ```powershell
    $env:GROQ_API_KEY = '<your_groq_key>'
    python JarvisOne/scripts/test_codegen.py
    ```

    (Optional) Test DeepSeek code generator:
    ```powershell
    $env:DEEPSEEK_API_KEY = '<your_deepseek_key>'
    python JarvisOne/scripts/test_codegen_deepseek.py
    ```

2.  **Run the Board locally (planner discussion):**
    ```powershell
    python JarvisOne/scripts/terminal_board.py
    ```
    The console will label which provider handled each Board turn (e.g., `[Groq Board:llama-3.1-8b-instant]`).

3.  **Fetch the board feed from the API:**
    ```powershell
    curl http://localhost:8001/board/feed
    ```
    Executor logs also label codegen/edit backends, e.g., `[DeepSeek CodeGen:deepseek-coder]`, `[Groq Edit:llama-3.1-8b-instant]`, and print the plan summary as the strategy title.
