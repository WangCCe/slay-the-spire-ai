[CmdletBinding()]
param(
    [string]$GameDir = "D:\SteamLibrary\steamapps\common\SlayTheSpire",
    [string]$ProjectRoot = "D:\PycharmProjects\slay-the-spire-ai",
    [string]$ModTheSpireJar = "D:\SteamLibrary\steamapps\workshop\content\646570\1605060445\ModTheSpire.jar",
    [int]$ShutdownWaitSeconds = 4,
    [switch]$DryRun,
    [switch]$SkipLaunch,
    [switch]$UseLauncher
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-MatchText {
    param([object]$Value)

    if ($null -eq $Value) {
        return ""
    }

    return ([string]$Value).Replace("/", "\").ToLowerInvariant()
}

function Get-NormalizedPathForMatch {
    param([string]$Path)

    try {
        return (Get-MatchText (Resolve-Path -LiteralPath $Path -ErrorAction Stop).Path)
    }
    catch {
        return (Get-MatchText $Path)
    }
}

function ShouldStopProjectPython {
    param(
        [object]$Process,
        [string]$NormalizedProjectRoot
    )

    $name = Get-MatchText $Process.Name
    if ($name -ne "python.exe" -and $name -ne "pythonw.exe") {
        return $false
    }

    $commandLine = Get-MatchText $Process.CommandLine
    if (-not $commandLine.Contains($NormalizedProjectRoot)) {
        return $false
    }

    return (
        $commandLine.Contains("\main.py") -or
        $commandLine.Contains("\scripts\run_training_batch.py") -or
        $commandLine.Contains("slay-the-spire-ai")
    )
}

function ShouldStopGameProcess {
    param(
        [object]$Process,
        [string]$NormalizedGameDir
    )

    $name = Get-MatchText $Process.Name
    $commandLine = Get-MatchText $Process.CommandLine
    $executablePath = Get-MatchText $Process.ExecutablePath
    $inGameDir = $commandLine.Contains($NormalizedGameDir) -or $executablePath.Contains($NormalizedGameDir)
    $isModTheSpireCommand = $commandLine.Contains("mts-launcher.jar") -or $commandLine.Contains("modthespire.jar")

    if ($name -eq "slaythespire.exe") {
        return $true
    }

    if (-not $inGameDir -and -not $isModTheSpireCommand) {
        return $false
    }

    if ($name -eq "java.exe" -or $name -eq "javaw.exe") {
        return (
            $isModTheSpireCommand -or
            $commandLine.Contains("desktop-1.0.jar") -or
            $commandLine.Contains("modthespire")
        )
    }

    return $commandLine.Contains("slaythespire") -or $commandLine.Contains("mts-launcher.jar")
}

function Get-RestartTargetProcesses {
    param(
        [string]$NormalizedProjectRoot,
        [string]$NormalizedGameDir
    )

    $allProcesses = Get-CimInstance Win32_Process
    foreach ($process in $allProcesses) {
        if ($null -eq $process.ProcessId -or $process.ProcessId -eq $PID) {
            continue
        }

        if (ShouldStopProjectPython $process $NormalizedProjectRoot) {
            [pscustomobject]@{
                ProcessId = $process.ProcessId
                Kind = "ai-python"
                Name = $process.Name
                CommandLine = $process.CommandLine
            }
            continue
        }

        if (ShouldStopGameProcess $process $NormalizedGameDir) {
            [pscustomobject]@{
                ProcessId = $process.ProcessId
                Kind = "sts-modded"
                Name = $process.Name
                CommandLine = $process.CommandLine
            }
        }
    }
}

function Stop-RestartTargetProcess {
    param(
        [object]$Target,
        [switch]$DryRun
    )

    $label = "PID=$($Target.ProcessId) kind=$($Target.Kind) name=$($Target.Name)"
    if ($DryRun) {
        Write-Host "[restart-sts] DRY RUN would stop $label"
        return
    }

    try {
        Stop-Process -Id $Target.ProcessId -Force -ErrorAction Stop
        Write-Host "[restart-sts] stopped $label"
    }
    catch {
        Write-Warning "[restart-sts] failed to stop $label`: $($_.Exception.Message)"
    }
}

function Find-JavaLauncher {
    param([string]$GameDir)

    $bundledJava = Join-Path $GameDir "jre\bin\javaw.exe"
    if (Test-Path -LiteralPath $bundledJava) {
        return $bundledJava
    }

    $javaw = Get-Command "javaw.exe" -ErrorAction SilentlyContinue
    if ($null -ne $javaw) {
        return $javaw.Source
    }

    $java = Get-Command "java.exe" -ErrorAction SilentlyContinue
    if ($null -ne $java) {
        return $java.Source
    }

    throw "Could not find javaw.exe or java.exe. Expected bundled Java at $bundledJava."
}

function Start-ModTheSpire {
    param(
        [string]$GameDir,
        [string]$ModTheSpireJar,
        [switch]$UseLauncher,
        [switch]$DryRun
    )

    $java = Find-JavaLauncher $GameDir
    if ($UseLauncher) {
        $launcher = Join-Path $GameDir "mts-launcher.jar"
        if (-not (Test-Path -LiteralPath $launcher)) {
            throw "ModTheSpire launcher not found: $launcher"
        }

        if ($DryRun) {
            Write-Host "[restart-sts] DRY RUN would start launcher: `"$java`" -jar `"$launcher`""
            return
        }

        Start-Process -FilePath $java -ArgumentList @("-jar", "`"$launcher`"") -WorkingDirectory $GameDir
        Write-Host "[restart-sts] started ModTheSpire launcher from $launcher"
        return
    }

    if (-not (Test-Path -LiteralPath $ModTheSpireJar)) {
        throw "ModTheSpire.jar not found: $ModTheSpireJar"
    }

    if ($DryRun) {
        Write-Host "[restart-sts] DRY RUN would start direct ModTheSpire: `"$java`" -jar `"$ModTheSpireJar`" --skip-launcher"
        return
    }

    Start-Process -FilePath $java -ArgumentList @("-jar", "`"$ModTheSpireJar`"", "--skip-launcher") -WorkingDirectory $GameDir
    Write-Host "[restart-sts] started ModTheSpire directly from $ModTheSpireJar"
}

$normalizedProjectRoot = Get-NormalizedPathForMatch $ProjectRoot
$normalizedGameDir = Get-NormalizedPathForMatch $GameDir

if ($DryRun) {
    Write-Host "[restart-sts] dry run: no processes will be stopped and no launcher will be started."
}

$targets = @()
try {
    $targets = @(Get-RestartTargetProcesses $normalizedProjectRoot $normalizedGameDir)
}
catch {
    if (-not $DryRun) {
        throw
    }

    Write-Warning "[restart-sts] process scan unavailable during dry run: $($_.Exception.Message)"
}

if ($targets.Count -eq 0) {
    Write-Host "[restart-sts] no matching AI or Slay the Spire processes found."
}
else {
    foreach ($target in $targets) {
        Stop-RestartTargetProcess $target -DryRun:$DryRun
    }
}

if (-not $DryRun -and $targets.Count -gt 0 -and $ShutdownWaitSeconds -gt 0) {
    Start-Sleep -Seconds $ShutdownWaitSeconds
}

if ($SkipLaunch) {
    Write-Host "[restart-sts] launch skipped."
    exit 0
}

Start-ModTheSpire $GameDir $ModTheSpireJar -UseLauncher:$UseLauncher -DryRun:$DryRun
