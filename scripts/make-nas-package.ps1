# Cree release\Audook-NAS-<version>.zip : uniquement ce dont le conteneur Docker a besoin
# (pas de node_modules, build, android, cles de signature). Le docker-compose.yml est
# fourni sous le nom docker-compose.example.yml pour ne pas ecraser celui du NAS
# (chemins et jeton deja configures).
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$version = (Get-Content (Join-Path $root 'package.json') -Raw | ConvertFrom-Json).version
$stage = Join-Path $env:TEMP "audook-nas-$version"
$out = Join-Path $root "release\Audook-NAS-$version.zip"

if (Test-Path $stage) { Remove-Item $stage -Recurse -Force }
New-Item -ItemType Directory -Path $stage, (Join-Path $root 'release') -Force | Out-Null

foreach ($f in 'Dockerfile', 'requirements.txt', 'audook_backend.py') {
    Copy-Item (Join-Path $root $f) $stage
}
Copy-Item (Join-Path $root 'docker-compose.yml') (Join-Path $stage 'docker-compose.example.yml')
Copy-Item (Join-Path $root 'app') (Join-Path $stage 'app') -Recurse
Get-ChildItem (Join-Path $stage 'app') -Recurse -Directory -Filter '__pycache__' | Remove-Item -Recurse -Force

@"
Audook NAS $version - mise a jour du conteneur

1. Copiez le CONTENU de ce zip dans le dossier Audook de votre NAS (celui qui contient
   deja votre docker-compose.yml), en acceptant de remplacer les fichiers.
   Ne remplacez PAS votre docker-compose.yml ni votre .env (chemins et jeton).
   Le dossier de donnees (volume) n'est pas touche.
2. Reconstruisez et relancez le conteneur :
   - SSH :       cd <dossier> && docker compose up -d --build
   - Portainer : Stacks > audook > "Update the stack" (avec reconstruction de l'image).
   - OpenMediaVault (plugin Compose) : fichier Audook > Down, puis Build, puis Up.
3. Verifiez : http://<ip-du-nas>:5000/health
"@ | Set-Content (Join-Path $stage 'LISEZMOI-NAS.txt') -Encoding UTF8

if (Test-Path $out) { Remove-Item $out -Force }
Compress-Archive -Path (Join-Path $stage '*') -DestinationPath $out
Remove-Item $stage -Recurse -Force
Write-Host "Cree : $out"
