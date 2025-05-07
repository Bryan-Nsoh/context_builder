Param()

Write-Host "Starting setup of the Context Builder tool for Windows..."

# Python script name
$pyScriptName = "context_builder.py"
$pyScriptPath = Join-Path $PSScriptRoot $pyScriptName

if (-not (Test-Path $pyScriptPath)) {
    Write-Host "ERROR: Python script '$pyScriptName' not found in the script's directory ('$PSScriptRoot')."
    Write-Host "Please ensure '$pyScriptName' is in the same directory as this setup script."
    exit 1
}

# Check if Python is available
$pythonCheck = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Python is not installed or not on PATH. Please install Python 3 and rerun."
    exit 1
}
Write-Host "Python version: $($pythonCheck -join ' ')"


# Create project directory relative to the script's location for build artifacts
$buildArtifactsDir = Join-Path $PSScriptRoot "ContextBuilder_WindowsBuild"
if (Test-Path $buildArtifactsDir) {
    Write-Host "Removing existing ContextBuilder_WindowsBuild directory: '$buildArtifactsDir'..."
    Remove-Item $buildArtifactsDir -Recurse -Force
}
Write-Host "Creating ContextBuilder_WindowsBuild directory at '$buildArtifactsDir'..."
New-Item -ItemType Directory -Path $buildArtifactsDir | Out-Null

# requirements.txt content
$requirements = @"
requests
pyperclip
pyinstaller
windnd; sys_platform == 'win32' # windnd is Windows-specific
"@
$reqFile = Join-Path $PSScriptRoot "requirements.txt" # Place requirements.txt alongside scripts
Set-Content -Path $reqFile -Value $requirements -Encoding UTF8
Write-Host "Wrote requirements.txt to '$reqFile'"

Write-Host "Creating virtual environment in '$buildArtifactsDir\venv'..."
$venvPath = Join-Path $buildArtifactsDir "venv"
python -m venv $venvPath

Write-Host "Activating virtual environment and installing requirements..."
$pipPath = Join-Path $venvPath "Scripts\pip.exe"
# For installing requirements, we don't need to activate for the whole script,
# just call pip from the venv directly.
& $pipPath install --upgrade pip
& $pipPath install -r $reqFile
$pyInstallerPath = Join-Path $venvPath "Scripts\pyinstaller.exe"


Write-Host "Requirements installed."

Write-Host "Building single-file executable with PyInstaller..."
$distPath = Join-Path $buildArtifactsDir "dist"
$workPathInternal = Join-Path $buildArtifactsDir "build" # PyInstaller's working directory for intermediate files

# PyInstaller command with specified output paths
# --noconsole is good for Windows GUI apps. --windowed is an alternative.
& $pyInstallerPath --onefile --name "context_builder" --noconsole --distpath $distPath --workpath $workPathInternal $pyScriptPath

$exePath = Join-Path $distPath "context_builder.exe"

if (Test-Path $exePath) {
    Write-Host "Build complete."
    Write-Host "--------------------------------------------------------------------"
    Write-Host "Setup complete for Windows!"
    Write-Host "You can find the executable at: '$exePath'"
    Write-Host "To run, navigate to '$distPath' and double-click context_builder.exe."
    Write-Host "You can also create a shortcut to '$exePath' or copy it elsewhere."
    Write-Host "The '$buildArtifactsDir' contains the venv and build files, you only need the .exe from the 'dist' subfolder."
    Write-Host "--------------------------------------------------------------------"
}
else {
    Write-Host "ERROR: Build failed. Executable not found at '$exePath'."
    Write-Host "Check PyInstaller output above for errors."
}