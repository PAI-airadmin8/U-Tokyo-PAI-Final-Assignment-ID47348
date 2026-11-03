$ErrorActionPreference = "Stop"
Write-Host "AIロボ V3｜Physical Pick & Place 自動 QA" -ForegroundColor White
docker exec pai-crane-ai-base-20261101 bash /home/ubuntu/airobot_ws/pai_airobo_v3_delivery/run.sh
if ($LASTEXITCODE -ne 0) { throw "AIロボ V3 QA failed. Exit code: $LASTEXITCODE" }
Write-Host "AIロボ V3 QA succeeded." -ForegroundColor White
