<#
    Build the Test Assist desktop app into a pinnable Windows executable.

        .\build.ps1              build into dist\TestAssist\
        .\build.ps1 -Zip         also produce dist\TestAssist-<version>-win64.zip
        .\build.ps1 -Shortcut    also drop a shortcut on your Desktop

    The release workflow runs the same PyInstaller spec on a clean Windows
    runner, so a local build and a released build come out the same way.
#>
[CmdletBinding()]
param(
    [switch]$Zip,
    [switch]$Shortcut
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here

# Use the repo venv when there is one, so the build matches what you run.
$venv = Join-Path (Split-Path -Parent $here) ".venv"
$python = if (Test-Path (Join-Path $venv "Scripts\python.exe")) {
    Join-Path $venv "Scripts\python.exe"
} else {
    "python"
}
Write-Host "Using $python" -ForegroundColor DarkGray

& $python -c "import PyInstaller" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing PyInstaller..." -ForegroundColor Cyan
    & $python -m pip install --quiet pyinstaller
}

Write-Host "Building..." -ForegroundColor Cyan
& $python -m PyInstaller --noconfirm --clean TestAssist.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

$exe = Join-Path $here "dist\TestAssist\TestAssist.exe"
if (-not (Test-Path $exe)) { throw "Expected $exe to exist" }

# Prove the thing actually runs before calling it a build. The app is windowed,
# so it has no usable stdout - it writes its version to this file instead.
$probe = Join-Path $here "version-probe.txt"
if (Test-Path $probe) { Remove-Item $probe }
$env:TESTASSIST_VERSION_FILE = $probe

$proc = Start-Process -FilePath $exe -ArgumentList '--version' -Wait -PassThru
if ($proc.ExitCode -ne 0) { throw "The built executable exited with $($proc.ExitCode)" }
if (-not (Test-Path $probe)) { throw "The executable ran but produced no version file" }

$reported = (Get-Content $probe -Raw).Trim()
Remove-Item $probe
Write-Host "Built and verified: $reported" -ForegroundColor Green

$version = ($reported -replace '[^0-9\.]', '').Trim()
if (-not $version) { $version = "0.0.0" }

if ($Zip) {
    $zip = Join-Path $here "dist\TestAssist-$version-win64.zip"
    if (Test-Path $zip) { Remove-Item $zip }
    Compress-Archive -Path (Join-Path $here "dist\TestAssist\*") -DestinationPath $zip
    Write-Host "Packaged: $zip" -ForegroundColor Green
}

if ($Shortcut) {
    $lnk = Join-Path ([Environment]::GetFolderPath("Desktop")) "Test Assist.lnk"
    $shell = New-Object -ComObject WScript.Shell
    $s = $shell.CreateShortcut($lnk)
    $s.TargetPath = $exe
    $s.WorkingDirectory = Split-Path -Parent $exe
    $s.IconLocation = $exe
    $s.Description = "Test Assist - QA evidence capture and annotation"
    $s.Save()
    Write-Host "Shortcut created: $lnk" -ForegroundColor Green
    Write-Host "Right-click it -> Pin to taskbar." -ForegroundColor DarkGray
}
