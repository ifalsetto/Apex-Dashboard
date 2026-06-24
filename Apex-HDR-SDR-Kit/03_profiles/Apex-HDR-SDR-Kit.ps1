<#
Apex-HDR-SDR-Kit.ps1

Read-only by default.
Generates:
- System snapshot (JSON)
- Strict Gemini prompt (MD) + expected output schema (JSON)
- Apex Dashboard-compatible HDR/SDR profile templates (JSON)
- Offline interactive HTML dashboard to review Gemini output

USAGE
  # 1) Generate snapshot + prompt + templates
  powershell -NoProfile -ExecutionPolicy Bypass -File .\Apex-HDR-SDR-Kit.ps1 -Mode Generate -Workspace "$env:USERPROFILE\Documents\Apex-HDR-SDR-Kit" -Open

  # 2) Validate Gemini output (folder containing HDR_PROFILE.json / SDR_PROFILE.json / SETTINGS_CATALOG.json)
  powershell -NoProfile -ExecutionPolicy Bypass -File .\Apex-HDR-SDR-Kit.ps1 -Mode Validate -Workspace "$env:USERPROFILE\Documents\Apex-HDR-SDR-Kit" -GeminiOutputDir "$env:USERPROFILE\Documents\Apex-HDR-SDR-Kit\05_gemini_output"

  # 3) Import validated profiles into your Apex Dashboard folder
  powershell -NoProfile -ExecutionPolicy Bypass -File .\Apex-HDR-SDR-Kit.ps1 -Mode Import -Workspace "$env:USERPROFILE\Documents\Apex-HDR-SDR-Kit" -GeminiOutputDir "$env:USERPROFILE\Documents\Apex-HDR-SDR-Kit\05_gemini_output" -ApexDashboardPath "C:\Path\To\Apex-Dashboard-0.1.0-beta"

PARAMETERS
  -Mode             Generate | Validate | Import
  -Workspace        Where to write outputs
  -InputDir         Optional folder of existing files (DxDiag.txt, NVIDIA System Information*.txt, FALSEGAMINGDESK.txt, servicesForApexOpt.txt)
  -GeminiOutputDir  Folder with Gemini-produced JSON files
  -ApexDashboardPath Path to your Apex Dashboard folder (contains apex_dashboard.py)
  -NoDxDiag         Skip dxdiag collection
  -NoNvidiaSmi      Skip nvidia-smi collection
  -Open             Open the workspace folder when done

NOTES
  This script does NOT change system settings.
  It is intentionally "safe" (collect + generate + validate + import only).
#>

[CmdletBinding()]
param(
  [ValidateSet('Generate','Validate','Import')]
  [string]$Mode = 'Generate',

  [string]$Workspace = (Join-Path $env:USERPROFILE 'Documents\Apex-HDR-SDR-Kit'),

  [string]$InputDir = '',

  [string]$GeminiOutputDir = '',

  [string]$ApexDashboardPath = '',

  [switch]$NoDxDiag,
  [switch]$NoNvidiaSmi,
  [switch]$Open
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ----------------------------
# Logging
# ----------------------------
function Write-Log {
  param(
    [ValidateSet('INFO','WARN','ERROR','OK')][string]$Level,
    [string]$Message
  )

  $ts = (Get-Date).ToString('HH:mm:ss')
  switch ($Level) {
    'INFO'  { Write-Host "[$ts] [INFO ] $Message" -ForegroundColor Cyan }
    'WARN'  { Write-Host "[$ts] [WARN ] $Message" -ForegroundColor Yellow }
    'ERROR' { Write-Host "[$ts] [ERROR] $Message" -ForegroundColor Red }
    'OK'    { Write-Host "[$ts] [OK   ] $Message" -ForegroundColor Green }
  }
}

function New-Dir {
  param([Parameter(Mandatory=$true)][string]$Path)
  if (-not (Test-Path -LiteralPath $Path)) {
    New-Item -ItemType Directory -Path $Path -Force | Out-Null
  }
}

function Resolve-FullPath {
  param([string]$Path)
  if (-not $Path) { return '' }
  try { return (Resolve-Path -LiteralPath $Path).Path } catch { return $Path }
}

function Get-TextFileRobust {
  param([Parameter(Mandatory=$true)][string]$Path)

  if (-not (Test-Path -LiteralPath $Path)) {
    throw "File not found: $Path"
  }

  $encodings = @('utf8','unicode','default')
  foreach ($enc in $encodings) {
    try {
      return Get-Content -LiteralPath $Path -Raw -Encoding $enc
    } catch {
      # keep trying
    }
  }

  # last resort
  return Get-Content -LiteralPath $Path -Raw
}

function Save-Json {
  param(
    [Parameter(Mandatory=$true)][string]$Path,
    [Parameter(Mandatory=$true)]$Object,
    [int]$Depth = 12
  )

  $json = $Object | ConvertTo-Json -Depth $Depth
  $tmp = "$Path.tmp"
  $json | Out-File -LiteralPath $tmp -Encoding utf8
  Move-Item -LiteralPath $tmp -Destination $Path -Force
}

function Copy-IfExists {
  param(
    [Parameter(Mandatory=$true)][string]$Src,
    [Parameter(Mandatory=$true)][string]$Dst
  )
  if (Test-Path -LiteralPath $Src) {
    Copy-Item -LiteralPath $Src -Destination $Dst -Force
    return $true
  }
  return $false
}

# ----------------------------
# External command helpers
# ----------------------------
function Invoke-ExternalToFile {
  param(
    [Parameter(Mandatory=$true)][string]$Exe,
    [Parameter()][string[]]$Args = @(),
    [Parameter(Mandatory=$true)][string]$OutFile
  )

  $exePath = $Exe
  if (-not (Test-Path -LiteralPath $exePath)) {
    $cmd = Get-Command $Exe -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source) { $exePath = $cmd.Source }
  }
  if (-not (Test-Path -LiteralPath $exePath)) {
    throw "Executable not found: $Exe"
  }

  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName = $exePath
  $psi.Arguments = ($Args -join ' ')
  $psi.RedirectStandardOutput = $true
  $psi.RedirectStandardError = $true
  $psi.UseShellExecute = $false
  $psi.CreateNoWindow = $true

  $p = New-Object System.Diagnostics.Process
  $p.StartInfo = $psi
  [void]$p.Start()

  $stdout = $p.StandardOutput.ReadToEnd()
  $stderr = $p.StandardError.ReadToEnd()
  $p.WaitForExit()

  $combined = $stdout
  if ($stderr) { $combined += "`r`n--- STDERR ---`r`n$stderr" }

  $combined | Out-File -LiteralPath $OutFile -Encoding utf8
}

function Find-NvidiaSmi {
  $candidates = @(
    (Join-Path $env:ProgramFiles 'NVIDIA Corporation\NVSMI\nvidia-smi.exe'),
    (Join-Path ${env:ProgramFiles(x86)} 'NVIDIA Corporation\NVSMI\nvidia-smi.exe'),
    'nvidia-smi.exe'
  )

  foreach ($c in $candidates) {
    $resolved = $c
    if ($c -eq 'nvidia-smi.exe') {
      $cmd = Get-Command $c -ErrorAction SilentlyContinue
      if ($cmd -and $cmd.Source) { $resolved = $cmd.Source }
    }

    if ($resolved -and (Test-Path -LiteralPath $resolved)) { return $resolved }
  }

  return ''
}

# ----------------------------
# Parse helpers
# ----------------------------
function Parse-DxDiagDisplays {
  param([Parameter(Mandatory=$true)][string]$DxDiagPath)

  $text = Get-TextFileRobust -Path $DxDiagPath
  $lines = $text -split "`r?`n"

  $inDisplaySection = $false
  $devices = @()
  $cur = $null

  foreach ($line in $lines) {
    if ($line -match '^\s*Display Devices\s*$') {
      $inDisplaySection = $true
      continue
    }
    if ($inDisplaySection -and ($line -match '^\s*Sound Devices\s*$')) {
      break
    }
    if (-not $inDisplaySection) { continue }

    if ($line -match '^\s*Card name:\s*(.+)$') {
      if ($cur) { $devices += [pscustomobject]$cur }
      $cur = [ordered]@{
        cardName = $matches[1].Trim()
      }
      continue
    }
    if (-not $cur) { continue }

    if ($line -match '^\s*Driver Version:\s*(.+)$') { $cur.driverVersion = $matches[1].Trim(); continue }
    if ($line -match '^\s*Driver Model:\s*(.+)$') { $cur.driverModel = $matches[1].Trim(); continue }
    if ($line -match '^\s*Current Mode:\s*(\d+)\s*x\s*(\d+).+\((\d+)Hz\)') {
      $cur.currentWidth  = [int]$matches[1]
      $cur.currentHeight = [int]$matches[2]
      $cur.refreshHz     = [int]$matches[3]
      continue
    }
    if ($line -match '^\s*Monitor Name:\s*(.+)$') { $cur.monitorName = $matches[1].Trim(); continue }
    if ($line -match '^\s*HDR Support:\s*(.+)$') { $cur.hdrSupport = $matches[1].Trim(); continue }
    if ($line -match '^\s*Monitor Capabilities:\s*(.+)$') { $cur.monitorCapabilities = $matches[1].Trim(); continue }
    if ($line -match '^\s*Advanced Color:\s*(.+)$') { $cur.advancedColor = $matches[1].Trim(); continue }
    if ($line -match '^\s*Active Color Mode:\s*(.+)$') { $cur.activeColorMode = $matches[1].Trim(); continue }
    if ($line -match '^\s*Display Topology:\s*(.+)$') { $cur.topology = $matches[1].Trim(); continue }
  }

  if ($cur) { $devices += [pscustomobject]$cur }

  # add a computed flag
  $devices | ForEach-Object {
    $_ | Add-Member -NotePropertyName hdrSupported -NotePropertyValue ($_.hdrSupport -match 'Supported') -Force
    $_
  }
}

function Parse-NvidiaSystemInfo {
  param([Parameter(Mandatory=$true)][string]$Path)

  $text = Get-TextFileRobust -Path $Path
  $obj = [ordered]@{}

  foreach ($line in ($text -split "`r?`n")) {
    if ($line -match '^\s*GPU processor:\s*(.+)$') { $obj.gpu = $matches[1].Trim(); continue }
    if ($line -match '^\s*Driver version:\s*(.+)$') { $obj.driverVersion = $matches[1].Trim(); continue }
    if ($line -match '^\s*Driver Type:\s*(.+)$') { $obj.driverType = $matches[1].Trim(); continue }
    if ($line -match '^\s*Resizable BAR\s*(Yes|No)') { $obj.resizableBar = $matches[1]; continue }
    if ($line -match '^\s*DirectX version:\s*(.+)$') { $obj.directX = $matches[1].Trim(); continue }
    if ($line -match '^\s*Dedicated video memory:\s*(.+)$') { $obj.vram = $matches[1].Trim(); continue }
    if ($line -match '^\s*Memory data rate:\s*(.+)$') { $obj.memoryDataRate = $matches[1].Trim(); continue }
    if ($line -match '^\s*Memory bandwidth:\s*(.+)$') { $obj.memoryBandwidth = $matches[1].Trim(); continue }
    if ($line -match '^\s*Bus:\s*(.+)$') { $obj.bus = $matches[1].Trim(); continue }
  }

  return [pscustomobject]$obj
}

function Get-WmiMonitors {
  $list = @()
  try {
    $raw = Get-CimInstance -Namespace root\wmi -ClassName WmiMonitorID -ErrorAction Stop
    foreach ($m in $raw) {
      $name = ($m.UserFriendlyName | Where-Object { $_ -ne 0 } | ForEach-Object { [char]$_ }) -join ''
      $manu = ($m.ManufacturerName | Where-Object { $_ -ne 0 } | ForEach-Object { [char]$_ }) -join ''
      $serial = ($m.SerialNumberID | Where-Object { $_ -ne 0 } | ForEach-Object { [char]$_ }) -join ''
      $list += [pscustomobject]@{
        instanceName = $m.InstanceName
        manufacturer = $manu
        friendlyName = $name
        serial = $serial
        weekOfManufacture = $m.WeekOfManufacture
        yearOfManufacture = $m.YearOfManufacture
      }
    }
  } catch {
    # ignore
  }
  return $list
}

function Parse-NvidiaSmiSummary {
  param([Parameter(Mandatory=$true)][string]$Path)

  $text = Get-TextFileRobust -Path $Path
  $lines = $text -split "`r?`n"
  $out = [ordered]@{}

  foreach ($l in $lines) {
    if (-not $out.productName -and ($l -match '^\s*Product Name\s*:\s*(.+)$')) { $out.productName = $matches[1].Trim(); continue }
    if (-not $out.driverVersion -and ($l -match '^\s*Driver Version\s*:\s*(.+)$')) { $out.driverVersion = $matches[1].Trim(); continue }
    if (-not $out.vbiosVersion -and ($l -match '^\s*VBIOS Version\s*:\s*(.+)$')) { $out.vbiosVersion = $matches[1].Trim(); continue }
    if (-not $out.vramTotal -and ($l -match '^\s*FB Memory Usage\s*$')) { $out._inFb = $true; continue }
    if ($out._inFb -and -not $out.vramTotal -and ($l -match '^\s*Total\s*:\s*(.+)$')) { $out.vramTotal = $matches[1].Trim(); $out._inFb = $false; continue }
  }

  $out.Remove('_inFb') | Out-Null
  return [pscustomobject]$out
}

# ----------------------------
# Snapshot builder
# ----------------------------
function Build-SystemSnapshot {
  param(
    [Parameter(Mandatory=$true)][hashtable]$Paths
  )

  $os = Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, BuildNumber, OSArchitecture
  $cpu = Get-CimInstance Win32_Processor | Select-Object Name, Manufacturer, NumberOfCores, NumberOfLogicalProcessors, MaxClockSpeed
  $cs  = Get-CimInstance Win32_ComputerSystem | Select-Object Manufacturer, Model, TotalPhysicalMemory
  $gpus = Get-CimInstance Win32_VideoController | Select-Object Name, DriverVersion, VideoProcessor, AdapterCompatibility

  $monWmi = Get-WmiMonitors

  $dxDisplays = @()
  if ($Paths.DxDiag -and (Test-Path -LiteralPath $Paths.DxDiag)) {
    try { $dxDisplays = Parse-DxDiagDisplays -DxDiagPath $Paths.DxDiag } catch { }
  }

  $nvidiaSmiSummary = $null
  if ($Paths.NvidiaSmi -and (Test-Path -LiteralPath $Paths.NvidiaSmi)) {
    try { $nvidiaSmiSummary = Parse-NvidiaSmiSummary -Path $Paths.NvidiaSmi } catch { }
  }

  $nvidiaSysInfo = $null
  if ($Paths.NvidiaSysInfo -and (Test-Path -LiteralPath $Paths.NvidiaSysInfo)) {
    try { $nvidiaSysInfo = Parse-NvidiaSystemInfo -Path $Paths.NvidiaSysInfo } catch { }
  }

  $bestDisplay = $null
  if ($dxDisplays -and $dxDisplays.Count -gt 0) {
    $bestDisplay = $dxDisplays | Sort-Object -Property @{Expression='refreshHz';Descending=$true} | Select-Object -First 1
  }

  $hdrDisplay = $null
  if ($dxDisplays -and $dxDisplays.Count -gt 0) {
    $hdrDisplay = $dxDisplays | Where-Object { $_.hdrSupported } | Sort-Object -Property @{Expression='refreshHz';Descending=$true} | Select-Object -First 1
  }

  $snap = [ordered]@{
    meta = [ordered]@{
      generatedISO = (Get-Date).ToString('o')
      machineName = $env:COMPUTERNAME
      script = 'Apex-HDR-SDR-Kit.ps1'
      mode = $Mode
    }
    system = [ordered]@{
      os = $os
      cpu = $cpu
      computer = [ordered]@{
        manufacturer = $cs.Manufacturer
        model = $cs.Model
        totalRamGB = [Math]::Round(($cs.TotalPhysicalMemory / 1GB), 2)
      }
      gpus = $gpus
      monitorsWmi = $monWmi
      displaysDxDiag = $dxDisplays
      bestDisplayDxDiag = $bestDisplay
      hdrCapableDisplayDxDiag = $hdrDisplay
      nvidia = [ordered]@{
        nvidiaSmiSummary = $nvidiaSmiSummary
        nvidiaSystemInfo = $nvidiaSysInfo
      }
    }
    files = [ordered]@{
      dxdiag = $Paths.DxDiag
      nvidiaSmi = $Paths.NvidiaSmi
      nvidiaSystemInfo = $Paths.NvidiaSysInfo
      cpuZReport = $Paths.CpuZ
      servicesList = $Paths.Services
    }
    privacy = [ordered]@{
      safeToShare = $true
      redactionsApplied = @('No user profile paths included by default')
    }
  }

  return $snap
}

# ----------------------------
# Gemini prompt + schema
# ----------------------------
function New-GeminiOutputSchema {
  $schema = [ordered]@{
    version = '1.0'
    requiredFiles = @('HDR_PROFILE.json','SDR_PROFILE.json','SETTINGS_CATALOG.json')
    profiles = [ordered]@{
      requiredKeys = @('meta','targets','toggles','launchOptions','hdrSetup','presets','performanceLogs','network','privacy')
    }
    settingsCatalogItem = [ordered]@{
      requiredKeys = @('id','category','scope','setting','current','hdrValue','sdrValue','why','evidence','risk','rollback','automation')
      evidenceItemRequiredKeys = @('url','publisher','type','date','quote')
      riskLevels = @('low','medium','high')
      automationMethods = @('manual','powershell','app_ui_only')
    }
    rules = @(
      'No guessing: if evidence is missing, set hdrValue/sdrValue to "INSUFFICIENT_EVIDENCE" and explain in why.',
      'Every non-empty recommendation must have at least 1 evidence item from a credible source.',
      'Any BIOS/firmware/overclocking/undocumented-registry edits must be risk=high and MUST NOT be included unless official documentation exists.'
    )
  }
  return $schema
}

function New-GeminiPrompt {
  param(
    [Parameter(Mandatory=$true)]$Snapshot,
    [Parameter(Mandatory=$true)][string]$SchemaPath,
    [Parameter(Mandatory=$true)][hashtable]$Paths
  )

  $sys = $Snapshot.system

  $gpuLines = @()
  foreach ($g in ($sys.gpus | Sort-Object Name -Unique)) {
    $gpuLines += "- $($g.Name) (DriverVersion: $($g.DriverVersion))"
  }
  if (-not $gpuLines) { $gpuLines = @('- (GPU unknown)') }

  $dispLines = @()
  foreach ($d in $sys.displaysDxDiag) {
    $dispLines += "- Monitor: $($d.monitorName) | Mode: $($d.currentWidth)x$($d.currentHeight)@$($d.refreshHz)Hz | HDR: $($d.hdrSupport) | AdvancedColor: $($d.advancedColor)"
  }
  if (-not $dispLines) { $dispLines = @('- (DxDiag display list unavailable)') }

  $hdrDisplay = $sys.hdrCapableDisplayDxDiag
  $hdrLine = if ($hdrDisplay) {
    "HDR-capable display detected (DxDiag): $($hdrDisplay.monitorName) @ $($hdrDisplay.currentWidth)x$($hdrDisplay.currentHeight) $($hdrDisplay.refreshHz)Hz"
  } else {
    'HDR-capable display not confidently detected from DxDiag.'
  }

  $nvidiaBits = @()
  if ($sys.nvidia.nvidiaSystemInfo) {
    $ni = $sys.nvidia.nvidiaSystemInfo
    $nvidiaBits += "- NVIDIA System Info: GPU=$($ni.gpu) | Driver=$($ni.driverVersion) | ResizableBAR=$($ni.resizableBar) | VRAM=$($ni.vram)"
  }
  if ($sys.nvidia.nvidiaSmiSummary) {
    $ns = $sys.nvidia.nvidiaSmiSummary
    $nvidiaBits += "- nvidia-smi: Product=$($ns.productName) | Driver=$($ns.driverVersion) | VRAM Total=$($ns.vramTotal)"
  }
  if (-not $nvidiaBits) { $nvidiaBits = @('- (NVIDIA summaries not available)') }

  $prompt = @"
You are Gemini (research + synthesis). Task: settle HDR vs SDR competitive settings for Apex Legends for THIS specific PC + display setup.

ABSOLUTE CONSTRAINTS
- NO GUESSING.
- Only include a recommendation if you can cite a credible source that contains empirical data OR official technical documentation.
- If you cannot prove a recommendation: output the setting but set the value to "INSUFFICIENT_EVIDENCE".
- Prefer primary sources: Microsoft docs, NVIDIA docs, monitor vendor docs, peer-reviewed or widely trusted measurement sites (e.g., RTINGS / Blur Busters), tool authors (PresentMon/FrameView docs).
- Do NOT suggest BIOS flashes, VBIOS edits, overclocking, undervolting, hidden registry hacks, or service-disabling "tweaks" unless (1) it’s officially documented, (2) reversible, (3) clearly safe.

DELIVERABLES (STRICT)
1) Output THREE files as JSON in THREE separate fenced code blocks (use triple-backtick code fences, language=json), exactly named:
   - HDR_PROFILE.json
   - SDR_PROFILE.json
   - SETTINGS_CATALOG.json
2) Each JSON must be valid (no trailing comments).
3) SETTINGS_CATALOG.json MUST conform to this schema file: $SchemaPath

WHAT TO BUILD
A) Two competitive profiles:
   - HDR Competitive Profile (Windows HDR pipeline ON)
   - SDR Competitive Profile (Windows HDR pipeline OFF)
B) A complete settings catalog (SETTINGS_CATALOG.json) covering ALL relevant categories below.
   For every setting:
   - setting path (where user finds it)
   - current value (from the provided files if possible; otherwise "UNKNOWN")
   - HDR profile value (or "INSUFFICIENT_EVIDENCE")
   - SDR profile value (or "INSUFFICIENT_EVIDENCE")
   - what it does (clear + technical)
   - measurable impact claims (only if cited)
   - evidence[] with at least 1 credible citation per recommendation
   - risk level + rollback steps
   - automation method: manual | powershell | app_ui_only

CATEGORIES TO COVER (do not skip)
1) Windows 11
   - Display: HDR / Auto HDR / SDR brightness in HDR / color management / HDR calibration
   - Graphics: Game Mode, Hardware-accelerated GPU scheduling (HAGS), Variable Refresh Rate setting
   - Power: power plan, sleep/hibernation behavior while gaming
   - Gaming: Xbox Game Bar/Captures (only if measurable impact is cited)
   - Fullscreen optimizations / borderless vs exclusive fullscreen (only if sourced)

2) NVIDIA (RTX 4070)
   - NVIDIA Control Panel: resolution, color format (RGB/YCbCr), output range, bit depth, refresh rate
   - G-SYNC/VRR + V-Sync interactions (driver vs in-game)
   - Low Latency / Reflex interactions (only if sourced)
   - RTX HDR (only if applicable + sourced)
   - Driver version notes if sources indicate regressions (must cite)

3) Monitor / Display Chain
   - Connection type (DP/HDMI), DSC if relevant (only if sourced)
   - Monitor OSD: overdrive, VRR, HDR mode/tone-mapping, local dimming, sharpness
   - Any setting that can cause permanent panel damage MUST be marked risk=high and excluded from recommendations unless official doc explicitly supports it.

4) Apex Legends
   - In-game video settings (every option): what it does, competitive recommendation when sourced
   - V-Sync, Reflex, AA, texture streaming budget, shadows, ambient occlusion, etc.
   - Launch options: ONLY include options proven current and safe. If an option is outdated/patch-dependent, mark INSUFFICIENT_EVIDENCE.

5) Overlays / Capture / Background
   - Discord overlay, Steam overlay, NVIDIA overlay, recording (only if sourced)

OUTPUT FORMAT DETAILS
- HDR_PROFILE.json and SDR_PROFILE.json must be compatible with the Apex Dashboard profile structure:
  meta, targets, toggles, launchOptions, hdrSetup, presets, performanceLogs, network, privacy
- SETTINGS_CATALOG.json must include:
  meta{}, systemSummary{}, settings[] (array), unsafeOrNoEvidence[] (array)

SYSTEM CONTEXT (from provided files)
OS:
- $($sys.os.Caption) | Version: $($sys.os.Version) | Build: $($sys.os.BuildNumber) | Arch: $($sys.os.OSArchitecture)
CPU:
- $($sys.cpu.Name) | Cores: $($sys.cpu.NumberOfCores) | Threads: $($sys.cpu.NumberOfLogicalProcessors)
GPU(s):
$($gpuLines -join "`n")
Displays (DxDiag):
$($dispLines -join "`n")
$hdrLine
NVIDIA details:
$($nvidiaBits -join "`n")

FILES YOU MUST USE (provided alongside this prompt)
- DxDiag: $($Paths.DxDiag)
- NVIDIA System Info (if present): $($Paths.NvidiaSysInfo)
- nvidia-smi output (if present): $($Paths.NvidiaSmi)
- CPU-Z report (if present): $($Paths.CpuZ)
- Services list (if present; only use if sourced + safe): $($Paths.Services)

FINAL CHECKS BEFORE YOU ANSWER
- If you cannot cite it, do not recommend it.
- Separate SAFE recommendations vs HIGH-RISK / NO-EVIDENCE items in SETTINGS_CATALOG.json.
- Keep profiles competitive: prioritize latency + clarity + stability.
"@

  return $prompt
}

# ----------------------------
# Profile templates (Apex Dashboard-compatible)
# ----------------------------
function New-ApexDashboardProfileTemplate {
  param(
    [Parameter(Mandatory=$true)]$Snapshot,
    [Parameter(Mandatory=$true)][ValidateSet('HDR','SDR')]$Flavor
  )

  $sys = $Snapshot.system
  $best = $sys.bestDisplayDxDiag
  $hdr = $sys.hdrCapableDisplayDxDiag

  $monitorName = if ($best -and $best.monitorName) { $best.monitorName } elseif ($hdr -and $hdr.monitorName) { $hdr.monitorName } else { 'Unknown' }
  $refresh = if ($best -and $best.refreshHz) { [int]$best.refreshHz } elseif ($hdr -and $hdr.refreshHz) { [int]$hdr.refreshHz } else { 0 }

  $gpuName = ''
  if ($sys.gpus -and $sys.gpus.Count -gt 0) {
    $gpuName = ($sys.gpus | Select-Object -First 1).Name
  }

  $isHdr = ($Flavor -eq 'HDR')

  $profileName = if ($isHdr) { 'Apex - HDR Competitive (Evidence-Based)' } else { 'Apex - SDR Competitive (Evidence-Based)' }

  $profile = [ordered]@{
    meta = [ordered]@{
      profileName = $profileName
      lastUpdatedISO = (Get-Date).ToString('o')
      monitor = $monitorName
      gpu = $gpuName
      os = $sys.os.Caption
      notes = 'TEMPLATE ONLY. Fill values only when you have sources + measurements.'
    }
    targets = [ordered]@{
      refreshHz = $refresh
      fpsTarget = 'INSUFFICIENT_EVIDENCE'
      latencyGoalMs = 'INSUFFICIENT_EVIDENCE'
    }
    toggles = [ordered]@{
      hdrWindowsOn = $isHdr
      autoHdrOn = if ($isHdr) { 'INSUFFICIENT_EVIDENCE' } else { $false }
      rtxHdrOn = 'INSUFFICIENT_EVIDENCE'
      gsyncOn = 'INSUFFICIENT_EVIDENCE'
      vsyncInGameOff = 'INSUFFICIENT_EVIDENCE'
      reflexBoostOn = 'INSUFFICIENT_EVIDENCE'
    }
    launchOptions = @(
      [ordered]@{ key='-novid'; enabled='INSUFFICIENT_EVIDENCE'; note='Only enable if sourced as current + safe.' },
      [ordered]@{ key='+fps_max 0'; enabled='INSUFFICIENT_EVIDENCE'; note='Only enable with sourced cap strategy.' },
      [ordered]@{ key='+m_rawinput 1'; enabled='INSUFFICIENT_EVIDENCE'; note='Only enable if confirmed still supported.' }
    )
    hdrSetup = [ordered]@{
      windows = @('INSUFFICIENT_EVIDENCE')
      nvidia  = @('INSUFFICIENT_EVIDENCE')
      monitor = @('INSUFFICIENT_EVIDENCE')
      apexBehavior = @('INSUFFICIENT_EVIDENCE')
    }
    presets = [ordered]@{
      'Competitive' = [ordered]@{
        Windows = [ordered]@{ }
        NVIDIA  = [ordered]@{ }
        Apex    = [ordered]@{ }
        Monitor = [ordered]@{ }
      }
    }
    performanceLogs = @()
    network = [ordered]@{
      connection = 'UNKNOWN'
      dns = 'UNKNOWN'
      router_model = ''
      modem_model = ''
      mtu = ''
      qos_enabled = ''
      bufferbloat_grade = ''
      isp = ''
      notes = ''
      tests = [ordered]@{
        speedtest_down_mbps = ''
        speedtest_up_mbps = ''
        speedtest_ping_ms = ''
        jitter_ms = ''
        packet_loss_pct = ''
      }
    }
    privacy = [ordered]@{
      sanitize_exports = $true
      redact_user_paths = $true
      redact_machine_name = $true
    }
  }

  return $profile
}

# ----------------------------
# Dashboard HTML (offline)
# ----------------------------
function New-DashboardHtml {
  param([Parameter(Mandatory=$true)][string]$OutFile)

  $html = @'
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Apex HDR/SDR Settings Dashboard (Offline)</title>
  <style>
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 16px; }
    header { display: flex; gap: 16px; align-items: baseline; flex-wrap: wrap; }
    h1 { font-size: 18px; margin: 0; }
    .muted { color: #666; font-size: 12px; }
    .controls { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; margin: 12px 0; }
    input[type="text"] { padding: 8px; min-width: 320px; }
    table { border-collapse: collapse; width: 100%; }
    th, td { border: 1px solid #ddd; padding: 8px; vertical-align: top; }
    th { position: sticky; top: 0; background: #f6f6f6; }
    details > summary { cursor: pointer; }
    .pill { display: inline-block; padding: 2px 8px; border-radius: 999px; border: 1px solid #ccc; font-size: 12px; }
    .pill.low { border-color: #2e7d32; }
    .pill.medium { border-color: #f9a825; }
    .pill.high { border-color: #c62828; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
    .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 12px; }
    .err { color: #b00020; }
  </style>
</head>
<body>
  <header>
    <h1>Apex HDR/SDR Settings Dashboard (Offline)</h1>
    <div class="muted">Load SETTINGS_CATALOG.json from Gemini output.</div>
  </header>

  <div class="controls">
    <input id="file" type="file" accept="application/json" />
    <input id="q" type="text" placeholder="Filter: category / setting / scope / evidence..." />
    <label><input id="safeOnly" type="checkbox" /> Safe only</label>
    <label>
      View:
      <select id="view">
        <option value="hdrValue">HDR profile</option>
        <option value="sdrValue">SDR profile</option>
      </select>
    </label>
    <span id="status" class="muted"></span>
  </div>

  <div id="meta" class="muted"></div>

  <table>
    <thead>
      <tr>
        <th style="width: 18%">Category</th>
        <th style="width: 16%">Scope</th>
        <th style="width: 18%">Setting</th>
        <th style="width: 12%">Current</th>
        <th style="width: 12%">Recommended</th>
        <th style="width: 8%">Risk</th>
        <th style="width: 16%">Details</th>
      </tr>
    </thead>
    <tbody id="rows"></tbody>
  </table>

<script>
  let catalog = null;
  let settings = [];

  const elFile = document.getElementById('file');
  const elQ = document.getElementById('q');
  const elSafe = document.getElementById('safeOnly');
  const elView = document.getElementById('view');
  const elRows = document.getElementById('rows');
  const elStatus = document.getElementById('status');
  const elMeta = document.getElementById('meta');

  function norm(s){ return (s || '').toString().toLowerCase(); }

  function safeBool(item){
    const r = norm(item?.risk?.level);
    return r === 'low' || r === 'medium';
  }

  function evidenceCount(item){
    return Array.isArray(item?.evidence) ? item.evidence.length : 0;
  }

  function render(){
    const q = norm(elQ.value);
    const safeOnly = elSafe.checked;
    const viewKey = elView.value;

    const filtered = settings.filter(item => {
      if (safeOnly && !safeBool(item)) return false;
      if (!q) return true;

      const blob = [
        item.category,
        item.scope,
        item.setting,
        item.current,
        item[viewKey],
        item?.why,
        item?.risk?.level,
        (item?.evidence || []).map(e => e.url).join(' ')
      ].map(norm).join(' ');

      return blob.includes(q);
    });

    elRows.innerHTML = '';

    for (const item of filtered){
      const tr = document.createElement('tr');

      const risk = norm(item?.risk?.level) || 'unknown';
      const pill = `<span class="pill ${risk}">${risk}</span>`;

      const ev = evidenceCount(item);

      tr.innerHTML = `
        <td>${item.category || ''}</td>
        <td>${item.scope || ''}</td>
        <td class="mono">${item.setting || ''}</td>
        <td class="mono">${item.current || ''}</td>
        <td class="mono">${item[viewKey] || ''}</td>
        <td>${pill}</td>
        <td>
          <details>
            <summary>${ev} evidence • rollback • automation</summary>
            <div style="margin-top:8px" class="grid">
              <div>
                <div><b>Why</b></div>
                <div class="mono">${(item.why || '').replaceAll('<','&lt;')}</div>
              </div>
              <div>
                <div><b>Rollback</b></div>
                <div class="mono">${(Array.isArray(item.rollback) ? item.rollback.join('\n') : (item.rollback || '')).replaceAll('<','&lt;')}</div>
              </div>
              <div>
                <div><b>Automation</b></div>
                <div class="mono">${(item.automation || '').toString().replaceAll('<','&lt;')}</div>
              </div>
              <div>
                <div><b>Evidence</b></div>
                <div class="mono">${(item.evidence || []).map(e => {
                  const url = e.url || '';
                  const pub = e.publisher || '';
                  const type = e.type || '';
                  return `<div><a href="${url}" target="_blank">${pub || url}</a> • ${type}</div>`;
                }).join('') || '<span class="err">(none)</span>'}</div>
              </div>
            </div>
          </details>
        </td>
      `;

      elRows.appendChild(tr);
    }

    elStatus.textContent = `Loaded: ${settings.length} • Showing: ${filtered.length}`;
  }

  elFile.addEventListener('change', async (evt) => {
    const f = evt.target.files?.[0];
    if (!f) return;

    const txt = await f.text();
    catalog = JSON.parse(txt);

    // Accept either { settings: [...] } or [...] directly
    settings = Array.isArray(catalog) ? catalog : (catalog.settings || []);

    const gen = catalog?.meta?.generatedISO || '(unknown time)';
    const sys = catalog?.systemSummary?.oneLine || '';
    elMeta.textContent = `Catalog generated: ${gen} ${sys ? ' • ' + sys : ''}`;

    render();
  });

  elQ.addEventListener('input', render);
  elSafe.addEventListener('change', render);
  elView.addEventListener('change', render);
</script>
</body>
</html>
'@

  $html | Out-File -LiteralPath $OutFile -Encoding utf8
}

# ----------------------------
# Generate
# ----------------------------
function Do-Generate {
  $Workspace = Resolve-FullPath $Workspace

  $dInputs   = Join-Path $Workspace '00_inputs'
  $dSnap     = Join-Path $Workspace '01_snapshot'
  $dGemini   = Join-Path $Workspace '02_gemini'
  $dProfiles = Join-Path $Workspace '03_profiles'
  $dDash     = Join-Path $Workspace '04_dashboard'
  $dOut      = Join-Path $Workspace '05_gemini_output'

  foreach ($d in @($Workspace,$dInputs,$dSnap,$dGemini,$dProfiles,$dDash,$dOut)) { New-Dir $d }

  $paths = @{
    DxDiag = ''
    NvidiaSmi = ''
    NvidiaSysInfo = ''
    CpuZ = ''
    Services = ''
  }

  # If user supplies an input dir, prefer copying those files as-is.
  if ($InputDir) {
    $InputDir = Resolve-FullPath $InputDir
    if (-not (Test-Path -LiteralPath $InputDir)) {
      throw "InputDir not found: $InputDir"
    }

    Write-Log INFO "Using InputDir: $InputDir"

    $candidateDx = Join-Path $InputDir 'DxDiag.txt'
    if (Copy-IfExists $candidateDx (Join-Path $dInputs 'DxDiag.txt')) {
      $paths.DxDiag = Join-Path $dInputs 'DxDiag.txt'
    }

    $candidateCpuZ = Join-Path $InputDir 'FALSEGAMINGDESK.txt'
    if (Copy-IfExists $candidateCpuZ (Join-Path $dInputs 'FALSEGAMINGDESK.txt')) {
      $paths.CpuZ = Join-Path $dInputs 'FALSEGAMINGDESK.txt'
    }

    $candidateServices = Join-Path $InputDir 'servicesForApexOpt.txt'
    if (Copy-IfExists $candidateServices (Join-Path $dInputs 'servicesForApexOpt.txt')) {
      $paths.Services = Join-Path $dInputs 'servicesForApexOpt.txt'
    }

    # NVIDIA System Information file name varies; pick first match.
    $nsi = Get-ChildItem -LiteralPath $InputDir -File -ErrorAction SilentlyContinue | Where-Object {
      $_.Name -like 'NVIDIA System Information*.txt'
    } | Select-Object -First 1

    if ($nsi) {
      Copy-Item -LiteralPath $nsi.FullName -Destination (Join-Path $dInputs $nsi.Name) -Force
      $paths.NvidiaSysInfo = Join-Path $dInputs $nsi.Name
    }
  }

  # Collect dxdiag if we don't already have it.
  if (-not $paths.DxDiag -and -not $NoDxDiag) {
    $dxOut = Join-Path $dInputs 'DxDiag.txt'
    $dxExe = Join-Path $env:SystemRoot 'System32\dxdiag.exe'

    if (Test-Path -LiteralPath $dxExe) {
      Write-Log INFO "Running dxdiag export..."
      Start-Process -FilePath $dxExe -ArgumentList "/t `"$dxOut`"" -Wait -NoNewWindow
      if (Test-Path -LiteralPath $dxOut) {
        $paths.DxDiag = $dxOut
        Write-Log OK "dxdiag saved: $dxOut"
      } else {
        Write-Log WARN "dxdiag did not produce output file."
      }
    } else {
      Write-Log WARN "dxdiag.exe not found at expected path: $dxExe"
    }
  }

  # Collect nvidia-smi if possible.
  if (-not $paths.NvidiaSmi -and -not $NoNvidiaSmi) {
    $smi = Find-NvidiaSmi
    if ($smi) {
      $smiOut = Join-Path $dInputs 'nvidia-smi-q.txt'
      Write-Log INFO "Running nvidia-smi -q..."
      Invoke-ExternalToFile -Exe $smi -Args @('-q') -OutFile $smiOut
      $paths.NvidiaSmi = $smiOut
      Write-Log OK "nvidia-smi saved: $smiOut"
    } else {
      Write-Log WARN "nvidia-smi not found (skipping)."
    }
  }

  # Always collect WMI monitor list (small + safe)
  $wmiMonPath = Join-Path $dInputs 'monitors_wmi.json'
  try {
    $mons = Get-WmiMonitors
    Save-Json -Path $wmiMonPath -Object $mons -Depth 6
    Write-Log OK "WMI monitors saved: $wmiMonPath"
  } catch {
    Write-Log WARN "Failed to query WMI monitors: $($_.Exception.Message)"
  }

  # Build snapshot
  Write-Log INFO "Building system snapshot..."
  $snapshot = Build-SystemSnapshot -Paths $paths

  $snapPath = Join-Path $dSnap 'system_snapshot.json'
  Save-Json -Path $snapPath -Object $snapshot -Depth 14
  Write-Log OK "Snapshot saved: $snapPath"

  # Output schema
  $schema = New-GeminiOutputSchema
  $schemaPath = Join-Path $dGemini 'GEMINI_OUTPUT_SCHEMA.json'
  Save-Json -Path $schemaPath -Object $schema -Depth 10
  Write-Log OK "Schema saved: $schemaPath"

  # Gemini prompt
  $promptPath = Join-Path $dGemini 'GEMINI_PROMPT.md'
  $promptText = New-GeminiPrompt -Snapshot $snapshot -SchemaPath $schemaPath -Paths $paths
  $promptText | Out-File -LiteralPath $promptPath -Encoding utf8
  Write-Log OK "Gemini prompt saved: $promptPath"

  # Profile templates
  $hdrProfile = New-ApexDashboardProfileTemplate -Snapshot $snapshot -Flavor HDR
  $sdrProfile = New-ApexDashboardProfileTemplate -Snapshot $snapshot -Flavor SDR

  $hdrPath = Join-Path $dProfiles 'HDR_Competitive_PROFILE_TEMPLATE.json'
  $sdrPath = Join-Path $dProfiles 'SDR_Competitive_PROFILE_TEMPLATE.json'
  Save-Json -Path $hdrPath -Object $hdrProfile -Depth 14
  Save-Json -Path $sdrPath -Object $sdrProfile -Depth 14
  Write-Log OK "Profile templates saved: $dProfiles"

  # Offline dashboard
  $dashPath = Join-Path $dDash 'Apex_Settings_Dashboard.html'
  New-DashboardHtml -OutFile $dashPath
  Write-Log OK "Offline dashboard saved: $dashPath"

  # Optional: copy templates into Apex Dashboard folder
  if ($ApexDashboardPath) {
    $ApexDashboardPath = Resolve-FullPath $ApexDashboardPath
    $profilesDir = Join-Path $ApexDashboardPath 'Profiles'
    if (Test-Path -LiteralPath $ApexDashboardPath) {
      New-Dir $profilesDir
      Copy-Item -LiteralPath $hdrPath -Destination (Join-Path $profilesDir (Split-Path $hdrPath -Leaf)) -Force
      Copy-Item -LiteralPath $sdrPath -Destination (Join-Path $profilesDir (Split-Path $sdrPath -Leaf)) -Force
      Write-Log OK "Copied templates into: $profilesDir"
    } else {
      Write-Log WARN "ApexDashboardPath not found: $ApexDashboardPath"
    }
  }

  # Create placeholder folder for Gemini output
  $readmeOut = Join-Path $dOut 'README.txt'
  @"
Put Gemini outputs here (exact filenames):
- HDR_PROFILE.json
- SDR_PROFILE.json
- SETTINGS_CATALOG.json

Then run:
  .\Apex-HDR-SDR-Kit.ps1 -Mode Validate -Workspace `"$Workspace`" -GeminiOutputDir `"$dOut`"
"@ | Out-File -LiteralPath $readmeOut -Encoding utf8

  if ($Open) {
    Start-Process explorer.exe $Workspace | Out-Null
  }
}

# ----------------------------
# Validate
# ----------------------------
function Load-JsonFile {
  param([Parameter(Mandatory=$true)][string]$Path)
  $raw = Get-Content -LiteralPath $Path -Raw -ErrorAction Stop
  return $raw | ConvertFrom-Json -ErrorAction Stop
}

function Validate-ProfileJson {
  param(
    [Parameter(Mandatory=$true)]$Profile,
    [Parameter(Mandatory=$true)][string[]]$RequiredKeys
  )

  $missing = @()
  foreach ($k in $RequiredKeys) {
    if (-not ($Profile.PSObject.Properties.Name -contains $k)) {
      $missing += $k
    }
  }

  return $missing
}

function Validate-SettingsCatalog {
  param(
    [Parameter(Mandatory=$true)]$Catalog,
    [Parameter(Mandatory=$true)]$Schema
  )

  $problems = New-Object System.Collections.Generic.List[string]

  $items = @()
  if ($Catalog -is [System.Array]) { $items = $Catalog }
  elseif ($Catalog.settings) { $items = $Catalog.settings }

  if (-not $items -or $items.Count -eq 0) {
    $problems.Add('settings[] is missing or empty.')
    return $problems
  }

  $req = $Schema.settingsCatalogItem.requiredKeys
  $eReq = $Schema.settingsCatalogItem.evidenceItemRequiredKeys

  $i = 0
  foreach ($it in $items) {
    $i++
    foreach ($k in $req) {
      if (-not ($it.PSObject.Properties.Name -contains $k)) {
        $problems.Add("settings[$i] missing key: $k")
      }
    }

    # evidence checks
    if (-not $it.evidence -or $it.evidence.Count -lt 1) {
      $problems.Add("settings[$i] has no evidence[]")
    } else {
      $j = 0
      foreach ($ev in $it.evidence) {
        $j++
        foreach ($ek in $eReq) {
          if (-not ($ev.PSObject.Properties.Name -contains $ek)) {
            $problems.Add("settings[$i].evidence[$j] missing key: $ek")
          }
        }
      }
    }

    # risk level checks
    $risk = ($it.risk.level | ForEach-Object { $_.ToString().ToLowerInvariant() })
    if ($risk -and -not ($Schema.settingsCatalogItem.riskLevels -contains $risk)) {
      $problems.Add("settings[$i] invalid risk.level: $risk")
    }

    # automation checks
    $method = ($it.automation.method | ForEach-Object { $_.ToString().ToLowerInvariant() })
    if ($method -and -not ($Schema.settingsCatalogItem.automationMethods -contains $method)) {
      $problems.Add("settings[$i] invalid automation.method: $method")
    }
  }

  return $problems
}

function Do-Validate {
  if (-not $GeminiOutputDir) {
    throw "-GeminiOutputDir is required for Mode=Validate"
  }

  $GeminiOutputDir = Resolve-FullPath $GeminiOutputDir
  if (-not (Test-Path -LiteralPath $GeminiOutputDir)) {
    throw "GeminiOutputDir not found: $GeminiOutputDir"
  }

  $schemaPath = Join-Path (Join-Path $Workspace '02_gemini') 'GEMINI_OUTPUT_SCHEMA.json'
  if (-not (Test-Path -LiteralPath $schemaPath)) {
    throw "Schema not found. Run Mode=Generate first. Missing: $schemaPath"
  }

  $schema = Load-JsonFile -Path $schemaPath

  $hdrPath = Join-Path $GeminiOutputDir 'HDR_PROFILE.json'
  $sdrPath = Join-Path $GeminiOutputDir 'SDR_PROFILE.json'
  $catPath = Join-Path $GeminiOutputDir 'SETTINGS_CATALOG.json'

  $report = New-Object System.Collections.Generic.List[string]
  $report.Add("Validation report: $(Get-Date -Format o)")
  $report.Add('')

  $ok = $true

  foreach ($p in @($hdrPath,$sdrPath,$catPath)) {
    if (-not (Test-Path -LiteralPath $p)) {
      $ok = $false
      $report.Add("MISSING FILE: $p")
    } else {
      $report.Add("FOUND FILE:   $p")
    }
  }
  $report.Add('')

  if ($ok) {
    $hdr = Load-JsonFile -Path $hdrPath
    $sdr = Load-JsonFile -Path $sdrPath
    $cat = Load-JsonFile -Path $catPath

    $reqKeys = $schema.profiles.requiredKeys

    $missHdr = Validate-ProfileJson -Profile $hdr -RequiredKeys $reqKeys
    $missSdr = Validate-ProfileJson -Profile $sdr -RequiredKeys $reqKeys

    if ($missHdr.Count -gt 0) { $ok = $false; $report.Add("HDR_PROFILE missing keys: $($missHdr -join ', ')") }
    else { $report.Add('HDR_PROFILE keys: OK') }

    if ($missSdr.Count -gt 0) { $ok = $false; $report.Add("SDR_PROFILE missing keys: $($missSdr -join ', ')") }
    else { $report.Add('SDR_PROFILE keys: OK') }

    $report.Add('')

    $catProblems = Validate-SettingsCatalog -Catalog $cat -Schema $schema
    if ($catProblems.Count -gt 0) {
      $ok = $false
      $report.Add('SETTINGS_CATALOG problems:')
      foreach ($prob in $catProblems) { $report.Add("- $prob") }
    } else {
      $report.Add('SETTINGS_CATALOG: OK')
    }

    $report.Add('')
    $report.Add("OVERALL: " + ($(if ($ok) { 'PASS' } else { 'FAIL' })))
  } else {
    $report.Add('')
    $report.Add('OVERALL: FAIL (missing required files)')
  }

  $outPath = Join-Path $GeminiOutputDir 'VALIDATION_REPORT.md'
  $report -join "`n" | Out-File -LiteralPath $outPath -Encoding utf8

  if ($ok) {
    Write-Log OK "Validation PASS. Report: $outPath"
  } else {
    Write-Log ERROR "Validation FAIL. Report: $outPath"
  }

  if ($Open) {
    Start-Process explorer.exe $GeminiOutputDir | Out-Null
  }
}

# ----------------------------
# Import
# ----------------------------
function Do-Import {
  if (-not $GeminiOutputDir) {
    throw "-GeminiOutputDir is required for Mode=Import"
  }
  if (-not $ApexDashboardPath) {
    throw "-ApexDashboardPath is required for Mode=Import"
  }

  $GeminiOutputDir = Resolve-FullPath $GeminiOutputDir
  $ApexDashboardPath = Resolve-FullPath $ApexDashboardPath

  $hdrPath = Join-Path $GeminiOutputDir 'HDR_PROFILE.json'
  $sdrPath = Join-Path $GeminiOutputDir 'SDR_PROFILE.json'

  if (-not (Test-Path -LiteralPath $hdrPath)) { throw "Missing: $hdrPath" }
  if (-not (Test-Path -LiteralPath $sdrPath)) { throw "Missing: $sdrPath" }

  if (-not (Test-Path -LiteralPath $ApexDashboardPath)) {
    throw "ApexDashboardPath not found: $ApexDashboardPath"
  }

  $profilesDir = Join-Path $ApexDashboardPath 'Profiles'
  New-Dir $profilesDir

  $dstHdr = Join-Path $profilesDir 'HDR_PROFILE.json'
  $dstSdr = Join-Path $profilesDir 'SDR_PROFILE.json'

  Copy-Item -LiteralPath $hdrPath -Destination $dstHdr -Force
  Copy-Item -LiteralPath $sdrPath -Destination $dstSdr -Force

  Write-Log OK "Imported profiles to: $profilesDir"
  Write-Log INFO "Next: open your Apex Dashboard and Import JSON (or use these files directly)."

  if ($Open) {
    Start-Process explorer.exe $profilesDir | Out-Null
  }
}

# ----------------------------
# Main
# ----------------------------
try {
  $Workspace = Resolve-FullPath $Workspace
  New-Dir $Workspace

  Write-Log INFO "Mode=$Mode"
  Write-Log INFO "Workspace=$Workspace"

  switch ($Mode) {
    'Generate' { Do-Generate }
    'Validate' { Do-Validate }
    'Import'   { Do-Import }
  }

  Write-Log OK "Done."
} catch {
  Write-Log ERROR $_.Exception.Message
  throw
}
