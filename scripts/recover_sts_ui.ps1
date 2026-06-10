<#
.SYNOPSIS
Recover common Slay the Spire UI stalls during live AI batches.

.DESCRIPTION
Canonical entry point for small UI recovery actions that unblock
CommunicationMod validation batches without restarting the game. The default
action clicks the combat End Turn button, matching the revive-animation stuck
state observed during live play. Talk/confirm recovery handles bottom-left
combat dialog buttons. Menu recovery is still available through -Action MenuFlow
and is delegated to recover_sts_menu_flow.ps1.

Use -CaptureBefore and -CaptureAfter to keep screenshots next to the recovery
attempt. This is useful when a click fixes the game state and the visible stall
would otherwise be lost from the evidence trail.

Use -DryRun first to confirm the target window and scaled coordinates before
clicking in the live desktop session.

.EXAMPLE
scripts\recover_sts_ui.ps1 -DryRun

.EXAMPLE
scripts\recover_sts_ui.ps1

.EXAMPLE
scripts\recover_sts_ui.ps1 -Action MenuFlow -StartScreen MainMenu -DryRun

.EXAMPLE
scripts\recover_sts_ui.ps1 -Action Talk -DryRun

.EXAMPLE
scripts\recover_sts_ui.ps1 -Action EndTurn -CaptureBefore -CaptureAfter
#>
[CmdletBinding()]
param(
    [string]$WindowTitlePattern = "Modded Slay the Spire|Slay the Spire",
    [ValidateSet("MenuFlow", "EndTurn", "Talk")]
    [string]$Action = "EndTurn",
    [ValidateSet("MainMenu", "PlayMenu", "CharacterSelect", "IroncladSelected", "PatchNotes")]
    [string]$StartScreen = "MainMenu",
    [switch]$BackFirst,
    [switch]$NoActivate,
    [switch]$DryRun,
    [int]$StepDelayMilliseconds = 900,
    [switch]$CaptureBefore,
    [switch]$CaptureAfter,
    [switch]$CaptureAllScreens,
    [string]$ScreenshotOutputDir = (Join-Path (Split-Path -Parent $PSScriptRoot) "debug_screenshots")
)

$ErrorActionPreference = "Stop"

$delegate = Join-Path $PSScriptRoot "recover_sts_menu_flow.ps1"
if (-not (Test-Path -LiteralPath $delegate)) {
    [Console]::Error.WriteLine("[recover-sts-ui] Missing delegate script: $delegate")
    exit 2
}

$captureScript = Join-Path $PSScriptRoot "capture_sts_screenshot.ps1"
if (($CaptureBefore -or $CaptureAfter) -and -not (Test-Path -LiteralPath $captureScript)) {
    [Console]::Error.WriteLine("[recover-sts-ui] Missing capture script: $captureScript")
    exit 2
}

$delegateArgs = @{
    WindowTitlePattern = $WindowTitlePattern
    Action = $Action
    StartScreen = $StartScreen
    StepDelayMilliseconds = $StepDelayMilliseconds
}

if ($BackFirst) {
    $delegateArgs.BackFirst = $true
}

if ($NoActivate) {
    $delegateArgs.NoActivate = $true
}

if ($DryRun) {
    $delegateArgs.DryRun = $true
}

function Invoke-RecoveryScreenshot {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Phase
    )

    $captureArgs = @(
        "-WindowTitlePattern", $WindowTitlePattern,
        "-OutputDir", $ScreenshotOutputDir
    )
    if ($CaptureAllScreens) {
        $captureArgs += "-AllScreens"
    }
    if ($NoActivate) {
        $captureArgs += "-NoActivate"
    }
    if ($DryRun) {
        $captureArgs += "-DryRun"
    }

    Write-Host "[recover-sts-ui] capture_$Phase"
    & $captureScript @captureArgs
    return $LASTEXITCODE
}

if ($CaptureBefore) {
    $captureResult = Invoke-RecoveryScreenshot -Phase "before"
    if ($captureResult -ne 0) {
        exit $captureResult
    }
}

& $delegate @delegateArgs
$delegateResult = $LASTEXITCODE
if ($delegateResult -ne 0) {
    exit $delegateResult
}

if ($CaptureAfter) {
    $captureResult = Invoke-RecoveryScreenshot -Phase "after"
    if ($captureResult -ne 0) {
        exit $captureResult
    }
}

exit $delegateResult
