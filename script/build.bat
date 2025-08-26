@echo off
setlocal enabledelayedexpansion

set "PYTHON_FILE=zerionyx.py"
set "OUTPUT_DIR=output"
set "EXE_NAME=zerionyx.exe"
set "EXIT_code=0"

if "%1"=="--clean" (
    echo Cleaning output directory...
    if exist "%OUTPUT_DIR%" (
        rmdir /s /q "%OUTPUT_DIR%"
    )
    echo Clean complete.
    goto :end
) else if "%1"=="--help" (
    echo Usage: build.bat [option]
    echo Options:
    echo   --clean      Clean the build directory.
    echo   --install    Build and copy the executable to Python's Scripts directory.
    echo   --uninstall  Remove the executable from Python's Scripts directory.
    echo   --help       Show this help message.
    echo.
    echo If no option is provided, the script will only build the executable locally.
    goto :end
) else if "%1"=="--install" (
    echo Building Zerionyx executable...
    if not exist "%OUTPUT_DIR%" (
        mkdir "%OUTPUT_DIR%"
    )
    nuitka --standalone --onefile --lto=yes --remove-output --output-dir="%OUTPUT_DIR%" --output-filename="%EXE_NAME%" "%PYTHON_FILE%"
    if %errorlevel% neq 0 (
        echo Build failed. Installation aborted.
        set EXIT_code=1
        goto :end
    )
    echo Build successful.
    echo.

    echo Finding Python Scripts directory...
    for /f "delims=" %%I in ('where python') do (
        set "PYTHON_DIR=%%~dpI"
        goto :found_python
    )
    
    echo Error: Could not find Python in your PATH. Cannot determine install location.
    set EXIT_code=1
    goto :end

    :found_python
    set "SCRIPTS_PATH=%PYTHON_DIR%Scripts"
    set "DEST_PATH=%SCRIPTS_PATH%\%EXE_NAME%"

    if not exist "%SCRIPTS_PATH%" (
        echo Error: Python Scripts directory not found at "%SCRIPTS_PATH%".
        set EXIT_code=1
        goto :end
    )

    echo Installing to: "%SCRIPTS_PATH%"
    copy /Y "%OUTPUT_DIR%\%EXE_NAME%" "%DEST_PATH%"
    if %errorlevel% neq 0 (
        echo.
        echo FAILED TO COPY FILE.
        echo Please try running this script as an Administrator.
        set EXIT_code=1
        goto :end
    )

    echo.
    echo Zerionyx was successfully installed!
    echo You can now run 'zerionyx' from any new terminal window.

    rmdir /s /q "%OUTPUT_DIR%"
    goto :end

) else if "%1"=="--uninstall" (
    echo Finding Python Scripts directory to uninstall from...
    for /f "delims=" %%I in ('where python') do (
        set "PYTHON_DIR=%%~dpI"
        goto :found_python_uninstall
    )

    echo Error: Could not find Python in your PATH. Cannot determine uninstall location.
    set EXIT_code=1
    goto :end

    :found_python_uninstall
    set "SCRIPTS_PATH=%PYTHON_DIR%Scripts"
    set "DEST_PATH=%SCRIPTS_PATH%\%EXE_NAME%"

    if exist "%DEST_PATH%" (
        echo Uninstalling "%EXE_NAME%" from "%SCRIPTS_PATH%"...
        del "%DEST_PATH%"
        if %errorlevel% equ 0 (
            echo Zerionyx has been successfully uninstalled.
        ) else (
            echo FAILED TO DELETE FILE.
            echo Please try running this script as an Administrator.
            set EXIT_code=1
        )
    ) else (
        echo Zerionyx is not installed at "%DEST_PATH%". Nothing to do.
    )
    goto :end

) else if "%1"=="" (
    echo Building Zerionyx executable locally...
    if not exist "%OUTPUT_DIR%" (
        mkdir "%OUTPUT_DIR%"
    )
    nuitka --standalone --onefile --lto=yes --remove-output --output-dir="%OUTPUT_DIR%" --output-filename="%EXE_NAME%" "%PYTHON_FILE%"
    echo Build complete. Executable is in "%OUTPUT_DIR%".
    goto :end
) else (
    echo Error: Invalid option "%1".
    echo Use "build.bat --help" to see available options.
    set EXIT_code=1
    goto :end
)

:end
endlocal
exit /b %EXIT_code%