@echo off
REM update.bat -- py-tree-manager self-replace helper.
REM
REM Args:
REM   %1 = full path to py-tree-manager.exe (the file being replaced)
REM   %2 = full path to the downloaded .new file (will be moved over %1)
REM   %3 = parent PID (we wait until this PID exits before swapping)
REM
REM Strategy: poll up to ~30 seconds for the parent to release the lock,
REM then atomically replace, then relaunch.

setlocal

set "TARGET=%~1"
set "SOURCE=%~2"
set "PARENT_PID=%~3"

REM --- Step 1: wait for parent process to exit (max ~30 s) ---
set /a TRIES=0
:WAIT_PARENT
tasklist /FI "PID eq %PARENT_PID%" 2>NUL | find "%PARENT_PID%" >NUL
if errorlevel 1 goto PARENT_GONE
set /a TRIES+=1
if %TRIES% GEQ 30 goto FORCE_RETRY
timeout /t 1 /nobreak >NUL
goto WAIT_PARENT

:PARENT_GONE
REM Parent confirmed gone. Even so, the file lock may linger one tick.
timeout /t 1 /nobreak >NUL

:FORCE_RETRY
REM --- Step 2: try to replace; retry on file-lock for up to ~30 s ---
set /a RETRY=0
:DO_MOVE
move /Y "%SOURCE%" "%TARGET%" >NUL 2>&1
if not errorlevel 1 goto MOVED
set /a RETRY+=1
if %RETRY% GEQ 30 goto FAIL
timeout /t 1 /nobreak >NUL
goto DO_MOVE

:MOVED
REM --- Step 3: relaunch the app ---
start "" "%TARGET%"
endlocal
exit /b 0

:FAIL
REM Move failed after 30 retries. Leave .new in place; the next launch
REM will detect the same version and re-attempt.
REM Don't delete .new; user may inspect.
endlocal
exit /b 1
