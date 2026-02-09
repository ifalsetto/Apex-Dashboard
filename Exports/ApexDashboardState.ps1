# Export-ApexDashboardState.ps1
# Safe read-only exporter for Streamlit dashboard autofill.
# Outputs a scan bundle folder containing scan.json + copied Apex config files + registry dump (raw).

$ErrorActionPreference = "SilentlyContinue"

function New-Folder([string]$Path) {
  if (-not (Test-Path $Path)) { New-Item -ItemType Directory -Path $Path | Out-Null }
}

function Try-GetRegKey([string]$Path) {
  try {
    if (Test-Path $Path) {
      $props = Get-ItemProperty -Path $Path
      $out = @{}
      foreach ($p in $props.PSObject.Properties) {
        if ($p.Name -notin @("PSPath","PSParentPath","PSChildName","PSDrive","PSProvider")) {
          $out[$p.Name] = $p.Value
        }
      }
      return $out
    }
  } catch {}
  return $null
}

function Copy-IfExists([string]$Src, [string]$DstDir) {
  try {
    if (Test-Path $Src) {
      Copy-Item -Path $Src -Destination $DstDir -Force
      return $true
    }
  } catch {}
  return $false
}

# ---- Base folders (assumes this script sits inside C:\Users\andre\ApexDashboard\) ----
$baseDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$profilesDir = Join-Path $baseDir "Profiles"
$scansDir = Join-Path $profilesDir "Scans"

New-Folder $profilesDir
New-Folder $scansDir

$timestamp = (Get-Date).ToString("yyyyMMdd_HHmmss")
$outDir = Join-Path $scansDir ("SCAN_{0}" -f $timestamp)
New-Folder $outDir

$configDir = Join-Path $outDir "ApexConfigs"
New-Folder $configDir

# ---- System info ----
$os = Get-CimInstance Win32_OperatingSystem
$cs = Get-CimInstance Win32_ComputerSystem
$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
$gpus = Get-CimInstance Win32_VideoController | ForEach-Object {
  [ordered]@{
    Name = $_.Name
    DriverVersion = $_.DriverVersion
    DriverDate = $_.DriverDate
    VideoProcessor = $_.VideoProcessor
    AdapterRAM = $_.AdapterRAM
    CurrentHorizontalResolution = $_.CurrentHorizontalResolution
    CurrentVerticalResolution = $_.CurrentVerticalResolution
    CurrentRefreshRate = $_.CurrentRefreshRate
  }
}

# ---- Apex config file discovery (common paths) ----
$u = $env:USERNAME
$home = $env:USERPROFILE

$apexCandidates = @(
  (Join-Path $home "Saved Games\Respawn\Apex\local\videoconfig.txt"),
  (Join-Path $home "Saved Games\Respawn\Apex\local\settings.cfg"),
  (Join-Path $home "Saved Games\Respawn\Apex\local\profile.cfg"),
  (Join-Path $home "Saved Games\Respawn\Apex\local\config_default_pc.cfg"),
  (Join-Path $home "Saved Games\Respawn\Apex\local\config_default_pc.cfg.pak"),
  (Join-Path $home "Saved Games\Respawn\Apex\local\autoexec.cfg"),
  (Join-Path $home "Saved Games\Respawn\Apex\local\videoconfig.txt.bak")
)

$apexFound = @()
foreach ($p in $apexCandidates) {
  if (Copy-IfExists $p $configDir) { $apexFound += $p }
}

# ---- HDR-related registry dumps (raw; may vary by Windows build) ----
# We dump *multiple likely locations* without claiming semantics.
$regPaths = @(
  "HKCU:\Software\Microsoft\Windows\CurrentVersion\VideoSettings",
  "HKCU:\Software\Microsoft\DirectX",
  "HKCU:\Software\Microsoft\GameBar",
  "HKCU:\Software\Microsoft\Windows\CurrentVersion\GameDVR",
  "HKLM:\SYSTEM\CurrentControlSet\Control\GraphicsDrivers"
)

$regDump = [ordered]@{}
foreach ($rp in $regPaths) {
  $val = Try-GetRegKey $rp
  if ($null -ne $val) { $regDump[$rp] = $val }
}

# ---- Build scan object ----
$scan = [ordered]@{
  scan = [ordered]@{
    createdISO = (Get-Date).ToString("o")
    outputFolder = $outDir
    username = $u
  }
  system = [ordered]@{
    computer = $cs.Name
    manufacturer = $cs.Manufacturer
    model = $cs.Model
    os = [ordered]@{
      caption = $os.Caption
      version = $os.Version
      build = $os.BuildNumber
    }
    cpu = [ordered]@{
      name = $cpu.Name
      cores = $cpu.NumberOfCores
      logicalProcessors = $cpu.NumberOfLogicalProcessors
      maxClockMHz = $cpu.MaxClockSpeed
    }
    gpus = $gpus
    ramGB = [math]::Round($cs.TotalPhysicalMemory / 1GB, 2)
  }
  apex = [ordered]@{
    configFilesCopiedTo = $configDir
    configFilesFound = $apexFound
    note = "These are raw config files copied for inspection/import. No changes were made."
  }
  registry_dump = [ordered]@{
    note = "Raw registry values only. Meanings vary by Windows build; dashboard can interpret later."
    paths = $regDump
  }
}

# ---- Write scan.json ----
$scanPath = Join-Path $outDir "scan.json"
($scan | ConvertTo-Json -Depth 8) | Out-File -FilePath $scanPath -Encoding utf8

Write-Host ""
Write-Host "Scan complete."
Write-Host "Folder: $outDir"
Write-Host "Import this into the dashboard: $scanPath"
Write-Host ""
