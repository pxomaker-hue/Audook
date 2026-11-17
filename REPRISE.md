# Reprise : publier la version 1.0.5 depuis l'autre PC

À lire en premier par la session (ou la personne) qui reprend sur le PC qui possède
la clé de signature des mises à jour. Écrit le 2026-11-17.

## Où on en est

- La **1.0.4** publiée / installée avait un backend Windows cassé : l'`.exe` embarqué
  plantait au démarrage avec `ModuleNotFoundError: No module named 'cryptography'`
  (l'appli affichait « Serveur non disponible (localhost:5000) »). Cause : `cryptography`
  (dans `requirements.txt`) n'était pas installé dans le Python du build, donc
  PyInstaller ne l'a pas embarqué, sans aucune erreur au build.
- Sur le PC « principal », une 1.0.4 **corrigée** a été compilée et installée à la main
  (même numéro de version, donc pas passée par le système de mises à jour). L'appli
  fonctionne de nouveau.
- **Mise à jour du 2026-11-17 au soir** : le dépôt est passé en **1.0.5** sur l'autre PC, et
  la 1.0.5 signée (installeur, APK, `latest.json` + `.sig`) y a été construite. Une copie de
  `release-signing.key` est maintenant rangée avec les clés Android, dans
  `Z:\Dev - Applications\Installations\key\audook\` (le même partage que `W:` ci-dessous).
- `build-release.ps1` a maintenant deux garde-fous : il vérifie que les modules Python
  nécessaires sont installés avant de compiler, et il démarre le backend compilé pour
  vérifier que `/health` répond. Le build s'arrête sinon.

## À ne pas oublier : les clés de signature

Deux clés différentes, **jamais dans git** (elles sont dans `.gitignore`) :

| Clé | Sert à | À copier sur la machine qui build |
|---|---|---|
| `release-signing.key` | Signer le manifeste de mise à jour `latest.json` (Ed25519). Sa moitié publique est dans `app/update_key.py`. | À la **racine du projet**. Elle n'existe que sur l'autre PC. |
| `audook-release.jks` + `keystore.properties` | Signer l'APK Android (sans cette clé, l'APK ne se met pas à jour sur le téléphone). | `keystore.properties` dans `android\` et le `.jks` dans `android\app\` (le chemin `storeFile` est relatif au module `app`). Copie de référence : `W:\Dev - Applications\Installations\key\audook\`. |

**Ne jamais lancer `python scripts/release_update.py keygen` si `release-signing.key`
manque** : cela génère une nouvelle paire et écrase `app/update_key.py`. Les applis déjà
installées rejetteraient alors toutes les mises à jour. (`build-all.bat` appelle `keygen`
automatiquement quand la clé est absente : vérifier qu'elle est là **avant**.)

Le SDK Android doit aussi être trouvable : `ANDROID_HOME` ou un `android\local.properties`
contenant `sdk.dir=C:/Android/Sdk` (barres obliques ; fichier ignoré par git).

## Procédure

1. Mettre à jour le dépôt : `git pull`.
2. Vérifier la clé : `release-signing.key` doit être à la racine (voir plus haut).
3. Dépendances Python du build :
   ```powershell
   pip install -r requirements.txt pyinstaller
   ```
4. Passer en 1.0.5 (met à jour `package.json`, le lock, `app/__init__.py` et le
   `versionCode` Android 10005) :
   ```powershell
   npm version 1.0.5 --no-git-tag-version
   ```
   Attention : le script `version` fait un `git add app/__init__.py` ; relire
   `git status` avant de commiter, pour ne pas mélanger ce fichier à un autre commit.
5. Optionnel : écrire les notes de version dans `CHANGELOG-notes.txt` (reprises dans le manifeste).
6. Tout construire :
   ```powershell
   .\build-all.bat
   ```
   Il enchaîne : clé, installeur Windows + APK signé, test de démarrage du backend
   compilé, puis `release\latest.json` et `release\latest.json.sig`. Il ne publie rien.
   S'il s'arrête, lire le message : modules Python manquants, clé Android absente, SDK
   introuvable, backend qui ne répond pas sur `/health`.
7. Commiter la version : `package.json`, `package-lock.json`, `app/__init__.py`.
   `git status` doit être propre ensuite. Si `app/update_key.py` apparaît modifié, c'est
   qu'un `keygen` s'est lancé : **arrêter**, restaurer le fichier (`git checkout app/update_key.py`)
   et retrouver la bonne clé privée.
8. Publier dans `https://easywork.kairos-app.website/audook/`, **dans cet ordre** :
   1. `Audook-Setup-1.0.5.exe`
   2. `Audook-1.0.5.apk`
   3. `latest.json`
   4. `latest.json.sig` en dernier (tant que le manifeste n'est pas en ligne, personne ne voit la mise à jour).
9. Tester : dans **Paramètres > Mise à jour** de l'appli installée en 1.0.4, la 1.0.5 doit
   être détectée, téléchargée (SHA-256 et signature vérifiés) et installée.
10. NAS (Docker) : mise à jour manuelle, sur le NAS :
    `git pull && docker compose up -d --build` (le dossier de données est un volume).
    Le NAS tourne peut-être encore avec un ancien backend.

## Pièges connus

- **`TEMP`/`TMP` sous `%AppData%`** : sur le PC principal, Gradle échouait avec
  `Unable to establish loopback connection`. `build-release.ps1` redirige `TEMP`/`TMP` vers
  `C:\BuildTmp` le temps de l'étape Gradle. Ce n'est pas lié à une erreur réseau.
- **Erreur TLS vers `dl.google.com`** pendant Gradle : problème réseau intermittent, le
  script réessaie une fois. Au besoin relancer.
- **`build-release.bat` ne doit pas être lancé depuis un shell non interactif** (il se
  termine par `pause`) : utiliser `build-release.ps1` ou `scripts\build-all.ps1`.
- **Journal du backend Windows** : `%APPDATA%\Audook\backend.log` (c'est là qu'on lit un
  plantage au démarrage).
