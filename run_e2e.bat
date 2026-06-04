@echo off
echo ================================================
echo   TEST E2E - AGENT LESO - CONTI
echo ================================================
echo.

REM Telecharge le script Python depuis GitHub
python -c "import urllib.request; urllib.request.urlretrieve('https://raw.githubusercontent.com/theotranvan/agent-leso/claude/stoic-wright-Fvn4G/backend/scripts/full_e2e.py', 'full_e2e.py')" 2>nul

REM Lance le test
python full_e2e.py ^
  --api      https://bet-agent-api.onrender.com ^
  --supabase https://dgjjvajjthsafserxugh.supabase.co ^
  --anon     eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRnamp2YWpqdGhzYWZzZXJ4dWdoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODA0MDUzNzQsImV4cCI6MjA5NTk4MTM3NH0.jKLEukprKldy1wYannLVUR2UXeq7DOVcOod-ZglLmcY ^
  --email    jc.szwed@conti-ing.ch ^
  --password jc.szwed202601

echo.
echo ================================================
echo Appuie sur une touche pour fermer...
pause >nul
