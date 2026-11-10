# Release complete : cle de signature (si absente) -> builds Windows + Android -> manifeste signe.
# Ne publie rien. Les options (-SkipAndroid, -SkipWindows, -RunTests) vont a build-release.ps1.
param([switch]$SkipWindows, [switch]$SkipAndroid, [switch]$RunTests)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
. (Join-Path $PSScriptRoot 'find-python.ps1')

function Step($m) { Write-Host "`n==> $m" -ForegroundColor Cyan }

$python = Find-Python
if (-not $python) {
    throw "Python 3 introuvable (ni 'python', ni 'py', ni dans les dossiers d'installation habituels). Installe-le depuis python.org en cochant 'Add python.exe to PATH'."
}
$pyExe = $python[0]; $pyArgs = @($python | Select-Object -Skip 1)
Write-Host "Python : $pyExe $($pyArgs -join ' ')"
function Py { & $pyExe @pyArgs @args; if ($LASTEXITCODE -ne 0) { throw "Echec ($LASTEXITCODE) : python $args" } }

$ErrorActionPreference = 'Continue'
& $pyExe @pyArgs -c "import cryptography" 2>$null
$hasCrypto = ($LASTEXITCODE -eq 0)
$ErrorActionPreference = 'Stop'
if (-not $hasCrypto) {
    throw "Le module 'cryptography' manque : lance  `"$pyExe`" -m pip install -r requirements.txt"
}

Step '1/3 Cle de signature des mises a jour'
if (Test-Path (Join-Path $root 'release-signing.key')) {
    Write-Host 'Deja presente.'
} else {
    Py scripts\release_update.py keygen
    Write-Host "`nIMPORTANT : sauvegardez release-signing.key (jamais dans git) et committez app\update_key.py :" -ForegroundColor Yellow
    Write-Host "la cle publique doit etre dans l'application construite ci-dessous." -ForegroundColor Yellow
}

Step '2/3 Build Windows + Android'
$buildArgs = @{}
if ($SkipWindows) { $buildArgs.SkipWindows = $true }
if ($SkipAndroid) { $buildArgs.SkipAndroid = $true }
if ($RunTests) { $buildArgs.RunTests = $true }
& (Join-Path $root 'build-release.ps1') @buildArgs
if ($LASTEXITCODE -ne 0) { throw "build-release.ps1 a echoue (code $LASTEXITCODE)" }

Step '3/3 Manifeste signe'
$notes = Join-Path $root 'CHANGELOG-notes.txt'
if (Test-Path $notes) { Py scripts\release_update.py manifest --notes-file $notes } else { Py scripts\release_update.py manifest }

Write-Host "`nTERMINE. Fichiers a envoyer sur le depot (dossier release\) :" -ForegroundColor Green
Get-ChildItem (Join-Path $root 'release') | Where-Object { $_.Name -match '^(Audook-Setup-.*\.exe|Audook-.*\.apk|latest\.json(\.sig)?)$' } | ForEach-Object { Write-Host "  $($_.Name)" }
Write-Host "Rien n'a ete publie. Envoyez latest.json et latest.json.sig en dernier."
