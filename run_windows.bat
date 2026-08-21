@echo off
setlocal
cd /d "%~dp0"

echo ================================================
echo  Portal zdravlja - preuzimanje nalaza / download
echo ================================================
echo.

where py >nul 2>nul
if errorlevel 1 goto nopython

rem Only install if the imports are actually missing, so a machine that already
rem has them does not hit the network on every run.
py -c "import requests, lz4.block" >nul 2>nul
if errorlevel 1 (
  echo Instaliram pakete / installing dependencies...
  py -m pip install --quiet --disable-pip-version-check -r requirements.txt
  if errorlevel 1 goto nodeps
)

echo.
if exist "cookie.txt" (
  echo Koristim cookie.txt / using cookie.txt
  py pz_download.py --cookie-file cookie.txt %*
) else (
  py pz_download.py %*
)
rem "if errorlevel N" means "N or higher", so the highest code is tested first.
if errorlevel 2 goto authfailed
if errorlevel 1 goto failed

echo.
echo Gotovo. Nalazi su u mapi "nalazi".
echo Done. Your reports are in the "nalazi" folder.
echo.
pause
exit /b 0

:failed
echo.
echo ------------------------------------------------
echo  Doslo je do greske / something went wrong
echo ------------------------------------------------
echo.
echo Poruka o gresci je ispisana iznad. Ako su se datoteke ipak
echo preuzele, provjerite mapu "nalazi" prije nego sto zakljucite
echo da nista nije uspjelo.
echo The error is printed above. If files were downloaded anyway,
echo check the "nalazi" folder before assuming nothing worked.
echo.
echo Prijavite gresku, ali NE lijepite odgovore portala.
echo Report the bug, but do NOT paste portal responses.
echo.
pause
exit /b 1

:authfailed
echo.
echo ------------------------------------------------
echo  Problem s prijavom / login problem
echo ------------------------------------------------
echo.
echo Poruka o gresci je ispisana iznad.
echo The error message is printed above.
echo.
echo Najcesci uzrok: niste prijavljeni na Portal zdravlja u Firefoxu,
echo ili koristite neki drugi preglednik.
echo Most common cause: you are not logged in to Portal zdravlja in
echo Firefox, or you use a different browser.
echo.
echo Rjesenje - spremite kolacic rucno / fix - save the cookie by hand:
echo   1. Prijavite se na portal / log in to the portal
echo   2. Pritisnite F12, kartica Mreza / Network
echo   3. Kliknite bilo koji zahtjev prema api/rest
echo   4. Kopirajte cijeli redak koji pocinje s "Cookie:"
echo   5. Spremite ga u datoteku cookie.txt u ovu mapu
echo   6. Ponovno pokrenite ovu datoteku / run this file again
echo.
pause
exit /b 2

:nopython
echo Python nije pronaden. / Python was not found.
echo.
echo Instalirajte Python s: https://www.python.org/downloads/
echo Install Python from:   https://www.python.org/downloads/
echo.
echo Nakon instalacije ponovno pokrenite ovu datoteku.
echo After installing, run this file again.
echo.
pause
exit /b 1

:nodeps
echo Instalacija paketa nije uspjela. / dependency install failed.
echo Provjerite internetsku vezu. / check your internet connection.
echo.
pause
exit /b 1
