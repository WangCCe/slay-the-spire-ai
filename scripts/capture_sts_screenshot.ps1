param(
    [string]$OutputDir = (Join-Path (Split-Path -Parent $PSScriptRoot) "debug_screenshots"),
    [string]$WindowTitlePattern = "Modded Slay the Spire|Slay the Spire",
    [switch]$AllScreens,
    [switch]$NoActivate,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Write-CaptureInfo {
    param([string]$Message)
    Write-Host "[capture-sts] $Message"
}

Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms

if (-not ("StsCaptureNative" -as [type])) {
    Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;

public struct StsCaptureRect {
    public int Left;
    public int Top;
    public int Right;
    public int Bottom;
}

public static class StsCaptureNative {
    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(IntPtr hWnd, out StsCaptureRect rect);

    [DllImport("user32.dll")]
    public static extern bool ShowWindowAsync(IntPtr hWnd, int nCmdShow);

    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);
}
"@
}

function New-ScreenshotPath {
    param([string]$Directory)

    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss_fff"
    return Join-Path $Directory "sts_screen_$timestamp.png"
}

function Get-AllScreensTarget {
    $screens = [System.Windows.Forms.Screen]::AllScreens
    if (-not $screens -or $screens.Count -eq 0) {
        throw "No display screens are available for capture."
    }

    $left = ($screens | ForEach-Object { $_.Bounds.Left } | Measure-Object -Minimum).Minimum
    $top = ($screens | ForEach-Object { $_.Bounds.Top } | Measure-Object -Minimum).Minimum
    $right = ($screens | ForEach-Object { $_.Bounds.Right } | Measure-Object -Maximum).Maximum
    $bottom = ($screens | ForEach-Object { $_.Bounds.Bottom } | Measure-Object -Maximum).Maximum

    [pscustomobject]@{
        Kind = "all-screens"
        Title = "All screens"
        Left = [int]$left
        Top = [int]$top
        Width = [int]($right - $left)
        Height = [int]($bottom - $top)
    }
}

function Get-WindowTarget {
    param([string]$TitlePattern)

    $window = Get-Process |
        Where-Object {
            $_.MainWindowHandle -ne 0 -and
            $_.MainWindowTitle -match $TitlePattern
        } |
        Sort-Object @{ Expression = { if ($_.MainWindowTitle -match "^Modded Slay the Spire$") { 0 } else { 1 } } }, ProcessName |
        Select-Object -First 1

    if (-not $window) {
        return $null
    }

    $rect = New-Object StsCaptureRect
    $ok = [StsCaptureNative]::GetWindowRect([IntPtr]$window.MainWindowHandle, [ref]$rect)
    if (-not $ok) {
        throw "Could not read window bounds for '$($window.MainWindowTitle)' (PID $($window.Id))."
    }

    [pscustomobject]@{
        Kind = "window"
        Title = $window.MainWindowTitle
        ProcessId = $window.Id
        Handle = [IntPtr]$window.MainWindowHandle
        Left = [int]$rect.Left
        Top = [int]$rect.Top
        Width = [int]($rect.Right - $rect.Left)
        Height = [int]($rect.Bottom - $rect.Top)
    }
}

function Invoke-WindowActivation {
    param([pscustomobject]$Target)

    if ($Target.Kind -ne "window" -or -not $Target.Handle) {
        return
    }

    $swRestore = 9
    [StsCaptureNative]::ShowWindowAsync($Target.Handle, $swRestore) | Out-Null
    [StsCaptureNative]::SetForegroundWindow($Target.Handle) | Out-Null
    Start-Sleep -Milliseconds 350
}

function Save-Screenshot {
    param(
        [pscustomobject]$Target,
        [string]$Path
    )

    if ($Target.Width -le 0 -or $Target.Height -le 0) {
        throw "Invalid capture bounds: $($Target.Width)x$($Target.Height)."
    }

    $bitmap = New-Object System.Drawing.Bitmap($Target.Width, $Target.Height)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    try {
        $graphics.CopyFromScreen($Target.Left, $Target.Top, 0, 0, $bitmap.Size)
        $bitmap.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)
    }
    finally {
        $graphics.Dispose()
        $bitmap.Dispose()
    }
}

$target = if ($AllScreens) {
    Get-AllScreensTarget
}
else {
    Get-WindowTarget -TitlePattern $WindowTitlePattern
}

if (-not $target) {
    [Console]::Error.WriteLine("[capture-sts] No visible window matching pattern '$WindowTitlePattern'. Use -AllScreens to capture desktop context.")
    exit 2
}

$outputPath = New-ScreenshotPath -Directory $OutputDir
$bounds = "left=$($target.Left), top=$($target.Top), width=$($target.Width), height=$($target.Height)"

if ($DryRun) {
    Write-CaptureInfo "dry run: target=$($target.Kind) title='$($target.Title)' $bounds"
    Write-CaptureInfo "would write $outputPath"
    exit 0
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
if (-not $NoActivate) {
    Invoke-WindowActivation -Target $target
}
Save-Screenshot -Target $target -Path $outputPath
Write-CaptureInfo "captured target=$($target.Kind) title='$($target.Title)' $bounds"
Write-CaptureInfo "wrote $outputPath"
Write-Output $outputPath
