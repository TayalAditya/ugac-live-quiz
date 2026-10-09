param(
    [Parameter(Mandatory = $true)]
    [string]$HostName,

    [Parameter(Mandatory = $true)]
    [string]$UserName,

    [string]$Branch = 'deploy/ugac',
    [string]$RemoteDirectory = ''
)

$ErrorActionPreference = 'Stop'

if (-not (Get-Command ssh -ErrorAction SilentlyContinue)) {
    throw 'OpenSSH client is not installed. Install it with: Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0'
}

$environmentArguments = "REPOSITORY_URL='https://github.com/TayalAditya/ugac-live-quiz.git' BRANCH='$Branch'"
if ($RemoteDirectory) {
    $environmentArguments += " APP_DIR='$RemoteDirectory'"
}

$remoteCommand = "$environmentArguments bash -s"
$bootstrapScript = Join-Path $PSScriptRoot 'server-bootstrap.sh'

Get-Content -Raw $bootstrapScript | ssh "$UserName@$HostName" $remoteCommand
