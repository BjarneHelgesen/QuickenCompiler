; Inno Setup Script for QuickenCL
; Build with: iscc setup.iss
; Version is read from VERSION file automatically

#define VerFile FileOpen("VERSION")
#define AppVersion Trim(FileRead(VerFile))
#expr FileClose(VerFile)

[Setup]
AppId={{B8F3A2E1-5C7D-4E9F-A1B2-3C4D5E6F7890}
AppName=QuickenCL
AppVersion={#AppVersion}
AppPublisher=QuickenCompiler
DefaultDirName={autopf}\QuickenCL
DefaultGroupName=QuickenCL
OutputDir=.
OutputBaseFilename=QuickenCL_Setup
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=admin
UsePreviousAppDir=yes
DisableProgramGroupPage=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
ChangesEnvironment=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Messages]
FinishedLabel=QuickenCL has been installed.%n%nQuickenToolsConfig will run to auto-detect your Visual Studio installation and configure tools.json.%n%nNote: If you added QuickenCL to PATH, open a new command prompt to use it.

[Tasks]
Name: "addtopath"; Description: "Add QuickenCL to system PATH"; GroupDescription: "Environment:"; Flags: checkedonce

[Files]
Source: "dist\QuickenCL.dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Uninstall QuickenCL"; Filename: "{uninstallexe}"

[Run]
; Run QuickenToolsConfig to auto-detect Visual Studio and generate tools.json
Filename: "{app}\QuickenToolsConfig.exe"; \
  Description: "Configure tool paths (Visual Studio auto-detection)"; \
  Flags: postinstall skipifsilent nowait

[Registry]
; Store install path for tools that need to find QuickenCL
Root: HKLM; Subkey: "Software\QuickenCL"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: uninsdeletekey

[Code]
var
  PreviousInstallPath: String;

const
  EnvironmentKey = 'SYSTEM\CurrentControlSet\Control\Session Manager\Environment';
  UserEnvironmentKey = 'Environment';

// Check if AppDir is a complete entry in semicolon-delimited Path string
function IsInPath(const Path, AppDir: String): Boolean;
begin
  Result := (CompareText(Path, AppDir) = 0) or
            (Pos(';' + Uppercase(AppDir) + ';', ';' + Uppercase(Path) + ';') > 0);
end;

procedure AddToPath();
var
  OldPath: String;
begin
  if not RegQueryStringValue(HKLM, EnvironmentKey, 'Path', OldPath) then
    OldPath := '';

  // Check if already in PATH (exact entry match, case-insensitive)
  if IsInPath(OldPath, ExpandConstant('{app}')) then
    Exit;

  // Strip trailing semicolons to avoid creating ;;
  while (Length(OldPath) > 0) and (OldPath[Length(OldPath)] = ';') do
    OldPath := Copy(OldPath, 1, Length(OldPath) - 1);

  // Append to PATH
  if OldPath <> '' then
    RegWriteExpandStringValue(HKLM, EnvironmentKey, 'Path', OldPath + ';' + ExpandConstant('{app}'))
  else
    RegWriteExpandStringValue(HKLM, EnvironmentKey, 'Path', ExpandConstant('{app}'));
end;

// Remove all occurrences of AppDir from a PATH string and clean up semicolons.
// Returns the cleaned PATH, or empty string if nothing remains.
function CleanPathString(const PathValue, AppDir: String): String;
var
  NewPath: String;
  UpperDir: String;
  P: Integer;
begin
  // Wrap in semicolons so every entry is delimited on both sides
  NewPath := ';' + PathValue + ';';
  UpperDir := Uppercase(AppDir);

  // Remove all occurrences of ;APPDIR; (replace with single ;)
  P := Pos(';' + UpperDir + ';', Uppercase(NewPath));
  while P > 0 do
  begin
    Delete(NewPath, P + 1, Length(AppDir) + 1);
    P := Pos(';' + UpperDir + ';', Uppercase(NewPath));
  end;

  // Also match entries with trailing backslash: ;APPDIR\;
  P := Pos(';' + UpperDir + '\;', Uppercase(NewPath));
  while P > 0 do
  begin
    Delete(NewPath, P + 1, Length(AppDir) + 2);
    P := Pos(';' + UpperDir + '\;', Uppercase(NewPath));
  end;

  // Strip the wrapping semicolons we added
  NewPath := Copy(NewPath, 2, Length(NewPath) - 2);

  // Clean up any double semicolons
  P := Pos(';;', NewPath);
  while P > 0 do
  begin
    Delete(NewPath, P, 1);
    P := Pos(';;', NewPath);
  end;

  // Remove leading/trailing semicolons
  if (Length(NewPath) > 0) and (NewPath[1] = ';') then
    NewPath := Copy(NewPath, 2, Length(NewPath) - 1);
  if (Length(NewPath) > 0) and (NewPath[Length(NewPath)] = ';') then
    NewPath := Copy(NewPath, 1, Length(NewPath) - 1);

  Result := NewPath;
end;

procedure RemoveFromPath();
var
  OldPath: String;
  NewPath: String;
  AppDir: String;
begin
  AppDir := ExpandConstant('{app}');

  // Clean system PATH (HKLM)
  if RegQueryStringValue(HKLM, EnvironmentKey, 'Path', OldPath) then
  begin
    NewPath := CleanPathString(OldPath, AppDir);
    if NewPath <> OldPath then
      RegWriteExpandStringValue(HKLM, EnvironmentKey, 'Path', NewPath);
  end;

  // Clean user PATH (HKCU) — in case it was duplicated there
  if RegQueryStringValue(HKCU, UserEnvironmentKey, 'Path', OldPath) then
  begin
    NewPath := CleanPathString(OldPath, AppDir);
    if NewPath <> OldPath then
      RegWriteExpandStringValue(HKCU, UserEnvironmentKey, 'Path', NewPath);
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    if WizardIsTaskSelected('addtopath') then
      AddToPath();
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
    RemoveFromPath();
end;

function InitializeSetup(): Boolean;
var
  PrevPath: String;
begin
  Result := True;
  PreviousInstallPath := '';
  // Check for previous installation
  if RegQueryStringValue(HKLM, 'Software\QuickenCL', 'InstallPath', PrevPath) then
  begin
    if DirExists(PrevPath) then
      PreviousInstallPath := PrevPath;
  end;
end;

function UpdateReadyMemo(Space, NewLine, MemoUserInfoInfo, MemoDirInfo, MemoTypeInfo, MemoComponentsInfo, MemoGroupInfo, MemoTasksInfo: String): String;
begin
  Result := '';
  if PreviousInstallPath <> '' then
    Result := Result + 'Upgrading existing installation at:' + NewLine + Space + PreviousInstallPath + NewLine + NewLine;
  if MemoDirInfo <> '' then
    Result := Result + MemoDirInfo + NewLine + NewLine;
  if MemoTasksInfo <> '' then
    Result := Result + MemoTasksInfo + NewLine + NewLine;
  Result := Result + 'After installation:' + NewLine;
  Result := Result + Space + 'QuickenToolsConfig will auto-detect your Visual Studio installation' + NewLine;
  Result := Result + Space + 'and configure tools.json automatically.';
end;
