@echo off
rem Opens the warehouse page; starts the local server in the background first if it is not running (no window stays open).
rem Needs Python 3.10+ on PATH (pythonw comes with it). Run from the toolkit: python tools/warehouse_link.py run -- serve  does the same with the right settings.
cd /d "%~dp0"
start "" pythonw warehouse.py serve --open
