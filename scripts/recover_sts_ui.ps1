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
    [int]$StepDelayMilliseconds = 900
)

$ErrorActionPreference = "Stop"

$delegate = Join-Path $PSScriptRoot "recover_sts_menu_flow.ps1"
if (-not (Test-Path -LiteralPath $delegate)) {
    [Console]::Error.WriteLine("[recover-sts-ui] Missing delegate script: $delegate")
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

& $delegate @delegateArgs
exit $LASTEXITCODE
