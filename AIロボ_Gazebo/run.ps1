param(
  [string]$ContainerName = $(if ($env:AIROBO_DOCKER_CONTAINER) { $env:AIROBO_DOCKER_CONTAINER } else { "pai-crane-ai-base-20261101" })
)

$ErrorActionPreference = "Stop"
$RemotePath = "/tmp/airobo_v3_from_github"

Write-Host "AIロボ V3：GitHubのソースをDockerへコピーします。"
docker exec $ContainerName mkdir -p $RemotePath
if ($LASTEXITCODE -ne 0) { throw "エラー：Dockerコンテナへ接続できません。" }

docker cp "$PSScriptRoot\." "${ContainerName}:$RemotePath"
if ($LASTEXITCODE -ne 0) { throw "エラー：ファイルをDockerへコピーできません。" }

Write-Host "物理Pick & Placeの自動検証を開始します。"
docker exec $ContainerName bash "$RemotePath/run.sh"
if ($LASTEXITCODE -ne 0) { throw "検証に失敗しました。終了コード：$LASTEXITCODE" }
Write-Host "検証が完了しました。QAはコンテナ内のruns/に保存されています。"
