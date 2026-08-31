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

Write-Host "Generating version_info.txt from __version__..." -ForegroundColor Cyan
& $python generate_version_info.py
if ($LASTEXITCODE -ne 0) { throw "Failed to generate version_info.txt" }

Write-Host "Building..." -ForegroundColor Cyan
& $python -m PyInstaller --noconfirm --clean TestAssist.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

$exe = Join-Path $here "dist\TestAssist\TestAssist.exe"
if (-not (Test-Path $exe)) { throw "Expected $exe to exist" }

# collect_data_files() in the spec is what puts ffmpeg in the bundle - verify
# it actually landed rather than assuming the hook worked, since MP4
# recording silently degrades to a frame sequence if it did not.
$ffmpeg = Get-ChildItem -Path (Join-Path $here "dist\TestAssist") -Recurse -Filter "ffmpeg-win-*.exe" -ErrorAction SilentlyContinue
if (-not $ffmpeg) { throw "ffmpeg binary missing from dist - MP4 recording would silently degrade to a frame sequence" }
Write-Host "ffmpeg bundled: $($ffmpeg.FullName)" -ForegroundColor DarkGray

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

# The ffmpeg-file check above only proves collect_data_files() dropped the
# exe somewhere under dist/. It does not prove the frozen app can actually
# find it: _resolve_ffmpeg_exe() resolves via imageio_ffmpeg.__file__, which
# only points inside the frozen bundle if PyInstaller rewrote it correctly.
# --selftest exercises that real resolution path and reports where it landed.
$selftestProbe = Join-Path $here "selftest-probe.txt"
if (Test-Path $selftestProbe) { Remove-Item $selftestProbe }
$env:TESTASSIST_VERSION_FILE = $selftestProbe

$proc = Start-Process -FilePath $exe -ArgumentList '--selftest' -Wait -PassThru
if ($proc.ExitCode -ne 0) { throw "The built executable exited with $($proc.ExitCode) during --selftest" }
if (-not (Test-Path $selftestProbe)) { throw "The executable ran --selftest but produced no probe file" }

$selftestLines = Get-Content $selftestProbe
$ffmpegPath = $selftestLines[0]
Remove-Item $selftestProbe

if ([string]::IsNullOrWhiteSpace($ffmpegPath)) {
    throw "--selftest could not resolve an ffmpeg binary in the built app"
}

$distRoot = (Resolve-Path (Join-Path $here "dist\TestAssist")).Path
$resolvedFfmpeg = Resolve-Path $ffmpegPath -ErrorAction SilentlyContinue
if (-not $resolvedFfmpeg -or -not $resolvedFfmpeg.Path.StartsWith($distRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "--selftest resolved ffmpeg outside the dist folder: $ffmpegPath"
}
Write-Host "ffmpeg resolves at runtime: $ffmpegPath" -ForegroundColor Green

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
