@echo off
REM ============================================================================
REM  UE Bridge - Legacy Python Setup Helper
REM  Automatically finds UE engine's built-in Python, creates a venv,
REM  and installs the Python package. No external Python installation required.
REM
REM  This helper is not the preferred installation path. The AI-first path is:
REM    1. install the plugin
REM    2. run ue-bridge doctor
REM    3. run ue-bridge verify
REM    4. optionally run the repo-contained integration script
REM ============================================================================

setlocal EnableDelayedExpansion

set "PLUGIN_DIR=%~dp0"
set "PYTHON_DIR=%PLUGIN_DIR%Python"
set "VENV_DIR=%PYTHON_DIR%\.venv"
REM ProjectRoot = go up two levels from Plugins/UEBridgeEditor
for %%I in ("%PLUGIN_DIR%..\..\") do set "PROJECT_ROOT=%%~fI"

echo ============================================
echo  UE Bridge - Legacy Python Setup Helper
echo ============================================
echo.

REM --- Step 1: Find UE Engine Python ---
echo [1/4] Searching for Unreal Engine Python...

set "UE_PYTHON="

REM --- Priority 1: Command-line argument ---
if not "%~1"=="" (
    if exist "%~1\Engine\Binaries\ThirdParty\Python3\Win64\python.exe" (
        set "UE_PYTHON=%~1\Engine\Binaries\ThirdParty\Python3\Win64\python.exe"
        echo   [param] !UE_PYTHON!
        goto :found_python
    )
)

REM --- Priority 2: Read .uproject EngineAssociation → Registry ---
REM Find .uproject file
for %%F in ("%PROJECT_ROOT%\*.uproject") do (
    REM Extract EngineAssociation value (simple text parsing)
    for /f "tokens=2 delims=:," %%A in ('findstr /i "EngineAssociation" "%%F" 2^>nul') do (
        set "ENGINE_VER=%%~A"
        REM Trim quotes and spaces
        set "ENGINE_VER=!ENGINE_VER: =!"
        set "ENGINE_VER=!ENGINE_VER:"=!"
        if not "!ENGINE_VER!"=="" (
            echo   Found EngineAssociation: !ENGINE_VER!
            REM Check HKLM registry
            for /f "tokens=2*" %%R in ('reg query "HKLM\SOFTWARE\EpicGames\Unreal Engine\!ENGINE_VER!" /v InstalledDirectory 2^>nul') do (
                set "REG_DIR=%%S"
                if exist "!REG_DIR!\Engine\Binaries\ThirdParty\Python3\Win64\python.exe" (
                    set "UE_PYTHON=!REG_DIR!\Engine\Binaries\ThirdParty\Python3\Win64\python.exe"
                    echo   [registry] !UE_PYTHON!
                    goto :found_python
                )
            )
        )
    )
)

REM --- Priority 3: UE_ENGINE_DIR environment variable ---
if defined UE_ENGINE_DIR (
    if exist "%UE_ENGINE_DIR%\Binaries\ThirdParty\Python3\Win64\python.exe" (
        set "UE_PYTHON=%UE_ENGINE_DIR%\Binaries\ThirdParty\Python3\Win64\python.exe"
        echo   [env] !UE_PYTHON!
        goto :found_python
    )
)

REM --- Priority 4: Scan common disk locations ---
for %%D in (C D E F) do (
    for %%P in (
        "%%D:\EpicGame\UE_5.7"
        "%%D:\EpicGame\UE_5.6"
        "%%D:\EpicGame\UE_5.5"
        "%%D:\Program Files\Epic Games\UE_5.7"
        "%%D:\Program Files\Epic Games\UE_5.6"
        "%%D:\Program Files\Epic Games\UE_5.5"
        "%%D:\UnrealEngine\UE_5.7"
    ) do (
        if exist %%~P\Engine\Binaries\ThirdParty\Python3\Win64\python.exe (
            set "UE_PYTHON=%%~P\Engine\Binaries\ThirdParty\Python3\Win64\python.exe"
            echo   [disk scan] !UE_PYTHON!
            goto :found_python
        )
    )
)

REM --- Priority 5: Ask user ---
echo.
echo   Could not auto-detect UE Engine Python.
echo   Please enter the full path to your UE engine root directory
echo   (e.g., E:\EpicGame\UE_5.7)
echo.
set /p "ENGINE_ROOT=  Engine root path: "
if exist "!ENGINE_ROOT!\Engine\Binaries\ThirdParty\Python3\Win64\python.exe" (
    set "UE_PYTHON=!ENGINE_ROOT!\Engine\Binaries\ThirdParty\Python3\Win64\python.exe"
    echo   Found UE Python: !UE_PYTHON!
    goto :found_python
)

echo.
echo   ERROR: Could not find python.exe at:
echo   !ENGINE_ROOT!\Engine\Binaries\ThirdParty\Python3\Win64\python.exe
pause
exit /b 1

:found_python

REM Show Python version
echo.
for /f "delims=" %%v in ('"!UE_PYTHON!" --version 2^>^&1') do echo   Python version: %%v
echo.

REM --- Step 2: Create virtual environment ---
echo [2/4] Creating virtual environment...

if exist "%VENV_DIR%" (
    echo   Removing existing venv...
    rmdir /s /q "%VENV_DIR%"
)

"!UE_PYTHON!" -m venv "%VENV_DIR%"
if %ERRORLEVEL% neq 0 (
    echo   ERROR: Failed to create virtual environment.
    pause
    exit /b 1
)
echo   Created: %VENV_DIR%
echo.

REM --- Step 3: Install dependencies ---
echo [3/4] Installing Python package...

"%VENV_DIR%\Scripts\pip.exe" install -r "%PYTHON_DIR%\requirements.txt" --quiet
if %ERRORLEVEL% neq 0 (
    echo   ERROR: Failed to install dependencies.
    pause
    exit /b 1
)
echo   Dependencies installed successfully.
echo.

REM --- Step 4: Legacy notice ---
echo [4/4] Legacy helper notice...
echo.
echo   This helper belongs to the older local command-server flow.
echo   It does not generate a valid setup for the current ue-bridge Python library + TCP plugin workflow.
echo   Use README.md and skills\ue_editor_installation.md for the current installation path.
echo   Prefer ue-bridge doctor / verify over manual inspection.
echo.
echo ============================================
echo  Done! No external Python installation needed.
echo  Legacy helper setup generation skipped.
echo ============================================

pause
