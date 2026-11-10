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
