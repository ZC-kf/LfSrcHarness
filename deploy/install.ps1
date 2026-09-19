param([string]$Root = "", [switch]$CopyOnly)
$ErrorActionPreference = 'Stop'
$SourceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
if ([string]::IsNullOrWhiteSpace($Root)) { $Root = $SourceRoot }
$InstallRoot = [System.IO.Path]::GetFullPath($Root)

if ($InstallRoot -ne $SourceRoot) {
  New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null
  $SourceDirectories = @('src', 'docs', 'plugins/examples', 'plugins/template',
    'deploy/ansible', 'deploy/k8s', 'deploy/systemd', 'deploy/windows', 'web/src')
  $SourceFiles = @('pyproject.toml', 'uv.lock', 'README.md', 'LICENSE.md',
    'plugins/scope.example.yaml', 'deploy/.env.example', 'deploy/Dockerfile',
    'deploy/Vagrantfile', 'deploy/config/config.yaml', 'deploy/config/scope.yaml',
    'deploy/desktop_entry.py', 'deploy/docker-compose.yml', 'deploy/install.ps1',
    'deploy/install.sh', 'deploy/pyinstaller_entry.py', 'web/index.html',
    'web/package.json', 'web/package-lock.json', 'web/tsconfig.app.json',
    'web/tsconfig.json', 'web/tsconfig.node.json', 'web/vite.config.ts')
  if (Test-Path -LiteralPath (Join-Path $SourceRoot 'web/dist')) {
    $SourceDirectories += 'web/dist'
  }
  foreach ($RelativePath in $SourceDirectories + $SourceFiles) {
    $From = Join-Path $SourceRoot $RelativePath
    if (-not (Test-Path -LiteralPath $From)) { continue }
    $To = Join-Path $InstallRoot $RelativePath
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $To) | Out-Null
    Copy-Item -LiteralPath $From -Destination $To -Recurse -Force
  }
}
if ($CopyOnly) { return }

$Python = 'python'
& $Python -m venv (Join-Path $InstallRoot '.venv')
$VenvPython = Join-Path $InstallRoot '.venv\Scripts\python.exe'
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install $InstallRoot

$WebRoot = Join-Path $InstallRoot 'web'
if (Get-Command npm -ErrorAction SilentlyContinue) {
  Push-Location $WebRoot
  try { npm ci; npm run build } finally { Pop-Location }
}

New-Item -ItemType Directory -Force -Path (Join-Path $InstallRoot 'runs'), (Join-Path $InstallRoot 'package') | Out-Null
$EnvFile = Join-Path $InstallRoot 'deploy\.env'
if (-not (Test-Path -LiteralPath $EnvFile)) {
  Copy-Item -LiteralPath (Join-Path $InstallRoot 'deploy\.env.example') -Destination $EnvFile
}
Write-Host "LfSrcHarness installed at $InstallRoot"
