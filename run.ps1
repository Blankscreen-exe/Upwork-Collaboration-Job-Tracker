$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition

Set-Location $ScriptDir

& "$ScriptDir\venv\Scripts\Activate.ps1"
python main.py