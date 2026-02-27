@echo off
REM =============================================================================
REM Tulpin Shop - Стартовый скрипт для запуска проекта (Windows)
REM =============================================================================
REM Использование:
REM   start.bat              - полный запуск (миграции + данные + сервер)
REM   start.bat --no-data    - запуск без создания тестовых данных
REM   start.bat --migrate    - только миграции
REM   start.bat --data       - только создание тестовых данных
REM   start.bat --clean      - очистить БД и начать заново
REM =============================================================================

setlocal enabledelayedexpansion

set "PYTHON_CMD=python"
set "ARG=%1"

echo.
echo =================================================
echo         TULPIN SHOP - Startup Script (Windows)
echo =================================================
echo.

REM Проверка Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python ne naiden! Ustanovite Python 3.10+
    exit /b 1
)

echo [INFO] Python: %PYTHON_CMD%
%PYTHON_CMD% --version
echo.

REM Обработка аргументов
if "%ARG%"=="--help" goto help
if "%ARG%"=="--clean" goto clean
if "%ARG%"=="--migrate" goto migrate
if "%ARG%"=="--data" goto data
if "%ARG%"=="--no-data" goto nodata
if "%ARG%"=="" goto full

echo [ERROR] Neizvestnaya optsiya: %ARG%
goto help

:help
echo Tulpin Shop - startovyy skript
echo.
echo Ispol'zovanie:
echo   start.bat              - polnyy zapusk proekta
echo   start.bat --no-data    - zapusk bez testovykh dannykh
echo   start.bat --migrate    - tol'ko migratsii
echo   start.bat --data       - tol'ko testovyye dannyye
echo   start.bat --clean      - ochistit BD i nachat zanovo
echo   start.bat --help       - pokazat' etu spravku
echo.
exit /b 0

:clean
echo [INFO] Ochistka bazy dannykh...
if exist db.sqlite3 del db.sqlite3
echo [OK] Baza dannykh udalena
goto full_after_clean

:full
echo [INFO] Ustanovka zavisimostey...
%PYTHON_CMD% -m pip install -q -r requirements.txt
echo [OK] Zavisimosti ustanovleny
echo.

echo [INFO] Primeneniye migratsiy...
%PYTHON_CMD% manage.py migrate
echo [OK] Migratsii primeneny
echo.

echo [INFO] Zapolneniye testovymi dannymi...
%PYTHON_CMD% manage.py shell ^< create_test_data.py
echo [OK] Testovyye dannyye sozdany
echo.

goto runserver

:full_after_clean
echo [INFO] Ustanovka zavisimostey...
%PYTHON_CMD% -m pip install -q -r requirements.txt
echo [OK] Zavisimosti ustanovleny
echo.

echo [INFO] Primeneniye migratsiy...
%PYTHON_CMD% manage.py migrate
echo [OK] Migratsii primeneny
echo.

echo [INFO] Sozdaniye super'pol'zovatelya...
%PYTHON_CMD% manage.py createsuperuser
echo [OK] Super'pol'zovatel' sozdan
echo.

echo [INFO] Zapolneniye testovymi dannymi...
%PYTHON_CMD% manage.py shell ^< create_test_data.py
echo [OK] Testovyye dannyye sozdany
echo.

goto runserver

:migrate
echo [INFO] Primeneniye migratsiy...
%PYTHON_CMD% manage.py migrate
echo [OK] Migratsii primeneny
exit /b 0

:data
echo [INFO] Zapolneniye testovymi dannymi...
%PYTHON_CMD% manage.py shell ^< create_test_data.py
echo [OK] Testovyye dannyye sozdany
exit /b 0

:nodata
echo [INFO] Primeneniye migratsiy...
%PYTHON_CMD% manage.py migrate
echo [OK] Migratsii primeneny
goto runserver

:runserver
echo.
echo =================================================
echo   Server zapushchen!
echo   - Osnovnoy sayt: http://localhost:8000
echo   - Admin panel':  http://localhost:8000/admin
echo   - API:           http://localhost:8000/api/
echo =================================================
echo.
%PYTHON_CMD% manage.py runserver
