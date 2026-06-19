#requires -RunAsAdministrator
<#
FalseTech Network Refresh v2.1
Safe refresh + diagnostics for Apex Legends / Windows 11

Updated for current clean Apex baseline:
  - Preferred gaming adapter: Ethernet / Realtek PCIe 5GbE Family Controller
  - Router gateway target: 192.168.1.1
  - Current gaming PC reservation: 192.168.1.14
  - Preferred DNS based on local benchmark: 1.0.0.1 primary, 1.1.1.1 secondary
  - Fallback DNS if Cloudflare spikes: 9.9.9.9 / 149.112.112.112
  - QoS should stay OFF unless dashboard proves jitter under load
  - UPnP ON, WMM ON, DMZ OFF
  - IPv6 tunnel/6to4 "2002:" addresses should stay gone

Usage:
  PowerShell (Admin):
    Set-ExecutionPolicy -Scope Process Bypass
    .\FalseTech-NetworkRefresh.ps1

Recommended normal Apex pre-check:
    .\FalseTech-NetworkRefresh.ps1 -PingCount 20

Optional DNS test:
    .\FalseTech-NetworkRefresh.ps1 -RunDnsBenchmark

Optional apply local Windows DNS override:
    .\FalseTech-NetworkRefresh.ps1 -ApplyPreferredDns

Optional undo local Windows DNS override and use DHCP/router DNS:
    .\FalseTech-NetworkRefresh.ps1 -ResetDnsToDhcp

Optional disable IPv6 binding on the gaming Ethernet adapter:
    .\FalseTech-NetworkRefresh.ps1 -DisableIPv6OnAdapter

Optional full network stack reset, reboot recommended:
    .\FalseTech-NetworkRefresh.ps1 -FullReset
    .\FalseTech-NetworkRefresh.ps1 -FullReset -RestartComputer

Notes:
  - By default, this script does NOT reset Winsock/TCP-IP anymore.
  - Full stack reset is available with -FullReset because it is heavier and best followed by reboot.
  - Ping tests use ping.exe instead of Test-Connection so it works on Windows PowerShell 5.1 and PowerShell 7.
#>

param(
    [switch]$RestartComputer,
    [switch]$FullReset,
    [switch]$RunDnsBenchmark,
    [switch]$ApplyPreferredDns,
    [switch]$ResetDnsToDhcp,
    [switch]$DisableIPv6OnAdapter,
    [switch]$SkipAdapterRestart,

    [int]$PingCount = 15,
    [int]$DnsCount = 5,

    [string]$PreferredAdapterName = 'Ethernet',
    [string]$RouterTarget = '192.168.1.1',
    [string]$DnsDomain = 'ea.com',

    [string[]]$PreferredDns = @('1.0.0.1', '1.1.1.1'),
    [string[]]$PingTargets = @('192.168.1.1', '1.0.0.1', '1.1.1.1', '8.8.8.8', '9.9.9.9', 'ea.com', 'cloudflare.com'),
    [string[]]$DnsBenchmarkServers = @('1.0.0.1', '1.1.1.1', '9.9.9.9', '149.112.112.112', '8.8.8.8', '8.8.4.4', '208.67.222.222', '208.67.220.220')
)

$ErrorActionPreference = 'Stop'

function Assert-Admin {
    $currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentIdentity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'Run this script in an elevated PowerShell window.'
    }
}

function Write-Section {
    param([string]$Text)

    $line = ('=' * 78)
    Write-Host "`n$line" -ForegroundColor Cyan
    Write-Host $Text -ForegroundColor Cyan
    Write-Host $line -ForegroundColor Cyan

    if ($script:LogFile) {
        Add-Content -Path $script:LogFile -Value "`n$line`n$Text`n$line"
    }
}

function Write-Log {
    param(
        [string]$Text,
        [ConsoleColor]$Color = [ConsoleColor]::Gray
    )

    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $entry = "[$timestamp] $Text"

    Write-Host $entry -ForegroundColor $Color

    if ($script:LogFile) {
        Add-Content -Path $script:LogFile -Value $entry
    }
}

function Invoke-LoggedCommand {
    param(
        [string]$Label,
        [scriptblock]$Command
    )

    Write-Log "START: $Label"
    try {
        $output = & $Command 2>&1 | Out-String
        if ($output.Trim()) {
            Add-Content -Path $script:LogFile -Value $output
        }
        Write-Log "OK: $Label" Green
    }
    catch {
        Write-Log "ERROR: $Label -> $($_.Exception.Message)" Red
    }
}

function Get-PreferredGamingAdapter {
    param([string]$Name = 'Ethernet')

    $byName = Get-NetAdapter -Name $Name -ErrorAction SilentlyContinue
    if ($byName -and $byName.Status -eq 'Up') {
        return $byName
    }

    $realtek = Get-NetAdapter |
        Where-Object {
            $_.Status -eq 'Up' -and
            $_.HardwareInterface -eq $true -and
            $_.InterfaceDescription -match 'Realtek|GbE|Ethernet' -and
            $_.InterfaceDescription -notmatch 'Wi-Fi|Wireless|Bluetooth|Virtual|VPN|Loopback|Hyper-V|VMware|VirtualBox|Tailscale'
        } |
        Select-Object -First 1

    if ($realtek) {
        return $realtek
    }

    $wired = Get-NetAdapter |
        Where-Object {
            $_.Status -eq 'Up' -and
            $_.HardwareInterface -eq $true -and
            $_.InterfaceDescription -notmatch 'Wi-Fi|Wireless|Bluetooth|Virtual|VPN|Loopback|Hyper-V|VMware|VirtualBox|Tailscale'
        } |
        Select-Object -First 1

    if ($wired) {
        return $wired
    }

    return Get-NetAdapter | Where-Object { $_.Status -eq 'Up' } | Select-Object -First 1
}

function Wait-AdapterOnline {
    param(
        [string]$Name,
        [int]$TimeoutSeconds = 45
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $adapter = Get-NetAdapter -Name $Name -ErrorAction SilentlyContinue
        if ($adapter -and $adapter.Status -eq 'Up') {
            return $adapter
        }
        Start-Sleep -Seconds 2
    }

    return $null
}

function Test-PingTarget {
    param(
        [string]$Target,
        [int]$Count = 10
    )

    Write-Log "Ping test -> $Target"

    try {
        $outputLines = & ping.exe -n $Count $Target 2>&1
        $output = $outputLines -join "`n"

        $sent = $Count
        $received = $null
        $lost = $null
        $lossPct = $null
        $min = $null
        $avg = $null
        $max = $null

        if ($output -match 'Sent = (\d+), Received = (\d+), Lost = (\d+) \((\d+)% loss\)') {
            $sent = [int]$matches[1]
            $received = [int]$matches[2]
            $lost = [int]$matches[3]
            $lossPct = [int]$matches[4]
        }

        if ($output -match 'Minimum = (\d+)ms, Maximum = (\d+)ms, Average = (\d+)ms') {
            $min = [int]$matches[1]
            $max = [int]$matches[2]
            $avg = [int]$matches[3]
        }

        if ($null -eq $received) {
            Write-Log "Ping parse warning for $Target. Raw output saved to log." Yellow
            Add-Content -Path $script:LogFile -Value $output
            return
        }

        $summary = "Target=$Target | Sent=$sent | Received=$received | Lost=$lost | Loss=${lossPct}% | Min=${min}ms | Avg=${avg}ms | Max=${max}ms"
        Write-Log $summary

        if ($lossPct -gt 0) {
            Write-Log "WARNING: Packet loss detected on $Target" Yellow
        }
        elseif ($max -ge 50 -and $Target -eq $RouterTarget) {
            Write-Log "WARNING: Router latency spike detected on $Target" Yellow
        }
        elseif ($max -ge 80) {
            Write-Log "WARNING: Internet latency spike detected on $Target" Yellow
        }
    }
    catch {
        Write-Log "Ping failed for $Target -> $($_.Exception.Message)" Red
    }
}

function Test-NetworkTargets {
    param(
        [string[]]$Targets,
        [int]$Count = 10
    )

    foreach ($target in $Targets) {
        Test-PingTarget -Target $target -Count $Count
    }
}

function Test-DnsResolvers {
    param(
        [string[]]$Servers,
        [string]$Domain = 'ea.com',
        [int]$Count = 5
    )

    Write-Section "DNS RESOLVER BENCHMARK"
    Write-Log "Domain: $Domain"
    Write-Log "Preferred based on last local benchmark: 1.0.0.1 primary, 1.1.1.1 secondary"

    $results = @()

    foreach ($server in $Servers) {
        $times = @()

        for ($i = 1; $i -le $Count; $i++) {
            $sw = [System.Diagnostics.Stopwatch]::StartNew()
            try {
                Resolve-DnsName $Domain -Server $server -ErrorAction Stop | Out-Null
                $sw.Stop()
                $times += $sw.ElapsedMilliseconds
            }
            catch {
                $sw.Stop()
                $times += 9999
            }
        }

        $results += [PSCustomObject]@{
            DNS     = $server
            AvgMs   = [math]::Round(($times | Measure-Object -Average).Average, 2)
            BestMs  = ($times | Measure-Object -Minimum).Minimum
            WorstMs = ($times | Measure-Object -Maximum).Maximum
        }
    }

    $table = $results | Sort-Object AvgMs | Format-Table -AutoSize | Out-String
    Write-Host $table
    Add-Content -Path $script:LogFile -Value $table

    $winner = $results | Sort-Object AvgMs | Select-Object -First 1
    if ($winner) {
        Write-Log "Fastest DNS in this run: $($winner.DNS) | Avg=$($winner.AvgMs)ms | Best=$($winner.BestMs)ms | Worst=$($winner.WorstMs)ms" Green
    }
}

function Test-IPv6TunnelState {
    Write-Section "IPv6 / 6to4 TUNNEL CHECK"

    $ipconfig = ipconfig /all | Out-String

    if ($ipconfig -match '2002:') {
        Write-Log 'WARNING: 2002: IPv6 tunnel/6to4 address or DNS still detected. For current Apex baseline, remove/disable it.' Yellow
    }
    else {
        Write-Log 'PASS: No 2002: IPv6 tunnel entries detected.' Green
    }

    if ($ipconfig -match 'DNS Servers[\s\S]*1\.0\.0\.1' -or $ipconfig -match 'DNS Servers[\s\S]*1\.1\.1\.1') {
        Write-Log 'DNS check: Cloudflare DNS appears in ipconfig output.'
    }
    else {
        Write-Log 'DNS check: Cloudflare DNS not clearly found in ipconfig output. Router/DHCP may be using different DNS.' Yellow
    }
}

function Export-NetworkSnapshot {
    param([string]$Phase)

    Write-Section "NETWORK SNAPSHOT: $Phase"

    Invoke-LoggedCommand -Label 'ipconfig /all' -Command { ipconfig /all }
    Invoke-LoggedCommand -Label 'route print' -Command { route print }
    Invoke-LoggedCommand -Label 'Get-NetIPConfiguration' -Command { Get-NetIPConfiguration | Format-List * }
    Invoke-LoggedCommand -Label 'Get-DnsClientServerAddress' -Command { Get-DnsClientServerAddress | Format-Table -AutoSize }
    Invoke-LoggedCommand -Label 'Get-NetAdapter' -Command { Get-NetAdapter | Format-Table -AutoSize }
    Invoke-LoggedCommand -Label 'Get-NetAdapterBinding IPv6' -Command { Get-NetAdapterBinding -ComponentID ms_tcpip6 | Format-Table -AutoSize }
    Invoke-LoggedCommand -Label 'Get-NetAdapterStatistics' -Command { Get-NetAdapterStatistics | Format-Table -AutoSize }
}

try {
    Assert-Admin

    $timestamp = Get-Date -Format 'yyyy-MM-dd_HH-mm-ss'
    $baseDir = Join-Path $env:USERPROFILE 'Desktop\FalseTech\NetworkRefresh'
    New-Item -ItemType Directory -Force -Path $baseDir | Out-Null
    $script:LogFile = Join-Path $baseDir "NetworkRefresh_$timestamp.log"

    Write-Section "FalseTech Network Refresh v2.1"
    Write-Log "Log file: $LogFile"
    Write-Log "Computer: $env:COMPUTERNAME"
    Write-Log "User: $env:USERNAME"
    Write-Log "OS: $((Get-CimInstance Win32_OperatingSystem).Caption)"
    Write-Log "Start time: $(Get-Date)"
    Write-Log "Router target: $RouterTarget"
    Write-Log "Preferred DNS: $($PreferredDns -join ', ')"
    Write-Log "QoS baseline: OFF"
    Write-Log "UPnP baseline: ON"
    Write-Log "WMM baseline: ON"
    Write-Log "DMZ baseline: OFF"
    Write-Log "IPv6 tunnel baseline: 2002: entries should be absent"

    $activeAdapter = Get-PreferredGamingAdapter -Name $PreferredAdapterName
    if ($null -eq $activeAdapter) {
        throw 'No active network adapter found.'
    }

    Write-Log "Preferred adapter detected: $($activeAdapter.Name) | InterfaceDescription: $($activeAdapter.InterfaceDescription) | Status: $($activeAdapter.Status)" Green

    Export-NetworkSnapshot -Phase 'BEFORE'
    Test-IPv6TunnelState

    Write-Section "BASELINE CONNECTIVITY TEST"
    Test-NetworkTargets -Targets $PingTargets -Count $PingCount

    if ($RunDnsBenchmark) {
        Test-DnsResolvers -Servers $DnsBenchmarkServers -Domain $DnsDomain -Count $DnsCount
    }

    Write-Section "SAFE NETWORK REFRESH"

    if ($ApplyPreferredDns -and $ResetDnsToDhcp) {
        throw 'Choose either -ApplyPreferredDns or -ResetDnsToDhcp, not both.'
    }

    if ($ApplyPreferredDns) {
        Invoke-LoggedCommand -Label "Apply preferred DNS to $($activeAdapter.Name): $($PreferredDns -join ', ')" -Command {
            Set-DnsClientServerAddress -InterfaceAlias $activeAdapter.Name -ServerAddresses $PreferredDns
        }
    }

    if ($ResetDnsToDhcp) {
        Invoke-LoggedCommand -Label "Reset DNS to DHCP/router on $($activeAdapter.Name)" -Command {
            Set-DnsClientServerAddress -InterfaceAlias $activeAdapter.Name -ResetServerAddresses
        }
    }

    if ($DisableIPv6OnAdapter) {
        Invoke-LoggedCommand -Label "Disable IPv6 binding on $($activeAdapter.Name)" -Command {
            Disable-NetAdapterBinding -Name $activeAdapter.Name -ComponentID ms_tcpip6
        }
    }

    Invoke-LoggedCommand -Label 'Flush DNS' -Command { ipconfig /flushdns }
    Invoke-LoggedCommand -Label 'Release DHCP leases' -Command { ipconfig /release }
    Start-Sleep -Seconds 2
    Invoke-LoggedCommand -Label 'Renew DHCP leases' -Command { ipconfig /renew }

    if ($FullReset) {
        Invoke-LoggedCommand -Label 'Reset Winsock catalog' -Command { netsh winsock reset }
        Invoke-LoggedCommand -Label 'Reset TCP/IP stack' -Command { netsh int ip reset }
        Write-Log 'FullReset selected. A reboot is strongly recommended.' Yellow
    }
    else {
        Write-Log 'Skipped Winsock/TCP-IP reset. Use -FullReset only when needed.' Yellow
    }

    if (-not $SkipAdapterRestart) {
        Write-Log "Restarting preferred adapter only: $($activeAdapter.Name)"
        Disable-NetAdapter -Name $activeAdapter.Name -Confirm:$false -ErrorAction Stop
        Start-Sleep -Seconds 5
        Enable-NetAdapter -Name $activeAdapter.Name -Confirm:$false -ErrorAction Stop

        $sameAdapterAfter = Wait-AdapterOnline -Name $activeAdapter.Name -TimeoutSeconds 45
        if ($sameAdapterAfter) {
            Write-Log "Adapter back online: $($sameAdapterAfter.Name) | $($sameAdapterAfter.InterfaceDescription)" Green
        }
        else {
            Write-Log "WARNING: Preferred adapter did not come back online within timeout: $($activeAdapter.Name)" Yellow
            Write-Log 'Check Ethernet cable/router port, then run Get-NetAdapter.'
        }
    }
    else {
        Write-Log 'Skipped adapter restart because -SkipAdapterRestart was selected.' Yellow
    }

    Export-NetworkSnapshot -Phase 'AFTER'
    Test-IPv6TunnelState

    Write-Section "POST-REFRESH CONNECTIVITY TEST"
    Test-NetworkTargets -Targets $PingTargets -Count $PingCount

    if ($RunDnsBenchmark) {
        Test-DnsResolvers -Servers $DnsBenchmarkServers -Domain $DnsDomain -Count $DnsCount
    }

    Write-Section "NEXT ACTIONS"
    Write-Log '1. Keep router QoS OFF unless the Apex dashboard proves jitter under load.'
    Write-Log '2. Keep UPnP ON, WMM ON, DMZ OFF.'
    Write-Log '3. Keep IPv6/6to4 2002: entries removed for the current Apex baseline.'
    Write-Log '4. Preferred DNS from your local test: 1.1.1.1 primary, 1.0.0.1 secondary.'
    Write-Log '5. Launch Apex and monitor through the FalseTech Apex Dashboard.'
    Write-Log '6. Watch for packet loss, prediction error, choke, and repeated score below 90.'
    Write-Log '7. If only one match is bad while monitor stays Elite, likely Apex server-side.'
    Write-Log '8. If -FullReset was used, reboot before the next Apex session.'

    Write-Section "COMPLETE"
    Write-Log 'Finished successfully.' Green
    Write-Log "Log saved to: $LogFile"

    if ($RestartComputer) {
        Write-Log 'RestartComputer switch detected. Rebooting in 10 seconds...' Yellow
        shutdown.exe /r /t 10 /c 'FalseTech Network Refresh completed. Rebooting to finalize network reset.'
    }
    else {
        Write-Log 'No automatic reboot selected.'
        if ($FullReset) {
            Write-Log 'Recommended: reboot the PC before your next Apex session because -FullReset was used.' Yellow
        }
    }
}
catch {
    $msg = $_.Exception.Message
    Write-Host "`nERROR: $msg" -ForegroundColor Red

    if ($script:LogFile) {
        Add-Content -Path $script:LogFile -Value "`nERROR: $msg"
        Write-Host "See log: $script:LogFile" -ForegroundColor Yellow
    }

    exit 1
}


