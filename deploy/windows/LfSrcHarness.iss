#define AppName "LfSrcHarness"
#define AppVersion "0.1.1-preview"

[Setup]
AppId=LfSrcHarness.Desktop
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=ZC-kf
AppPublisherURL=https://github.com/ZC-kf/LfSrcHarness
DefaultDirName={localappdata}\Programs\LfSrcHarness
DefaultGroupName=LfSrcHarness
DisableDirPage=no
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
OutputDir=..\..\package
OutputBaseFilename=LfSrcHarness-Windows-Setup-preview
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\LfSrcHarness.exe

[Languages]
Name: "chinesesimp"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Files]
Source: "..\..\package\LfSrcHarness-Desktop-Preview\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "VerifyMicrosoftSignature.ps1"; Flags: dontcopy noencryption

[Icons]
Name: "{group}\LfSrcHarness"; Filename: "{app}\LfSrcHarness.exe"
Name: "{userdesktop}\LfSrcHarness"; Filename: "{app}\LfSrcHarness.exe"

[Run]
Filename: "{app}\LfSrcHarness.exe"; Description: "启动 LfSrcHarness"; Flags: nowait postinstall skipifsilent

[Code]
const
  WebView2Client = 'Software\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';
  DotNetFull = 'SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full';
  DotNetUrl = 'https://go.microsoft.com/fwlink/?LinkId=2085155';
  WebView2Url = 'https://go.microsoft.com/fwlink/p/?LinkId=2124703';

function OnDownloadProgress(const Url, FileName: String;
  const Progress, ProgressMax: Int64): Boolean;
begin
  Result := True;
end;

function VerifyMicrosoftSignature(const FileName: String): Boolean;
var
  ExitCode: Integer;
begin
  ExtractTemporaryFile('VerifyMicrosoftSignature.ps1');
  Result := Exec(
    ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'),
    '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' +
    ExpandConstant('{tmp}\VerifyMicrosoftSignature.ps1') +
    '" -InstallerPath "' + ExpandConstant('{tmp}\' + FileName) + '"',
    '', SW_HIDE, ewWaitUntilTerminated, ExitCode) and (ExitCode = 0);
end;

function FetchMicrosoftInstaller(const Url, FileName: String): Boolean;
begin
  Result := False;
  try
    DownloadTemporaryFile(Url, FileName, '', @OnDownloadProgress);
    Result := VerifyMicrosoftSignature(FileName);
  except
    Log(GetExceptionMessage);
  end;
end;

function HasDotNet: Boolean;
var
  Release: Cardinal;
begin
  Result := False;
  if IsWin64 then
    Result := RegQueryDWordValue(HKLM64, DotNetFull, 'Release', Release) and
      (Release >= 394802);
  if not Result then
    Result := RegQueryDWordValue(HKLM32, DotNetFull, 'Release', Release) and
      (Release >= 394802);
end;

function HasWebView2: Boolean;
var
  Version: String;
begin
  Result := RegQueryStringValue(HKLM32, WebView2Client, 'pv', Version) and
    (Version <> '') and (Version <> '0.0.0.0');
  if not Result then
    Result := RegQueryStringValue(HKCU, WebView2Client, 'pv', Version) and
      (Version <> '') and (Version <> '0.0.0.0');
  if IsWin64 and not Result then
    Result := RegQueryStringValue(HKLM64, WebView2Client, 'pv', Version) and
      (Version <> '') and (Version <> '0.0.0.0');
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ExitCode, Attempt: Integer;
begin
  Result := '';
  if not IsWin64 then
  begin
    Result := '此版本需要 64 位 Windows。请下载适合系统架构的发行包。';
    Exit;
  end;
  if not HasDotNet then
  begin
    if MsgBox(
      '检测到缺少 .NET Framework 4.6.2 或更新版本。' + #13#10 +
      '接下来会启动微软签名的 .NET Framework 4.8 安装程序，联网补齐后继续安装。',
      mbConfirmation, MB_OKCANCEL) <> IDOK then
    begin
      Result := '.NET Framework 是桌面界面的必要组件；本次安装已暂停。';
      Exit;
    end;
    if not FetchMicrosoftInstaller(DotNetUrl, 'NDP48-web.exe') then
    begin
      Result := '无法从微软下载或验证 .NET Framework 安装程序。请检查网络，或从微软官网下载后重试。';
      Exit;
    end;
    if not Exec(ExpandConstant('{tmp}\NDP48-web.exe'),
      '/passive /norestart', '', SW_SHOW, ewWaitUntilTerminated, ExitCode) then
    begin
      Result := '无法启动微软 .NET Framework 安装程序。请检查网络或从微软官网下载后重试。';
      Exit;
    end;
    if ExitCode = 3010 then
    begin
      NeedsRestart := True;
      Result := '.NET Framework 安装后需要重启 Windows；重启后请重新运行安装包。';
      Exit;
    end;
    for Attempt := 1 to 10 do
    begin
      if HasDotNet then Break;
      Sleep(1000);
    end;
    if not HasDotNet then
    begin
      Result := '.NET Framework 尚未安装成功。请完成微软安装向导后重新运行安装包。';
      Exit;
    end;
  end;
  if HasWebView2 then
    Exit;
  if MsgBox(
    '检测到缺少 Microsoft Edge WebView2 Runtime。' + #13#10 +
    '接下来会启动微软签名的安装程序，由它联网下载所需组件。' + #13#10 +
    '请完成微软安装向导，之后 LfSrcHarness 将继续安装。',
    mbConfirmation, MB_OKCANCEL) <> IDOK then
  begin
    Result := 'WebView2 是桌面界面的必要组件；本次安装已暂停。';
    Exit;
  end;
  if not FetchMicrosoftInstaller(WebView2Url, 'MicrosoftEdgeWebview2Setup.exe') then
  begin
    Result := '无法从微软下载或验证 WebView2 安装程序。请检查网络，或从微软官网下载后重试。';
    Exit;
  end;
  if not Exec(ExpandConstant('{tmp}\MicrosoftEdgeWebview2Setup.exe'),
    '/install', '', SW_SHOW, ewWaitUntilTerminated, ExitCode) then
  begin
    Result := '无法启动微软 WebView2 安装程序。请检查网络或从微软官网下载后重试。';
    Exit;
  end;
  for Attempt := 1 to 10 do
  begin
    if HasWebView2 then
      Exit;
    Sleep(1000);
  end;
  Result := 'WebView2 尚未安装成功。请检查网络、完成微软安装向导后重新运行安装包。';
end;
