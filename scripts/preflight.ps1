# TA-204 preflight - run before the multi-display pass, and again after each
# display-settings change. Read-only: checks and reports, changes nothing.
#
#   powershell -ExecutionPolicy Bypass -File scripts\preflight.ps1
#
# ASCII only, deliberately. Windows PowerShell 5.1 reads .ps1 as ANSI unless
# the file has a UTF-8 BOM, and a UTF-8 em-dash then decodes to a CP1252 smart
# quote, which PowerShell treats as a string delimiter - it breaks the parse.

$ErrorActionPreference = 'Continue'
Add-Type -AssemblyName System.Windows.Forms

$expectedVersion = '1.4.0'
$buildPath       = 'C:\TestAssist-1.4.0\TestAssist.exe'
$script:fail     = $false

function Ok   { param($m) Write-Host "  PASS  $m" -ForegroundColor Green }
function Bad  { param($m) Write-Host "  FAIL  $m" -ForegroundColor Red; $script:fail = $true }
function Note { param($m) Write-Host "  ..    $m" -ForegroundColor DarkGray }

Write-Host ""
Write-Host "TA-204 preflight" -ForegroundColor Cyan
Write-Host ("=" * 64)

# ---- S-1: nothing already running -----------------------------------------
Write-Host ""
Write-Host "S-1  No Test Assist already running"
$procs = @(Get-Process -Name 'TestAssist' -ErrorAction SilentlyContinue)
if ($procs.Count -gt 0) {
    Bad ("{0} TestAssist process(es) still running:" -f $procs.Count)
    foreach ($p in $procs) {
        Note ("PID {0}  started {1}" -f $p.Id, $p.StartTime)
    }
    Note "Close it from the tray, or: Stop-Process -Name TestAssist"
    Note "A stray instance hands your launch off to itself, so you test the"
    Note "wrong build, and it holds the Win32 hotkeys, which fails LCH-13"
    Note "for reasons that have nothing to do with the build. See TA-230."
}
else {
    Ok "no TestAssist process running"
}

# ---- S-2: the right build --------------------------------------------------
Write-Host ""
Write-Host "S-2  Testing the released v$expectedVersion build"
if (Test-Path $buildPath) {
    $vi      = (Get-Item $buildPath).VersionInfo
    $prodVer = [string]$vi.ProductVersion
    $fileVer = [string]$vi.FileVersion
    if (($prodVer + $fileVer) -like "*$expectedVersion*") {
        Ok ("{0} reports {1}" -f $buildPath, $prodVer)
    }
    else {
        Bad ("{0} reports '{1}' - expected {2}" -f $buildPath, $prodVer, $expectedVersion)
        Note "This is the failure the pass doc warns about: testing an old build"
        Note "while believing otherwise. Tell builds apart by folder, not title."
    }
}
else {
    Bad "not found: $buildPath"
    Note "Download TestAssist-1.4.0-win64.zip from the Releases page and unzip"
    Note "it there. rc4 and rc5 predate the HiDPI capture fixes and must not"
    Note "be used for this pass."
}

$others = @(Get-ChildItem 'C:\' -Directory -Filter 'TestAssist*' -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -ne 'C:\TestAssist-1.4.0' })
if ($others.Count -gt 0) {
    Note "other builds present (fine, as long as you launch the right one):"
    foreach ($o in $others) { Note ("  " + $o.FullName) }
}

# ---- Display layout --------------------------------------------------------
Write-Host ""
Write-Host "--   Display layout (record this in SMOKE_TEST.md)"
$screens = @([System.Windows.Forms.Screen]::AllScreens)
Write-Host ("      {0} screen(s) detected" -f $screens.Count)
for ($i = 0; $i -lt $screens.Count; $i++) {
    $s = $screens[$i]
    $b = $s.Bounds
    if ($s.Primary) { $tag = 'PRIMARY' } else { $tag = 'secondary' }
    Write-Host ("      [{0}] {1,-9} {2}x{3} at ({4},{5})  {6}" -f `
        $i, $tag, $b.Width, $b.Height, $b.X, $b.Y, $s.DeviceName)
}
if ($screens.Count -lt 2) {
    Note "only one screen - Blocks A to D need the external connected."
    Note "(Block E is the single-screen block, so that one is correct here.)"
}

$dpiKey = Get-ItemProperty 'HKCU:\Control Panel\Desktop\WindowMetrics' -Name AppliedDPI -ErrorAction SilentlyContinue
$dpi = $null
if ($dpiKey) {
    $dpi = $dpiKey.AppliedDPI
    $pct = [math]::Round(($dpi / 96) * 100)
    Write-Host ("      AppliedDPI {0}  (about {1}%)" -f $dpi, $pct)
    Note "Current/primary scaling only. Windows does not expose per-monitor"
    Note "scaling here - confirm each screen in Settings > Display."
}

# ---- S-4: data locations ---------------------------------------------------
Write-Host ""
Write-Host "S-4  Data locations"
$docs  = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Test Assist'
$local = Join-Path $env:LOCALAPPDATA 'Test Assist'
foreach ($path in @($docs, $local)) {
    if (Test-Path $path) {
        $count = @(Get-ChildItem $path -File -ErrorAction SilentlyContinue).Count
        Ok ("{0}  ({1} files)" -f $path, $count)
    }
    else {
        Note ("{0} does not exist yet - created on first capture, not an error" -f $path)
    }
}
$legacy = Join-Path $env:USERPROFILE '.test-assist'
if (Test-Path $legacy) {
    Note "legacy .test-assist still present - should migrate on first launch"
}

# ---- verdict ---------------------------------------------------------------
Write-Host ""
Write-Host ("=" * 64)
if ($script:fail) {
    Write-Host "PREFLIGHT FAILED - fix the above before testing." -ForegroundColor Red
    Write-Host "Results from the wrong build or a stale instance are worse than none." -ForegroundColor Red
    Write-Host ""
    exit 1
}

Write-Host "Preflight clear. Safe to start." -ForegroundColor Green
$parts = @()
foreach ($s in $screens) {
    $b = $s.Bounds
    if ($s.Primary) { $role = 'primary' } else { $role = 'secondary' }
    $parts += ("{0} {1}x{2} at ({3},{4})" -f $role, $b.Width, $b.Height, $b.X, $b.Y)
}
Write-Host ""
Write-Host "Paste into your notes:" -ForegroundColor Cyan
Write-Host ("  Hardware: " + ($parts -join ' | '))
if ($dpi) { Write-Host ("  AppliedDPI " + $dpi) }
Write-Host ""
exit 0
