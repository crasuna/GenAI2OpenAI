$ErrorActionPreference = 'Stop'
$taskName = 'GenAI2OpenAI-Local'
$projectRoot = $PSScriptRoot
$python = Join-Path $projectRoot '.venv\Scripts\pythonw.exe'
$runner = Join-Path $projectRoot 'run_managed.py'
if (!(Test-Path -LiteralPath $python)) { throw "Python runtime missing: $python" }
$account = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$action = New-ScheduledTaskAction -Execute $python -Argument ('"' + $runner + '"') -WorkingDirectory $projectRoot
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $account
$principal = New-ScheduledTaskPrincipal -UserId $account -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description 'Local GenAI proxy. Start at user logon; recover on exit. Listen only on 127.0.0.1:5057.' -Force | Out-Null
Write-Output "Registered $taskName for $account. No password stored; no elevated runtime privileges."
Write-Output "Start: Start-ScheduledTask -TaskName '$taskName'"
Write-Output "Disable autostart: Disable-ScheduledTask -TaskName '$taskName'"
