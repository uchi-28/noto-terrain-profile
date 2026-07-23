# 側線ピッカー(DEM断面図ツール)セットアップスクリプト
#
# 使い方: このフォルダ内でPowerShellを開き、次を実行する。
#   powershell -ExecutionPolicy Bypass -File install.ps1
#
# 実行内容:
#   1. uv (Pythonパッケージマネージャ)が無ければインストールする
#   2. `uv sync` でPython環境を構築する
#   3. デスクトップに「側線ピッカー」ショートカットを作成する
#
# 実行後、DEM(GeoTIFF、EPSG:6675)ファイルを dem\ フォルダに配置してから
# デスクトップの「側線ピッカー」を起動すること。

$ErrorActionPreference = "Stop"
$ProjectDir = $PSScriptRoot

Write-Host "=== 1. uv の確認 ==="
$uvCmd = Get-Command uv -ErrorAction SilentlyContinue
if ($uvCmd) {
    $uvExe = $uvCmd.Source
} else {
    Write-Host "uv が見つからないため、公式インストーラーで導入します..."
    Invoke-Expression (Invoke-RestMethod https://astral.sh/uv/install.ps1)
    $uvExe = "$env:USERPROFILE\.local\bin\uv.exe"
}

if (-not (Test-Path $uvExe)) {
    Write-Error "uv が見つかりません。手動で https://docs.astral.sh/uv/ を参照してインストールしてから、このスクリプトを再実行してください。"
    exit 1
}
Write-Host "uv: $uvExe"

Write-Host ""
Write-Host "=== 2. Python環境のセットアップ (uv sync) ==="
Push-Location $ProjectDir
& $uvExe sync
Pop-Location

Write-Host ""
Write-Host "=== 3. デスクトップショートカットの作成 ==="
# .bat経由だと組織管理PCのセキュリティポリシーでブロックされることがあったため、
# uv.exeを直接呼び出す形にしている(実機で動作確認済みの構成)。
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\側線ピッカー.lnk")
$Shortcut.TargetPath = $uvExe
$Shortcut.Arguments = 'run python -m dem_profile.pick_transect_gui'
$Shortcut.WorkingDirectory = $ProjectDir
$Shortcut.Description = "陰影図をクリックして側線を選び、断面図を作成するツール"
$Shortcut.Save()

Write-Host ""
Write-Host "=== 完了 ==="
Write-Host "デスクトップに「側線ピッカー」というショートカットを作成しました。"
Write-Host "実行前に、DEM(GeoTIFF、EPSG:6675)ファイルを次のフォルダに配置してください:"
Write-Host "  $ProjectDir\dem\"
