@echo off
REM ============================================================================
REM fix-gem-ext.bat — build a native Ruby gem whose generated Makefile carries
REM MSYS-style absolute paths (/D/Ruby40/...) that the ucrt64 gcc cannot resolve.
REM
REM Root cause (proven 2026-10-07): mkmf writes the include dirs in MSYS form.
REM Working from MSYS bash it happens to survive (the MSYS runtime rewrites the
REM path before gcc sees it), but as soon as `make` is driven through cmd/ridk
REM the path reaches gcc verbatim and every `#include <ruby.h>` fails, while the
REM C files that do NOT include ruby.h compile fine.  That split is the tell.
REM
REM Usage:  fix-gem-ext.bat <gem-name> <version> [ext-subdir]
REM   e.g.  fix-gem-ext.bat yajl-ruby 1.4.3
REM         fix-gem-ext.bat websocket-driver 0.8.2
REM         fix-gem-ext.bat fiddle 1.1.8
REM
REM What it does, in order:
REM   1. run extconf.rb to (re)generate the Makefile
REM   2. rewrite '/D/Ruby40' -> 'D:/Ruby40' inside it  <-- the actual fix
REM   3. make + make install under the devkit environment
REM   4. register the build: copy the .so into extensions/<arch>/<ver>/<gem>-<ver>/
REM      and write gem.build_complete, otherwise RubyGems keeps reporting
REM      "Ignoring <gem> because its extensions are not built"
REM ============================================================================
setlocal enabledelayedexpansion
set RUBYDIR=D:\Ruby40
set GEMNAME=%1
set GEMVER=%2
set GEMROOT=%RUBYDIR%\lib\ruby\gems\4.0.0\gems\%GEMNAME%-%GEMVER%
set EXTDIR=%GEMROOT%\ext\%3
if "%3"=="" set EXTDIR=%GEMROOT%\ext\%GEMNAME%

if not exist "%EXTDIR%\extconf.rb" (
  echo   extconf.rb not in %EXTDIR% -- searching...
  for /f "delims=" %%F in ('dir /b /s "%GEMROOT%\ext\extconf.rb" 2^>nul') do set EXTDIR=%%~dpF
)
if not exist "%EXTDIR%\extconf.rb" ( echo   no extconf.rb under %GEMROOT% & exit /b 1 )

cd /d "%EXTDIR%" || ( echo   ext dir missing & exit /b 1 )
echo   ext: %EXTDIR%

"%RUBYDIR%\bin\ruby.exe" extconf.rb >nul 2>&1
if not exist Makefile ( echo   Makefile not generated & exit /b 1 )

REM ---- THE FIX --------------------------------------------------------------
powershell -NoProfile -Command "(Get-Content Makefile) -replace '/D/Ruby40','D:/Ruby40' | Set-Content Makefile"
REM ---------------------------------------------------------------------------

call "%RUBYDIR%\bin\ridk.cmd" exec make >nul 2>&1
if errorlevel 1 ( echo   BUILD FAILED -- re-run make by hand to see the real error & exit /b 1 )
call "%RUBYDIR%\bin\ridk.cmd" exec make install >nul 2>&1

set EXTSTORE=%RUBYDIR%\lib\ruby\gems\4.0.0\extensions\x64-mingw-ucrt\4.0.0\%GEMNAME%-%GEMVER%
if not exist "%EXTSTORE%\" mkdir "%EXTSTORE%"
for /r "%EXTDIR%" %%S in (*.so) do copy /y "%%S" "%EXTSTORE%\" >nul 2>&1
echo built > "%EXTSTORE%\gem.build_complete"
echo   BUILD+REGISTER OK  (%EXTSTORE%)
endlocal
