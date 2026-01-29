# Slide Voice Maker - ワンクリック起動スクリプト
# バージョン: 1.0.0
# 日付: 2026-01-05

$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "Slide Voice Maker Server"

Set-Location -Path $PSScriptRoot
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001 | Out-Null

# .env を読み込んで環境変数に反映（KEY=VALUE、#コメント行は無視）
$envFile = Join-Path $PSScriptRoot ".env"
if (Test-Path $envFile) {
    Write-Host ".env を読み込んで環境変数に反映します..."
    Get-Content $envFile | ForEach-Object {
        $line = $_.Trim()
        if (-not $line) { return }
        if ($line.StartsWith("#")) { return }
        if ($line -notmatch "=") { return }
        $parts = $line.Split("=", 2)
        $k = $parts[0].Trim()
        $v = $parts[1].Trim()
        if (-not $k) { return }
        # 前後のクォートを軽く剥がす
        if (($v.StartsWith('"') -and $v.EndsWith('"')) -or ($v.StartsWith("'") -and $v.EndsWith("'"))) {
            $v = $v.Substring(1, $v.Length - 2)
        }
        Set-Item -Path ("Env:" + $k) -Value $v
    }
}

Write-Host ""
Write-Host "========================================"
Write-Host "  Slide Voice Maker Server"
Write-Host "  http://127.0.0.1:8000"
Write-Host "========================================"
Write-Host ""

# 仮想環境の確認と作成
if (Test-Path ".venv\Scripts\Activate.ps1") {
    Write-Host "既存の仮想環境を使用します..."
    & .\.venv\Scripts\Activate.ps1

    # requirements.txt 更新時の取りこぼし防止（例: truststore 追加）
    Write-Host "依存関係を確認しています..."
    pip show truststore | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "不足パッケージを検出しました。依存関係をインストールしています..."
        pip install -r requirements.txt
    }
} else {
    Write-Host "仮想環境を作成しています..."
    py -m venv .venv
    & .\.venv\Scripts\Activate.ps1
    Write-Host "依存関係をインストールしています..."
    pip install -r requirements.txt
}

# ポート8000の解放（使用中のプロセスを終了）
Write-Host "ポート8000を確認中..."
$portInUse = netstat -ano | Select-String ":8000\s+.*LISTENING" | ForEach-Object {
    if ($_ -match '\s+(\d+)\s*$') { $matches[1] }
}
if ($portInUse) {
    Write-Host "ポート8000を使用しているプロセス(PID: $portInUse)を終了しています..."
    Stop-Process -Id $portInUse -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

Write-Host "サーバーを起動しています..."

# サーバーをバックグラウンドで起動
$venvPython = "$PSScriptRoot\.venv\Scripts\python.exe"
Start-Process -FilePath $venvPython -ArgumentList "-m", "uvicorn", "src.server:app", "--host", "127.0.0.1", "--port", "8000" -WindowStyle Hidden -WorkingDirectory $PSScriptRoot

Write-Host "サーバー起動を待機中..."
$maxWait = 30
$waited = 0
while ($waited -lt $maxWait) {
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/health" -TimeoutSec 1 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) { break }
    } catch { }
    Start-Sleep -Seconds 1
    $waited++
}

if ($waited -ge $maxWait) {
    Write-Host "サーバー起動がタイムアウトしました。" -ForegroundColor Red
    Write-Host "手動で起動する場合: py -m uvicorn src.server:app --host 127.0.0.1 --port 8000"
    exit 1
}

# ブラウザでindex.htmlを開く
Write-Host "ブラウザを起動しています..."
Start-Process "http://127.0.0.1:8000/index.html"

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  サーバー起動完了！" -ForegroundColor Green
Write-Host "  URL: http://127.0.0.1:8000/index.html" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "サーバーはバックグラウンドで動作しています。"
Write-Host "終了するにはタスクマネージャーからpython.exeを終了してください。"
Write-Host ""

Start-Sleep -Seconds 3
