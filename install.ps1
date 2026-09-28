# install.ps1
# PowerShell script to set up the AlgortimTrading-robot project on Windows

Write-Host "Setting up virtual environment..."
python -m venv env

Write-Host "Activating virtual environment..."
& "./env/Scripts/Activate.ps1"

Write-Host "Installing required packages..."
pip install -r requirements.txt

Write-Host "Copying .env example to .env..."
Copy-Item .env.example -Destination .env -Force

Write-Host "Please edit .env with your Alpaca, Moomoo and Telegram credentials before running the bot."
Write-Host "You can now start the bot with: python bot.py"
