# setup_app.ps1
# PowerShell script to set up AlgortimTrading‑robot as a ready‑to‑run application
# ---------------------------------------------------------------
# 1. Create virtual environment
# 2. Install Python dependencies
# 3. Copy .env.example → .env (user must edit afterwards)
# 4. Create a convenient batch file to launch the bot
# 5. (Optional) Create a Docker image for containerised execution
# ---------------------------------------------------------------

Write-Host "=== Setting up AlgortimTrading‑robot ==="

# Ensure we are in the script's directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# 1. Virtual environment
Write-Host "Creating virtual environment..."
python -m venv env
if ($LASTEXITCODE -ne 0) { Write-Error "Failed to create virtual environment"; exit 1 }

# 2. Activate and install dependencies
Write-Host "Activating virtual environment and installing requirements..."
& "${ScriptDir}\env\Scripts\Activate.ps1"
if ($LASTEXITCODE -ne 0) { Write-Error "Failed to activate virtual environment"; exit 1 }

pip install --upgrade pip
pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { Write-Error "Failed to install dependencies"; exit 1 }

# 3. Copy .env example
Write-Host "Copying .env.example to .env"
Copy-Item -Path ".env.example" -Destination ".env" -Force

Write-Host "---------------------------------------------------"
Write-Host "Setup complete!"
Write-Host "Edit the .env file with your Alpaca, Moomoo and Telegram credentials."
Write-Host "Then you can start the bot with one of the following options:"
Write-Host "  * Run the batch file:   .\\run_bot.bat"
Write-Host "  * Run via PowerShell:  python bot.py"
Write-Host "  * Run inside Docker (see Dockerfile)."
Write-Host "---------------------------------------------------"
