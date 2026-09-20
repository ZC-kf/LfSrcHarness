param(
  [ValidateSet('Check', 'Install')][string]$Mode = 'Check',
  [Parameter(Mandatory=$true)][string]$InstallRoot,
  [string]$NmapExecutable = '',
  [string]$MetasploitExecutable = '',
  [switch]$Offline
)

$ErrorActionPreference = 'Stop'

function Find-Component([string]$Override, [string]$CommandName, [string[]]$Candidates) {
  if ($Override -ne '') {
    if (Test-Path -LiteralPath $Override -PathType Leaf) {
      return [System.IO.Path]::GetFullPath($Override)
    }
    return $null
  }
  $command = Get-Command $CommandName -ErrorAction SilentlyContinue
  if ($command -and (Test-Path -LiteralPath $command.Source -PathType Leaf)) {
    return $command.Source
  }
  foreach ($candidate in $Candidates) {
    if ($candidate -and (Test-Path -LiteralPath $candidate -PathType Leaf)) {
      return [System.IO.Path]::GetFullPath($candidate)
    }
  }
  return $null
}

function Get-UninstallCandidates([string]$NamePattern, [string]$RelativeExecutable) {
  $keys = @(
    'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*',
    'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*',
    'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*'
  )
  foreach ($entry in @(Get-ItemProperty -Path $keys -ErrorAction SilentlyContinue)) {
    if ($entry.DisplayName -match $NamePattern -and $entry.InstallLocation) {
      Join-Path $entry.InstallLocation $RelativeExecutable
    }
  }
}

function Get-ComponentStatus {
  $nmapCandidates = @(
    (Join-Path $InstallRoot 'tools\nmap\nmap.exe'),
    (Join-Path ${env:ProgramFiles(x86)} 'Nmap\nmap.exe'),
    (Join-Path $env:ProgramFiles 'Nmap\nmap.exe')
  ) + @(Get-UninstallCandidates '^Nmap(\s|$)' 'nmap.exe')
  $metasploitCandidates = @(
    (Join-Path $InstallRoot 'tools\metasploit\bin\msfconsole.bat'),
    (Join-Path $InstallRoot 'tools\metasploit\msfconsole.bat'),
    (Join-Path $env:ProgramFiles 'Metasploit-framework\bin\msfconsole.bat'),
    'C:\metasploit-framework\bin\msfconsole.bat',
    'C:\metasploit-framework\msfconsole.bat'
  ) + @(Get-UninstallCandidates 'Metasploit Framework' 'bin\msfconsole.bat') +
    @(Get-UninstallCandidates 'Metasploit Framework' 'msfconsole.bat')
  $nmapPath = Find-Component $NmapExecutable 'nmap.exe' $nmapCandidates
  $metasploitPath = Find-Component $MetasploitExecutable 'msfconsole.bat' $metasploitCandidates
  return [ordered]@{
    metasploit = [ordered]@{ ready = [bool]$metasploitPath; path = $metasploitPath }
    nmap = [ordered]@{ ready = [bool]$nmapPath; path = $nmapPath }
  }
}

function Save-OfficialInstaller([string]$Uri, [string]$FileName, [string]$PublisherPattern) {
  $downloadRoot = Join-Path $InstallRoot 'tools\downloads'
  New-Item -ItemType Directory -Force -Path $downloadRoot | Out-Null
  $destination = Join-Path $downloadRoot $FileName
  Invoke-WebRequest -UseBasicParsing -Uri $Uri -OutFile $destination
  if ((Get-Item -LiteralPath $destination).Length -eq 0) {
    throw "Empty official installer download: $FileName"
  }
  $signature = Get-AuthenticodeSignature -LiteralPath $destination
  if ($signature.Status -ne 'Valid' -or
      -not $signature.SignerCertificate -or
      $signature.SignerCertificate.Subject -notmatch $PublisherPattern) {
    throw "Publisher signature could not be verified: $FileName"
  }
  return $destination
}

function Start-OfficialInstaller([string]$FileName, [string]$Arguments) {
  $options = @{
    FilePath = $FileName
    Verb = 'RunAs'
    WindowStyle = 'Normal'
    Wait = $true
    PassThru = $true
  }
  if ($Arguments -ne '') { $options.ArgumentList = $Arguments }
  $process = Start-Process @options
  if ($process.ExitCode -notin @(0, 3010)) {
    throw "Official installer returned exit code $($process.ExitCode): $FileName"
  }
}

function Write-InstallLog([string]$Message) {
  $logRoot = Join-Path $InstallRoot 'logs'
  New-Item -ItemType Directory -Force -Path $logRoot | Out-Null
  Add-Content -LiteralPath (Join-Path $logRoot 'official-components.log') `
    -Value ((Get-Date -Format 'o') + ' ' + $Message) -Encoding UTF8
}

$status = Get-ComponentStatus
if ($Mode -eq 'Check') {
  $status | ConvertTo-Json -Depth 3 -Compress
  if ($status.nmap.ready -and $status.metasploit.ready) { exit 0 }
  exit 20
}

if ($status.nmap.ready -and $status.metasploit.ready) {
  $status | ConvertTo-Json -Depth 3 -Compress
  exit 0
}
if ($Offline) {
  $missing = @('nmap', 'metasploit') | Where-Object { -not $status[$_].ready }
  [Console]::Error.WriteLine('Missing components while offline: ' + ($missing -join ', '))
  exit 21
}

try {
  if (-not $status.nmap.ready) {
    Write-InstallLog 'Nmap missing; downloading official installer.'
    $installer = Save-OfficialInstaller 'https://nmap.org/dist/nmap-7.991-setup.exe' `
      'nmap-7.991-setup.exe' 'Nmap|Insecure'
    Start-OfficialInstaller $installer ''
    Write-InstallLog 'Nmap vendor installer finished.'
  }
  if (-not $status.metasploit.ready) {
    Write-InstallLog 'Metasploit Framework missing; downloading official installer.'
    $installer = Save-OfficialInstaller `
      'https://windows.metasploit.com/metasploitframework-latest.msi' `
      'metasploitframework-latest.msi' 'Rapid7'
    $destination = Join-Path $InstallRoot 'tools\metasploit'
    Start-OfficialInstaller (Join-Path $env:SystemRoot 'System32\msiexec.exe') `
      ('/i "' + $installer + '" INSTALLLOCATION="' + $destination + '"')
    Write-InstallLog 'Metasploit vendor installer finished.'
  }
  $status = Get-ComponentStatus
  $status | ConvertTo-Json -Depth 3 -Compress
  if ($status.nmap.ready -and $status.metasploit.ready) {
    Write-InstallLog 'All configured components detected.'
    exit 0
  }
  Write-InstallLog 'A component was not detected after the vendor installers finished.'
  [Console]::Error.WriteLine(
    'Vendor installation finished, but a component was not detected. Check its install location.'
  )
  exit 23
} catch {
  Write-InstallLog ('Installation failed: ' + $_.Exception.Message)
  [Console]::Error.WriteLine($_.Exception.Message)
  exit 22
}
