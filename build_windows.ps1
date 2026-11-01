# AtsFlow - Windows paketleme betigi
# Kullanim: powershell -ExecutionPolicy Bypass -File build_windows.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

python -m pip install --quiet pyinstaller

python -m PyInstaller --noconfirm --clean `
  --onefile --noconsole `
  --name AtsFlow `
  --icon "assets\icon.ico" `
  --add-data "web;web" `
  --add-data "assets;assets" `
  --collect-binaries imageio_ffmpeg `
  main.py

Write-Host ""
Write-Host "Tamamlandi: dist\AtsFlow.exe"

# Microsoft Store (MSIX) icin:
# 1) Windows SDK kurulu olmali (MakeAppx + signtool)
# 2) packaging\AppxManifest.xml dosyasini dist icine kopyalayin
# 3) MakeAppx pack /d dist /p AtsFlow.msix
# 4) Kendi sertifikanizla imzalayin:
#    signtool sign /fd SHA256 /a /f mycert.pfx /p <sifre> AtsFlow.msix
# 5) Partner Center'a yukleyin (https://partner.microsoft.com)
