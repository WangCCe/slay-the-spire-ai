<#
.SYNOPSIS
Recover a stuck Slay the Spire main-menu flow for CommunicationMod batches.

.DESCRIPTION
This helper repeats the UI clicks used when a clean batch starts at the game
main menu instead of emitting CommunicationMod state updates. It uses scaled
window-relative coordinates so the same reference points work across DPI-aware
and DPI-virtualized PowerShell sessions.

Run this only after a screenshot confirms the game is on a menu screen, not
during an active run.

.EXAMPLE
scripts\recover_sts_menu_flow.ps1 -DryRun -StartScreen MainMenu

.EXAMPLE
scripts\recover_sts_menu_flow.ps1 -StartScreen MainMenu

.EXAMPLE
scripts\recover_sts_menu_flow.ps1 -StartScreen PatchNotes
#>
[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = "Medium")]
param(
    [string]$WindowTitlePattern = "Modded Slay the Spire|Slay the Spire",
    [ValidateSet("MainMenu", "PlayMenu", "CharacterSelect", "IroncladSelected", "PatchNotes")]
    [string]$StartScreen = "MainMenu",
    [switch]$BackFirst,
    [switch]$NoActivate,
    [switch]$DryRun,
    [int]$StepDelayMilliseconds = 900
)

$ErrorActionPreference = "Stop"

function Write-RecoveryInfo {
    param([string]$Message)
    Write-Host "[recover-sts-menu] $Message"
}

if (-not ("StsMenuRecoveryNative" -as [type])) {
    Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;

public struct StsMenuRecoveryRect {
    public int Left;
    public int Top;
    public int Right;
    public int Bottom;
}

public static class StsMenuRecoveryNative {
    [DllImport("user32.dll")]
    public static extern IntPtr SetProcessDpiAwarenessContext(IntPtr dpiContext);

    [DllImport("user32.dll")]
    public static extern bool SetProcessDPIAware();

    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(IntPtr hWnd, out StsMenuRecoveryRect rect);

    [DllImport("user32.dll")]
    public static extern bool ShowWindowAsync(IntPtr hWnd, int nCmdShow);

    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool SetCursorPos(int X, int Y);

    [DllImport("user32.dll")]
    public static extern void mouse_event(uint dwFlags, uint dx, uint dy, uint dwData, UIntPtr dwExtraInfo);
}
"@
}

function Enable-DpiAwareWindowCoordinates {
    $dpiAwarenessContextPerMonitorAwareV2 = [IntPtr]::new(-4)

    try {
        if ([StsMenuRecoveryNative]::SetProcessDpiAwarenessContext($dpiAwarenessContextPerMonitorAwareV2) -ne [IntPtr]::Zero) {
            return
        }
    }
    catch {
        # Older Windows versions may not expose SetProcessDpiAwarenessContext.
    }

    try {
        [StsMenuRecoveryNative]::SetProcessDPIAware() | Out-Null
    }
    catch {
        Write-RecoveryInfo "warning: could not set process DPI awareness; scaled coordinate fallback will still be used"
    }
}

function Get-StsWindowTarget {
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

    $rect = New-Object StsMenuRecoveryRect
    $ok = [StsMenuRecoveryNative]::GetWindowRect([IntPtr]$window.MainWindowHandle, [ref]$rect)
    if (-not $ok) {
        throw "Could not read window bounds for '$($window.MainWindowTitle)' (PID $($window.Id))."
    }

    [pscustomobject]@{
        Title = $window.MainWindowTitle
        ProcessId = $window.Id
        Handle = [IntPtr]$window.MainWindowHandle
        Left = [int]$rect.Left
        Top = [int]$rect.Top
        Width = [int]($rect.Right - $rect.Left)
        Height = [int]($rect.Bottom - $rect.Top)
    }
}

function Invoke-StsWindowActivation {
    param([pscustomobject]$Target)

    if ($NoActivate) {
        return
    }

    $swRestore = 9
    [StsMenuRecoveryNative]::ShowWindowAsync($Target.Handle, $swRestore) | Out-Null
    [StsMenuRecoveryNative]::SetForegroundWindow($Target.Handle) | Out-Null
    Start-Sleep -Milliseconds 350
}

function Get-ScaledClickPoint {
    param(
        [pscustomobject]$Target,
        [int]$ReferenceX,
        [int]$ReferenceY
    )

    $referenceWidth = 1286.0
    $referenceHeight = 755.0

    [pscustomobject]@{
        X = [int][Math]::Round($Target.Left + ($ReferenceX / $referenceWidth) * $Target.Width)
        Y = [int][Math]::Round($Target.Top + ($ReferenceY / $referenceHeight) * $Target.Height)
    }
}

function Invoke-StsClick {
    param(
        [pscustomobject]$Target,
        [string]$StepName,
        [hashtable]$Point
    )

    $scaled = Get-ScaledClickPoint -Target $Target -ReferenceX $Point.X -ReferenceY $Point.Y
    Write-RecoveryInfo ("step={0} ref=({1},{2}) click=({3},{4})" -f $StepName, $Point.X, $Point.Y, $scaled.X, $scaled.Y)

    if ($DryRun) {
        return
    }

    [StsMenuRecoveryNative]::SetCursorPos($scaled.X, $scaled.Y) | Out-Null
    Start-Sleep -Milliseconds 100
    [StsMenuRecoveryNative]::mouse_event(0x0002, 0, 0, 0, [UIntPtr]::Zero)
    Start-Sleep -Milliseconds 80
    [StsMenuRecoveryNative]::mouse_event(0x0004, 0, 0, 0, [UIntPtr]::Zero)
    Start-Sleep -Milliseconds $StepDelayMilliseconds
}

Enable-DpiAwareWindowCoordinates

$target = Get-StsWindowTarget -TitlePattern $WindowTitlePattern
if (-not $target) {
    [Console]::Error.WriteLine("[recover-sts-menu] No visible window matching pattern '$WindowTitlePattern'.")
    exit 2
}

$bounds = "left=$($target.Left), top=$($target.Top), width=$($target.Width), height=$($target.Height)"
Write-RecoveryInfo "target title='$($target.Title)' pid=$($target.ProcessId) $bounds"
Write-RecoveryInfo "start_screen=$StartScreen back_first=$($BackFirst.IsPresent) dry_run=$($DryRun.IsPresent)"

$points = @{
    Back = @{ X = 95; Y = 629 }
    Play = @{ X = 108; Y = 476 }
    Standard = @{ X = 345; Y = 405 }
    Ironclad = @{ X = 416; Y = 620 }
    Embark = @{ X = 1193; Y = 631 }
}

$sequence = @()
if ($BackFirst -and $StartScreen -ne "PatchNotes") {
    $sequence += "Back"
}

switch ($StartScreen) {
    "MainMenu" {
        $sequence += @("Play", "Standard", "Ironclad", "Embark")
    }
    "PlayMenu" {
        $sequence += @("Standard", "Ironclad", "Embark")
    }
    "CharacterSelect" {
        $sequence += @("Ironclad", "Embark")
    }
    "IroncladSelected" {
        $sequence += @("Embark")
    }
    "PatchNotes" {
        $sequence += @("Back", "Play", "Standard", "Ironclad", "Embark")
    }
}

if ($sequence.Count -eq 0) {
    Write-RecoveryInfo "no steps selected"
    exit 0
}

Write-RecoveryInfo "sequence=$($sequence -join ' -> ')"

if (-not $DryRun -and -not $PSCmdlet.ShouldProcess($target.Title, "click $($sequence -join ' -> ')")) {
    Write-RecoveryInfo "cancelled"
    exit 0
}

Invoke-StsWindowActivation -Target $target

foreach ($step in $sequence) {
    Invoke-StsClick -Target $target -StepName $step -Point $points[$step]
}

if ($DryRun) {
    Write-RecoveryInfo "dry run complete"
}
else {
    Write-RecoveryInfo "menu recovery clicks complete"
}
