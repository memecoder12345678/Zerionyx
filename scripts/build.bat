@echo off
setlocal
set "PYTHON_FILE=zerionyx.py"
set "OUTPUT_DIR=output"
set EXIT_code=0
if "%1"=="--clean" (
	if exist "%OUTPUT_DIR%" (
		rmdir /s /q "%OUTPUT_DIR%"
	)
	goto :end
) else if "%1"=="--help" (
	echo Usage: build.bat [option]
	echo Options:
	echo   --clean    Clean the output directory.
	echo   --help     Show this help message.
	echo.
	echo If no option is provided, the script will build the Python file.
	goto :end
) else if "%1"=="" (
	if not exist "%OUTPUT_DIR%" (
		mkdir "%OUTPUT_DIR%"
	)
	nuitka --standalone --onefile --lto=yes --remove-output --output-dir="%OUTPUT_DIR%" "%PYTHON_FILE%"
    echo WARNING: This script only creates executable files. To be able to call them, you need to add them to your PATH.
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
