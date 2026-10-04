# Audook - build des releases : installeur Windows (NSIS) + APK Android signe.
#
# Usage (depuis la racine du projet) :
#   .\build-release.ps1                  # installeur Windows + APK
#   .\build-release.ps1 -SkipAndroid     # seulement l'installeur Windows
#   .\build-release.ps1 -SkipWindows     # seulement l'APK
#   .\build-release.ps1 -RunTests        # lance `npm test` avant de construire
#
# Resultat dans .\release\ :
#   Audook-Setup-<version>.exe   installeur NSIS
#   Audook-<version>.apk         APK signe (android\keystore.properties requis)

param(
    [switch]$SkipWindows,
    [switch]$SkipAndroid,
    [switch]$RunTests
)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
Set-Location $root

function Step($message) { Write-Host "`n==> $message" -ForegroundColor Cyan }
function Check($label) {
    if ($LASTEXITCODE -ne 0) { throw "$label a echoue (code $LASTEXITCODE)" }
}

$version = (Get-Content (Join-Path $root 'package.json') -Raw | ConvertFrom-Json).version
$releaseDir = Join-Path $root 'release'
$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()

if ($SkipWindows -and $SkipAndroid) { throw 'Rien a construire : -SkipWindows et -SkipAndroid sont tous les deux actifs.' }

# --- Prerequis -------------------------------------------------------------
Step 'Verification des prerequis'
foreach ($tool in @('node', 'npm')) {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) { throw "$tool introuvable dans le PATH" }
}

# Python : on teste plusieurs emplacements (le PATH n'est pas toujours configure
# quand on lance le .bat par double-clic) et on verifie qu'il demarre vraiment
# (l'alias du Microsoft Store existe parfois sans etre un vrai Python).
function Find-Python {
    $candidates = @()
    foreach ($name in @('python', 'python3')) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($cmd) { $candidates += , @($cmd.Source) }
    }
    $launcher = Get-Command py -ErrorAction SilentlyContinue
    if ($launcher) { $candidates += , @($launcher.Source, '-3') }
    $roots = @("$env:LOCALAPPDATA\Programs\Python", $env:ProgramFiles, "${env:ProgramFiles(x86)}")
    foreach ($r in $roots) {
        if ($r -and (Test-Path $r)) {
            Get-ChildItem $r -Directory -Filter 'Python3*' -ErrorAction SilentlyContinue |
                Sort-Object Name -Descending |
                ForEach-Object { $exe = Join-Path $_.FullName 'python.exe'; if (Test-Path $exe) { $candidates += , @($exe) } }
        }
    }
    foreach ($c in $candidates) {
        $exe = $c[0]; $extra = @($c | Select-Object -Skip 1)
        $ErrorActionPreference = 'Continue'
        $out = & $exe @extra --version 2>&1
        $ok = ($LASTEXITCODE -eq 0) -and ("$out" -match 'Python 3')
        $ErrorActionPreference = 'Stop'
        if ($ok) { return , $c }
    }
    return $null
}

$python = $null
if (-not $SkipWindows) {
    $python = Find-Python
    if (-not $python) {
        throw "Python 3 introuvable (ni 'python', ni 'py', ni dans les dossiers d'installation habituels). Installe-le depuis python.org en cochant 'Add python.exe to PATH'."
    }
    $pyExe = $python[0]; $pyArgs = @($python | Select-Object -Skip 1)
    Write-Host "Python      : $pyExe $($pyArgs -join ' ')"
    $ErrorActionPreference = 'Continue'
    & $pyExe @pyArgs -c "import PyInstaller" 2>$null
    $hasPyInstaller = ($LASTEXITCODE -eq 0)
    $ErrorActionPreference = 'Stop'
    if (-not $hasPyInstaller) {
        throw "PyInstaller n'est pas installe pour ce Python : lance  `"$pyExe`" -m pip install pyinstaller -r requirements.txt"
    }
}
if (-not (Test-Path (Join-Path $root 'node_modules'))) {
    Step 'npm install'
    npm install
    Check 'npm install'
}

if (-not $SkipAndroid) {
    if (-not (Test-Path (Join-Path $root 'android\keystore.properties'))) {
        throw "android\keystore.properties introuvable : sans la cle de signature, l'APK ne pourrait pas s'installer en mise a jour sur un telephone qui a deja Audook."
    }

    # SDK Android : ANDROID_HOME, sinon sdk.dir de android\local.properties
    $sdk = $env:ANDROID_HOME
    if (-not $sdk) { $sdk = $env:ANDROID_SDK_ROOT }
    if (-not $sdk) {
        $localProps = Join-Path $root 'android\local.properties'
        if (Test-Path $localProps) {
            $line = Get-Content $localProps | Where-Object { $_ -match '^sdk\.dir=' } | Select-Object -First 1
            if ($line) { $sdk = ($line -replace '^sdk\.dir=', '') -replace '\\:', ':' -replace '\\\\', '\' }
        }
    }
    if (-not $sdk -or -not (Test-Path $sdk)) { throw 'SDK Android introuvable : definis ANDROID_HOME ou sdk.dir dans android\local.properties' }
    $env:ANDROID_HOME = $sdk

    # JDK : JAVA_HOME, sinon le JBR embarque dans Android Studio
    $javaHome = $env:JAVA_HOME
    if (-not $javaHome -or -not (Test-Path (Join-Path $javaHome 'bin\java.exe'))) {
        $candidates = @(
            (Join-Path (Split-Path $sdk -Parent) 'Android Studio\jbr'),
            "$env:ProgramFiles\Android\Android Studio\jbr"
        )
        $javaHome = $candidates | Where-Object { Test-Path (Join-Path $_ 'bin\java.exe') } | Select-Object -First 1
    }
    if (-not $javaHome) { throw 'JDK introuvable : definis JAVA_HOME (ex. le dossier jbr d''Android Studio)' }
    $env:JAVA_HOME = $javaHome
    Write-Host "SDK Android : $sdk"
    Write-Host "JDK         : $javaHome"
}

if ($RunTests) {
    Step 'Tests automatises'
    npm test
    Check 'Les tests'
}

New-Item -ItemType Directory -Force -Path $releaseDir | Out-Null

# --- Backend Windows (PyInstaller), avant le build React qui vide build\ -----
if (-not $SkipWindows) {
    Step 'Backend Python -> audook_backend.exe (PyInstaller)'
    $work = Join-Path $root 'build\pyinstaller'
    & $pyExe @pyArgs -m PyInstaller audook_backend.py `
        --name=audook_backend --onefile --console `
        "--icon=$root\assets\icons\audook.ico" `
        --clean --noconfirm `
        "--distpath=$root\dist\audook_backend" "--workpath=$work" "--specpath=$work" `
        "--add-data=$root\assets;assets" `
        --hidden-import=flask --hidden-import=flask_cors --hidden-import=sqlalchemy --hidden-import=sqlalchemy.orm `
        --hidden-import=vlc --hidden-import=requests --hidden-import=pydantic --hidden-import=pydantic_core `
        --collect-submodules=pychromecast --collect-submodules=zeroconf --collect-submodules=casttube
    Check 'PyInstaller'
}

# --- Frontend React (une seule fois pour les deux cibles) --------------------
Step 'Frontend React (npm run react-build)'
npm run react-build
Check 'react-build'

# --- Installeur Windows ------------------------------------------------------
if (-not $SkipWindows) {
    Step 'Installeur Windows NSIS (electron-builder)'
    npm run preelectron-build
    Check 'preelectron-build'
    $winOut = Join-Path $releaseDir '_win'
    if (Test-Path $winOut) { Remove-Item $winOut -Recurse -Force }
    npx electron-builder --win nsis --publish never "-c.directories.output=$winOut"
    Check 'electron-builder'

    $installer = Get-ChildItem $winOut -Filter '*Setup*.exe' | Select-Object -First 1
    if (-not $installer) { throw "Installeur introuvable dans $winOut" }
    Copy-Item $installer.FullName (Join-Path $releaseDir "Audook-Setup-$version.exe") -Force
    Remove-Item $winOut -Recurse -Force
}

# --- APK Android -------------------------------------------------------------
if (-not $SkipAndroid) {
    Step 'Synchronisation Capacitor'
    $assets = Join-Path $root 'android\app\src\main\assets\public'
    if (Test-Path $assets) { Remove-Item $assets -Recurse -Force }
    npx cap sync android
    Check 'cap sync'

    Step 'APK release (Gradle)'
    Push-Location (Join-Path $root 'android')
    try {
        .\gradlew.bat :app:assembleRelease --console=plain
        Check 'Gradle assembleRelease'
    } finally {
        Pop-Location
    }

    $apk = Join-Path $root 'android\app\build\outputs\apk\release\app-release.apk'
    if (-not (Test-Path $apk)) { throw "APK introuvable : $apk (signature non configuree ?)" }

    Step "Verification de la signature"
    $apksigner = Get-ChildItem (Join-Path $env:ANDROID_HOME 'build-tools') -Recurse -Filter 'apksigner.bat' |
        Sort-Object FullName | Select-Object -Last 1
    if ($apksigner) {
        # apksigner prints harmless Java warnings on stderr; PowerShell 5.1 would
        # turn those into terminating errors under 'Stop'.
        $ErrorActionPreference = 'Continue'
        $certs = & $apksigner.FullName verify --print-certs $apk 2>$null
        $signerExit = $LASTEXITCODE
        $ErrorActionPreference = 'Stop'
        if ($signerExit -ne 0) { throw 'La signature de l''APK est invalide' }
        $certs | Where-Object { $_ -match 'SHA-256' } | ForEach-Object { Write-Host $_ }
    } else {
        Write-Host 'apksigner introuvable - signature non verifiee' -ForegroundColor Yellow
    }
    Copy-Item $apk (Join-Path $releaseDir "Audook-$version.apk") -Force
}

# --- Resume ------------------------------------------------------------------
$stopwatch.Stop()
Write-Host "`nTermine en $([int]$stopwatch.Elapsed.TotalSeconds) s - fichiers dans $releaseDir :" -ForegroundColor Green
Get-ChildItem $releaseDir -File | ForEach-Object {
    Write-Host ("  {0}  ({1:N1} Mo)" -f $_.Name, ($_.Length / 1MB))
}
