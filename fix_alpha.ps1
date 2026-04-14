Write-Host "Repairing Alpha Omega..." -ForegroundColor Cyan
& .\.venv\Scripts\Activate.ps1
python -m pip install pipwin
& .\.venv\Scripts\pipwin install pyaudio
python -m pip install vosk speech_recognition pyttsx3 pyyaml psutil numpy opencv-python
if (-not (Test-Path "model-small")) {
    Write-Host "Downloading AI models..."
    Invoke-WebRequest -Uri "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip" -OutFile "model.zip"
    Expand-Archive -Path "model.zip" -DestinationPath "." -Force
    Get-ChildItem -Filter "vosk-model-small-en-us-*" | Rename-Item -NewName "model-small"
    Remove-Item "model.zip"
}
Write-Host "System Repaired!" -ForegroundColor Green