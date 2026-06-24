2. ☀️ HDR Competitive Profile
Uses Windows Auto HDR to push OLED brightness, but keeps the game engine completely stripped of shadows and bloom to prevent blinding double-exposure.

Manual Checklist (Do this once)
Windows OS: Settings > Display > Use HDR: ON AND Auto HDR: ON.

Windows OS: Run the Windows HDR Calibration app (from MS Store) to set peak clipping correctly.

Windows OS: Settings > Gaming > Game Mode: ON.

Windows OS: Settings > Display > Graphics > Hardware-Accelerated GPU Scheduling: ON.

Monitor (ASUS): OSD > Image > Uniform Brightness > OFF (Let HDR manage local dimming).

NVCP (3D Settings): Max Frame Rate: 237 FPS | Vertical Sync: ON.

NVCP (Display): G-Sync: ON for Fullscreen | Change Resolution: 10 bpc / RGB / Full.



Deployment Script (Apply-HDR-Comp.ps1)
Deploys the low-clutter engine config so Auto HDR has a clean slate to tone-map.



Write-Host "Deploying HDR Competitive Profile (File-Level Only)..." -ForegroundColor Yellow

$vPath = "$env:USERPROFILE\\Saved Games\\Respawn\\Apex\\local\\videoconfig.txt"
$aPath = "C:\\Program Files (x86)\\Steam\\steamapps\\common\\Apex Legends\\cfg\\autoexec.cfg"

$video = @"
"VideoConfig"
{
"setting.cl\_gib\_allow" "0"
"setting.cl\_particle\_fallback\_base" "0"
"setting.cl\_particle\_fallback\_multiplier" "1"
"setting.cl\_ragdoll\_maxcount" "0"
"setting.cl\_ragdoll\_self\_collision" "0"
"setting.mat\_forceaniso" "16"
"setting.mat\_mip\_linear" "1"
"setting.stream\_memory" "8388608"
"setting.mat\_picmip" "1"
"setting.particle\_cpu\_level" "0"
"setting.r\_createmodeldecals" "0"
"setting.r\_decals" "0"
"setting.r\_lod\_switch\_scale" "2"
"setting.shadow\_enable" "0"
"setting.shadow\_depth\_dimen\_min" "0"
"setting.shadow\_depth\_upres\_factor\_max" "0"
"setting.shadow\_maxdynamic" "0"
"setting.dvs\_enable" "0"
"setting.dvs\_gpuframetime\_min" "15000"
"setting.dvs\_gpuframetime\_max" "16500"
"setting.sound\_volume" "1.000000"
"setting.last\_display\_width" "2560"
"setting.last\_display\_height" "1440"
"setting.nowindowborder" "0"
"setting.fullscreen" "1"
"setting.defaultres" "2560"
"setting.defaultresheight" "1440"
"setting.volumetric\_lighting" "0"
"setting.volumetric\_fog" "0"
"setting.mat\_vsync\_mode" "0"
"setting.mat\_backbuffer\_count" "1"
"setting.mat\_antialias\_mode" "12"
"setting.csm\_enabled" "0"
"setting.csm\_coverage" "0"
"setting.csm\_cascade\_res" "0"
"setting.fadeDistScale" "1.000000"
"setting.new\_shadow\_settings" "0"
"setting.dynamic\_streaming\_budget" "0"
"setting.gamma" "1.006032"
"setting.configversion" "10"
"setting.map\_detail\_level" "2"
"setting.ssao\_quality" "0"
"setting.mat\_disable\_bloom" "1"
"setting.reflex\_mode" "2"
}


"@

$autoexec = @"
m\_rawinput "1"
m\_customaccel "0"
cl\_updaterate "60"
cl\_interp\_ratio "2"
cl\_interp "0"
hud\_setting\_minimapRotate "1"
player\_setting\_enable\_fovSlider "1"
fov\_desired "110"
"@

if(Test-Path $vPath){ Set-ItemProperty -Path $vPath -Name IsReadOnly -Value $false }
Set-Content -Path $vPath -Value $video -Encoding UTF8
Set-ItemProperty -Path $vPath -Name IsReadOnly -Value $true
if(Test-Path $(Split-Path $aPath)){ Set-Content -Path $aPath -Value $autoexec -Encoding UTF8 }

Write-Host "HDR Comp deployed and locked." -ForegroundColor Green
Write-Host "Ensure Windows HDR \& Auto HDR are ON in Windows Settings before launching." -ForegroundColor Yellow
Start-Sleep -s 4

