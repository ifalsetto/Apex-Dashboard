# FalseTech Apex Process Skill Package

This package extracts the useful process/service rules from the Windows Process Strategy research and turns them into:

1. `ApexGamingPrep.ps1` — safe prep/restore PowerShell script.
2. `FalseTech_Apex_Process_Hygiene.skill.md` — reusable skill/SOP.

## Install

Copy these files into the root of your Apex Dashboard repo:

```powershell
Copy-Item .\ApexGamingPrep.ps1 "C:\Users\andre\Downloads\Apex-Dashboard-0.1.0-security-clean\Apex-Dashboard-0.1.0-security-clean\" -Force
Copy-Item .\FalseTech_Apex_Process_Hygiene.skill.md "C:\Users\andre\Downloads\Apex-Dashboard-0.1.0-security-clean\Apex-Dashboard-0.1.0-security-clean\" -Force
```

## Use

Safe prep:

```powershell
powershell -ExecutionPolicy Bypass -File .\ApexGamingPrep.ps1 -Mode Prep
```

Prep with update suppression and Bluetooth PAN cleanup. Run PowerShell as Administrator:

```powershell
powershell -ExecutionPolicy Bypass -File .\ApexGamingPrep.ps1 -Mode Prep -StopUpdateServices -DisableBluetoothPan
```

Check status:

```powershell
powershell -ExecutionPolicy Bypass -File .\ApexGamingPrep.ps1 -Mode Status
```

Restore:

```powershell
powershell -ExecutionPolicy Bypass -File .\ApexGamingPrep.ps1 -Mode Restore
```

## Safe by design

The script does not target:

- Apex
- anti-cheat
- Defender
- firewall
- DHCP
- DNS
- audio
- NVIDIA display services
- core Windows services

## Recommended after prep

Run the network monitor:

```powershell
python .\optimizer\network\network_monitor.py --target 192.168.1.1 --target 1.1.1.1 --target 8.8.8.8 --interval 5
```
