python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
Write-Host "`nSetup complete! Run: .venv\Scripts\activate then python run.py"
