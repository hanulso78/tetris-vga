@echo off
rem Build TETRIS.EXE with djgpp (arguments go to make)
call "%~dp0..\..\djgpp\setenv.bat"
cd /d "%~dp0"
make -f tt.mak %*
