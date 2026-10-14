# Audook — lecteur d'audiolivres pour Windows et Android

Audook est un lecteur d'audiolivres moderne qui se connecte à vos serveurs **Audiobookshelf** et **Plex**, ou lit simplement un **dossier local**. Il existe en trois versions qui partagent la même interface :

- **Windows** — application de bureau (Electron + React), avec son propre serveur local.
- **Android** — application mobile (Capacitor) avec un lecteur natif qui continue de jouer écran éteint.
- **NAS** — le même serveur, déployable en conteneur Docker pour être utilisé par l'application mobile.

## Fonctionnalités

### Sources et bibliothèque
- Serveurs **Audiobookshelf**, **Plex** et **dossiers locaux**, plusieurs à la fois (chacun peut être masqué sans perdre ses données)
- Grille de la bibliothèque triable par série, ordre alphabétique, auteur, genre, collection, progression ou marque-page, avec recherche
- Rubrique **Reprendre l'écoute**, **Collections**, **Historique** d'écoute et page **Découvrir** (parcourir la bibliothèque par auteur)
- Pages **auteur** (biographie et photo, rafraîchissables depuis le web) et page **livre** (chapitres, progression, séries, genres)
- **Édition des métadonnées** avec verrouillage des champs modifiés (un re-scan ne les écrase pas) et **association à une fiche en ligne** (Open Library, Google Books, Audible)
- Marquer un livre comme lu, retirer un livre de « Reprendre l'écoute »

### Lecture
- Lecture/pause, chapitre précédent/suivant, retour/avance de 30 s, barre de progression utilisable au clavier
- Vitesse de lecture (0,75× à 2×), volume (version Windows), **reprise automatique de la position**
- **Minuteur de veille** (5, 10, 15, 20, 30 ou 60 min) avec fondu sur les 20 dernières secondes
- **Égaliseur** (préréglages et préréglages personnalisés), **normalisation du volume** par livre (EBU R128, cible −18 LUFS) et **compression dynamique** (légère, modérée, forte)
- **Réduction du souffle** par livre (ffmpeg), avec choix d'écouter la version nettoyée
- **Marque-pages multiples** par livre, nommables, avec date et reprise en un clic
- **Chromecast / Google Home** (Windows et Android)
- Windows : **mini-lecteur** détachable, touches multimédia du clavier, réduction dans la zone de notification
- Android : lecture en arrière-plan avec contrôles sur l'écran verrouillé (ExoPlayer + MediaSession), minuteur et cast natifs

### Synchronisation
- La progression de lecture est synchronisée avec le serveur d'origine (Audiobookshelf et Plex), donc entre vos appareils
- Les livres d'un dossier local ne se synchronisent qu'avec l'instance qui les contient

### Interface
- Thème **clair, sombre ou automatique** (suit le système), accessibilité clavier (focus visible, boîtes de dialogue, barre de lecture)

## Architecture

| Élément | Technologie | Dossier |
|---|---|---|
| Interface | React + TypeScript (partagée Windows / Android) | `src/` |
| Application Windows | Electron | `electron/` |
| Serveur | Flask + SQLAlchemy (SQLite), routes en blueprints | `audook_backend.py`, `app/` (`app/api/`) |
| Lecture sur PC | VLC (`python-vlc`), Chromecast (`pychromecast`) | `app/player/`, `app/cast/` |
| Application Android | Capacitor + plugin natif Kotlin | `android/` |
| Déploiement NAS | Docker | `Dockerfile`, `docker-compose.yml` |
| Tests | pytest, Jest, JUnit | `tests/`, `src/**/*.test.ts`, `android/app/src/test/` |

Sur Windows, l'application lance son serveur local (`audook_backend.exe`, qui n'écoute que sur `127.0.0.1:5000`). Sur Android, il n'y a pas de serveur local : l'application se connecte à celui du NAS.

## Installation

### Application Windows
Aucune version n'est publiée sur GitHub pour l'instant : l'installeur se construit soi-même (voir [Build de release](#build-de-release)) et se trouve ensuite dans `release/Audook-Setup-<version>.exe`. Lancez-le et suivez l'assistant ; une nouvelle version s'installe **par-dessus** l'ancienne, sans désinstallation préalable. Vos livres, votre progression et vos réglages sont conservés.

### Application Android
Une fois l'APK construit (`release/Audook-<version>.apk`), installez-le sur le téléphone :

```bash
adb install -r release/Audook-<version>.apk
```

ou copiez le fichier sur l'appareil et ouvrez-le (autoriser les sources inconnues). Certains téléphones (Xiaomi) demandent de confirmer l'installation sur l'écran quand elle vient de l'ordinateur.

Au premier lancement, l'application essaie l'adresse du NAS préremplie, `http://192.168.1.200:5000/api` (définie dans `src/config.ts`, modifiable à la compilation avec la variable `REACT_APP_MOBILE_API_BASE`). Si votre NAS a une autre adresse, saisissez-la dans l'écran de connexion ; elle se modifie ensuite dans **Paramètres > Connexion au backend**. Si le NAS exige un jeton d'accès, l'application l'indique et le demande (voir plus bas). L'adresse que vous enregistrez remplace toujours celle par défaut.

L'APK est signé avec une clé de release. **Gardez cette clé** (voir [Build de release](#build-de-release)) : si vous la perdez, Android refusera toute mise à jour et il faudra désinstaller l'application.

### Pour le développement
Prérequis : **Node.js 22+**, **Python 3.11+** et **VLC** 64 bits installé (nécessaire à `python-vlc`). `ffmpeg.exe` est fourni dans `assets/bin/`.

```bash
git clone https://github.com/pxomaker-hue/Audook.git
cd Audook
npm install
pip install -r requirements-dev.txt
npm start        # interface React + Electron ; Electron lance lui-même le backend Python
```

Pour travailler dans un navigateur plutôt que dans Electron, `dev.bat` (ou `dev.ps1`) démarre le backend Flask puis le serveur de développement React.

## Utilisation

### Ajouter un serveur
1. Ouvrez **Paramètres** (barre latérale) puis la section **Serveurs**
2. Cliquez sur **Ajouter un serveur** et choisissez le type :
   - **Audiobookshelf** : URL du serveur (ex. `http://votre-nas:13378`), nom d'utilisateur et mot de passe ; une URL distante facultative permet de basculer entre adresse locale et adresse externe
   - **Plex** : URL du serveur (ex. `http://192.168.1.100:32400`) et clé API (token Plex)
   - **Dossier local** : le dossier qui contient vos livres. Chaque dossier qui contient directement des fichiers audio est un livre, à n'importe quelle profondeur ; titre, auteur et pochette sont lus dans les étiquettes des fichiers (ou dans une image `cover.jpg` à côté)
3. Enregistrez, puis lancez la synchronisation : les livres apparaissent dans la bibliothèque

### Parcourir et écouter
- La **Bibliothèque** liste tous les livres ; cliquez sur un livre pour ouvrir sa page, puis sur **Lire** (ou **Reprendre**)
- Le lecteur est dans le panneau de droite (en bas de l'écran sur petit écran et sur mobile) ; le bouton **…** ouvre vitesse, égaliseur, normalisation, compression, minuteur de veille, volume et Chromecast
- Le bouton marque-page du lecteur enregistre la position courante ; les marque-pages d'un livre sont listés sur sa page (renommer, reprendre, supprimer)

### Touches du clavier
- Touches multimédia (Windows, même application en arrière-plan) : **Lecture/Pause**, **Piste suivante** (avance de 30 s) et **Piste précédente** (recule de 30 s)
- Sur la barre de progression : **← / →** ±10 s, **Page précédente / suivante** ±60 s, **Début / Fin**

### Données
Windows stocke tout dans `%USERPROFILE%\.Audook\` : `audook.db` (base SQLite : bibliothèque, progression, marque-pages, collections, réglages) et `cache\` (pochettes, audio nettoyé). Les réglages propres à l'application Electron (comportement de la fermeture) et le journal du serveur `backend.log` sont dans `%APPDATA%\audook\`.

## Résolution des problèmes

- **Connexion à un serveur** : Plex demande l'URL et le token, Audiobookshelf l'URL, l'utilisateur et le mot de passe ; vérifiez que le serveur est joignable depuis la machine
- **« Serveur non disponible » sur Android** : l'adresse est fausse ou le NAS est injoignable ; **« Accès refusé »** : le NAS exige un jeton d'accès (voir plus bas)
- **Le serveur local ne démarre pas (Windows)** : un autre programme utilise le port 5000 ; consultez `%APPDATA%\audook\backend.log`
- **Pas de son / pas de cast** : vérifiez la sortie audio ; pour le cast, le téléphone et le Chromecast doivent être sur le même réseau
- **Installation Windows bloquée** : quittez Audook par le menu de son icône près de l'horloge, puis relancez l'installeur

## Déploiement Docker sur NAS (OpenMediaVault)

En plus de l'application Windows, une instance backend séparée peut tourner sur un NAS OMV pour être utilisée par l'app mobile Android (voir plus bas). Cette instance a sa **propre base de données SQLite** et sa **propre configuration de serveur** (Plex/Audiobookshelf/dossier local) — elle ne remplace ni ne synchronise l'installation Windows, à l'exception de la progression de lecture sur les livres Plex/Audiobookshelf, qui se synchronise automatiquement via les deux comptes serveur.

### Prérequis
- OMV avec le plugin **Docker Compose** ou **Portainer** installé
- Un dossier sur le NAS pour la persistance des données (`~/.audook` du conteneur)
- Le chemin de partage réseau contenant vos livres audio locaux (optionnel, pour le scan de dossier local)

### Déploiement via le plugin Docker Compose d'OMV
1. Copiez ce dépôt (ou au minimum `Dockerfile`, `docker-compose.yml`, `requirements.txt`, `audook_backend.py`, le dossier `app/`) sur le NAS
2. Éditez `docker-compose.yml` : remplacez les deux chemins d'exemple sous `volumes:` par les chemins réels du NAS (dossier de données + dossier des livres audio)
3. Dans OMV, ouvrez le plugin **Compose**, créez un nouveau fichier pointant vers ce `docker-compose.yml`, puis cliquez sur **Up**
4. Vérifiez que le service tourne : `http://<ip-du-nas>:5000/health` (ou testez `/api/books`)
5. Dans l'app mobile (ou tout client web), configurez l'URL du serveur sur `http://<ip-du-nas>:5000/api`

### Déploiement via Portainer
1. Créez une nouvelle **Stack**, collez le contenu de `docker-compose.yml` (adapté avec vos chemins réels)
2. Déployez la stack ; le conteneur `audook-nas` écoute sur le port `5000`

### Protéger l'API avec un jeton (recommandé)
Par défaut l'API du NAS est ouverte à tout le réseau local. Pour la protéger :
1. Générez un jeton long et aléatoire, par exemple `openssl rand -hex 24`
2. Mettez-le dans un fichier `.env` à côté de `docker-compose.yml` : `AUDOOK_API_TOKEN=votre-jeton` (ou remplacez la valeur dans le compose), puis redéployez
3. Dans l'app, saisissez le même jeton dans l'écran de connexion (il s'affiche tout seul avec « Accès refusé ») ou dans Paramètres > Connexion au backend > Jeton d'accès

Toutes les requêtes doivent alors porter `Authorization: Bearer <jeton>` (ou l'en-tête `X-Audook-Token`). Seul `/health` reste public (sonde de vie, sans donnée). Le flux audio `/api/cast/local-audio` accepte aussi `?token=` car ExoPlayer et les Chromecast ne peuvent pas envoyer d'en-têtes ; le jeton est masqué dans les logs. L'app Windows locale n'en a pas besoin (le backend n'écoute que sur 127.0.0.1) : ne définissez pas la variable côté desktop. Sans HTTPS, le jeton circule en clair sur le réseau local : il protège contre les accès non voulus, pas contre quelqu'un qui écoute le réseau (voir la section VPN ci-dessous pour l'accès distant).

### Accès depuis l'extérieur : un VPN plutôt que HTTPS
L'app parle en HTTP simple au NAS. Sur votre réseau local c'est acceptable (surtout avec le jeton ci-dessus), mais n'ouvrez **jamais** le port 5000 sur Internet. Pour y accéder de l'extérieur, passez par un VPN comme WireGuard : tout le trafic, jeton compris, est alors chiffré dans le tunnel, sans rien changer à l'app, et il n'y a ni certificat ni reverse proxy à gérer.

- **Conseil de configuration :** dans le profil WireGuard du téléphone, routez le sous-réseau de votre maison (par exemple `AllowedIPs = 192.168.1.0/24`, à adapter) et utilisez toujours l'adresse LAN du NAS dans l'app. Elle fonctionne alors à l'identique chez vous et à l'extérieur, sans rien reconfigurer.
- **Cast (Chromecast / Google Home) :** le Chromecast va chercher l'audio lui-même, à l'adresse que l'app lui donne, et il est découvert par mDNS sur le réseau local. Il faut donc que le téléphone soit sur le Wi-Fi de la maison : le cast ne fonctionne pas à travers le VPN.
- Gardez le jeton d'API activé même derrière le VPN : il protège aussi contre les autres appareils de votre réseau.

### Notes
- Le conteneur tourne en mode headless (`AUDOOK_HEADLESS=1`) : VLC utilise une sortie audio factice, la lecture audio se fait côté client (VLC/Chromecast desktop, ExoPlayer mobile), pas dans le conteneur
- Le port `5000` est exposé via un réseau bridge (pas de `network_mode: host`) ; adaptez le mapping de port si `5000` est déjà utilisé sur le NAS
- La progression de lecture sur des livres provenant d'un dossier local **propre au NAS** ne se synchronise pas vers le PC (limitation connue, acceptée) — seuls les livres Plex/Audiobookshelf se synchronisent entre les deux instances

## Application mobile Android (Capacitor)

L'application Android vit dans `android/` et est générée avec [Capacitor](https://capacitorjs.com/). Elle réutilise l'interface React (bibliothèque, collections, découvrir, historique, paramètres) et se connecte au backend du NAS (section précédente) via l'adresse configurée.

La lecture audio en arrière-plan (contrôles à l'écran de verrouillage, lecture continue application fermée ou écran éteint) passe par un plugin natif Kotlin (`android/app/src/main/java/com/audook/app/AudookPlayerPlugin.kt` et `AudookPlaybackService.kt`) basé sur ExoPlayer + MediaSession : un `<audio>` de WebView ne survit pas de façon fiable à la mise en veille de l'écran. Pour la même raison, le minuteur de veille et le Chromecast (Cast Sender SDK) sont implémentés côté natif.

Les APK de release se construisent avec `build-release.bat` (section suivante). Pour travailler dans Android Studio : `npm run android-sync` (build web + `cap sync android`) puis `npm run android-open`.

## Build de release

Double-cliquez sur `build-release.bat` (ou lancez-le depuis un terminal) : il construit l'installeur Windows (NSIS) et l'APK Android signé, puis les place dans le dossier `release/` (`Audook-Setup-<version>.exe` et `Audook-<version>.apk`).

- `build-release.bat -SkipAndroid` : seulement l'installeur Windows.
- `build-release.bat -SkipWindows` : seulement l'APK.
- `build-release.bat -RunTests` : lance les tests avant de construire.

Prérequis : Node.js, Python avec les dépendances de `requirements.txt` et PyInstaller, et pour l'APK le SDK Android, un JDK (celui d'Android Studio convient) et le fichier `android/keystore.properties` de la clé de signature (jamais commité, ainsi que le fichier `.jks` qu'il désigne : **sauvegardez-les hors du projet**).

L'installeur Windows (`assets/installer.nsh`, images dans `assets/installer/`) est en français, aux couleurs d'Audook, et se met à jour par-dessus l'ancienne version sans désinstallation préalable : il ferme lui-même Audook et son backend s'ils tournent encore, et ne dépend pas du désinstalleur de la version précédente.

### Changer de version

`package.json` est la seule source de la version : l'installeur Windows, l'APK (nom et code de version), les noms des fichiers de `release/`, la page Paramètres et le backend en dérivent. Pour passer à une nouvelle version :

```bash
npm version patch --no-git-tag-version   # ou minor / major / 1.2.3
```

Cela met aussi à jour `app/__init__.py`. Le code de version Android vaut `major*10000 + minor*100 + patch` (1.2.3 donne 10203) : il doit toujours augmenter pour qu'Android accepte la mise à jour, et minor/patch restent sous 100. Des tests vérifient que tout reste aligné.

## Tests

- Backend (pytest) : `pip install -r requirements-dev.txt` puis `npm run test:backend`. Les tests utilisent une base SQLite et un dossier de données temporaires : votre bibliothèque n'est jamais touchée.
- Frontend (Jest) : `npm run test:frontend`.
- Kotlin (logique pure du lecteur natif : fondu du minuteur, conversion de gain, type de contenu du cast) : `cd android && ./gradlew :app:testDebugUnitTest`.
- Backend + frontend d'un coup : `npm test`.

Une CI GitHub Actions (`.github/workflows/ci.yml`) lance les trois à chaque push sur `main` et sur chaque pull request, plus la vérification des types et le build du frontend.

Couverture actuelle : table des routes HTTP, progression (pourcentage sur tout le livre), jeton d'API, CORS, gestion des erreurs, durcissement de `/api/cast/local-audio` et `/api/shutdown`, API bibliothèque (livres, marque-pages, collections, serveurs), versions, configuration de l'installeur, minuteur de veille (fondu et annulation côté desktop et Kotlin, câblage côté mobile), hook `usePolling`. Ce qui touche directement Android (ExoPlayer, MediaSession, Chromecast réel) n'a pas de test automatisé.

## Références API

- [Documentation API Audiobookshelf](https://github.com/advplyr/audiobookshelf/wiki/API-Documentation)
- [Documentation API Plex](https://developer.plex.tv/)

## Contribution

Les contributions sont les bienvenues ! N'hésitez pas à soumettre des issues ou des pull requests.

### Directives de développement
- Python : respectez PEP 8, utilisez les annotations de type et écrivez des docstrings pour les méthodes publiques
- TypeScript : le projet est compilé en mode strict (`npx tsc --noEmit`)
- Ajoutez ou adaptez des tests pour tout comportement modifié, et vérifiez que `npm test` passe avant de proposer un changement

## Licence

Ce projet est sous licence MIT - voir le fichier [LICENSE](LICENSE) pour plus de détails.

## Remerciements

- [Audiobookshelf](https://github.com/advplyr/audiobookshelf) - Le meilleur serveur auto-hébergé pour livres audio
- [Plex](https://www.plex.tv/) - Plateforme de serveur multimédia
- [VLC](https://www.videolan.org/) - Lecteur multimédia utilisé pour la lecture sur PC
- [Electron](https://www.electronjs.org/), [React](https://react.dev/) et [Capacitor](https://capacitorjs.com/) - Socle de l'application
- [ExoPlayer / Media3](https://developer.android.com/media/media3) - Lecture native sur Android
- [PyChromecast](https://github.com/home-assistant-libs/pychromecast) - Diffusion vers Chromecast et Google Home
- [PyInstaller](https://www.pyinstaller.org/) et [electron-builder](https://www.electron.build/) - Empaquetage

## Support

Pour obtenir de l'aide, veuillez ouvrir une issue sur le [dépôt GitHub](https://github.com/pxomaker-hue/Audook).

---

**Audook** - Votre compagnon pour les livres audio sur Windows et Android 📚🎧
