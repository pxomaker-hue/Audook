# Audook - Client Audiobook pour Windows

Un lecteur de livres audio moderne et riche en fonctionnalités pour Windows qui prend en charge les serveurs **Audiobookshelf** et **Plex**.

## Fonctionnalités

### Fonctionnalités principales
- ✅ Connexion aux serveurs **Audiobookshelf**
- ✅ Connexion aux serveurs **Plex**
- ✅ Parcourir les bibliothèques de livres audio
- ✅ Lire les livres audio avec prise en charge des chapitres
- ✅ Interface moderne avec thèmes sombre et clair

### Fonctionnalités de lecture
- ✅ Contrôles Lecture/Pause/Arrêt
- ✅ Navigation entre chapitres (Précédent/Suivant)
- ✅ **Reculer/Avancer de 10s et 30s**
- ✅ Vitesse de lecture ajustable (0,5x - 2,0x)
- ✅ Contrôle du volume
- ✅ **Mémorisation de la position de lecture entre les sessions**
- ✅ Barre de progression avec affichage du temps

### Fonctionnalités de bibliothèque
- ✅ Parcourir les livres audio par bibliothèque
- ✅ Rechercher des livres audio
- ✅ Afficher les métadonnées des livres (titre, auteur, narrateur, durée)
- ✅ **Marque-pages** pour sauvegarder les positions
- ✅ **Téléchargement des livres audio pour écoute hors ligne**

### Fonctionnalités de synchronisation
- ✅ **Synchronisation de la position de lecture avec le serveur** (Audiobookshelf & Plex)
- ✅ **Synchronisation multi-appareils** (via la synchronisation serveur)

### Paramètres
- ✅ Ajouter/Modifier/Supprimer plusieurs serveurs
- ✅ Basculer entre Audiobookshelf et Plex
- ✅ Thèmes sombre et clair
- ✅ Configurer les paramètres de lecture par défaut

## Captures d'écran

*(Les captures d'écran seront ajoutées dans les versions futures)*

## Installation

### Prérequis
- Windows 10 ou 11
- Python 3.10 ou supérieur (pour le développement)

### Installation rapide (via l'installateur)
1. Téléchargez le dernier installateur depuis la page [Releases](https://github.com/pxomaker-hue/Audook/releases)
2. Exécutez l'installateur et suivez les instructions
3. Lancez Audook depuis le menu Démarrer ou le raccourci bureau

### Configuration pour le développement
1. Clonez ce dépôt :
 ```bash
 git clone https://github.com/pxomaker-hue/Audook.git
 cd Audook
 ```

2. Créez un environnement virtuel :
 ```bash
 python -m venv venv
 source venv/bin/activate # Sur Windows : venv\Scripts\activate
 ```

3. Installez les dépendances :
 ```bash
 pip install -r requirements.txt
 ```

4. Lancez l'application :
 ```bash
 python main.py
 ```

### Création de l'exécutable

Pour créer un exécutable Windows autonome :

1. Installez PyInstaller :
 ```bash
 pip install pyinstaller
 ```

2. Exécutez le script de build :
 ```bash
 python build_spec.py
 ```
 ou double-cliquez sur `build.bat`

3. L'exécutable sera créé dans le dossier `dist/`

### Création d'un installateur

Pour créer un installateur Windows professionnel :

1. Installez [Inno Setup](https://jrsoftware.org/isinfo.php)
2. Exécutez le script de build (il créera automatiquement l'installateur si Inno Setup est installé)
3. L'installateur sera dans le dossier `dist/` sous le nom `Audook_Setup.exe`

## Utilisation

### Ajouter un serveur

1. Cliquez sur le bouton **Paramètres** (⚙️) en haut à droite
2. Allez dans l'onglet **Serveurs**
3. Cliquez sur **Ajouter un serveur**
4. Entrez les détails du serveur :
 - **Nom** : Un nom convivial pour le serveur
 - **Type** : Audiobookshelf ou Plex
 - **URL** : L'URL du serveur (ex: `http://votre-nas:13378` pour Audiobookshelf)
 - **Clé API** : Pour Audiobookshelf (à trouver dans Paramètres > Utilisateurs > Votre utilisateur > Clé API)
 - **Nom d'utilisateur/Mot de passe** : Pour Plex
5. Cliquez sur **Enregistrer**

### Parcourir les livres audio

1. Sélectionnez un serveur dans la liste déroulante de la vue bibliothèque
2. Sélectionnez une bibliothèque
3. Parcourez ou recherchez des livres audio
4. Double-cliquez sur un livre audio pour commencer la lecture

### Contrôles de lecture

- **Espace** : Lecture/Pause
- **Flèche gauche** : Reculer de 10 secondes
- **Flèche droite** : Avancer de 10 secondes
- **Ctrl+Flèche gauche** : Reculer de 30 secondes
- **Ctrl+Flèche droite** : Avancer de 30 secondes
- **Flèche haut** : Chapitre précédent
- **Flèche bas** : Chapitre suivant

### Raccourcis clavier

| Raccourci | Action |
|-----------|--------|
| Espace | Lecture/Pause |
| ← | Reculer de 10s |
| → | Avancer de 10s |
| Ctrl+← | Reculer de 30s |
| Ctrl+→ | Avancer de 30s |
| ↑ | Chapitre précédent |
| ↓ | Chapitre suivant |
| Ctrl+↑ | Augmenter le volume |
| Ctrl+↓ | Diminuer le volume |
| Ctrl+F | Rechercher |
| Ctrl+, | Paramètres |

## Configuration

Toute la configuration est stockée dans :
- `%USERPROFILE%\.Audook\config.json` - Configuration principale
- `%USERPROFILE%\.Audook\playback_state.json` - État de lecture
- `%USERPROFILE%\.Audook\bookmarks.json` - Marque-pages
- `%USERPROFILE%\.Audook\cache\` - Fichiers audio en cache

## Résolution des problèmes

### Problèmes de connexion
- **Audiobookshelf** : Vérifiez que l'URL du serveur est correcte et que la clé API est valide
- **Plex** : Vérifiez que l'URL du serveur est correcte et que vous avez les identifiants corrects
- Vérifiez que votre NAS/serveur est accessible depuis votre machine Windows

### Problèmes de lecture
- Assurez-vous d'avoir une connexion Internet active (pour le streaming)
- Pour l'écoute hors ligne, téléchargez d'abord le livre audio
- Vérifiez que votre périphérique audio fonctionne correctement

### Problèmes de performance
- Réduisez le nombre de livres audio chargés en même temps
- Effacez le cache s'il prend trop de place
- Utilisez un paramètre de qualité plus faible pour les téléchargements

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
4. Vérifiez que le service tourne : `http://<ip-du-nas>:5000/api/health` (ou testez `/api/books`)
5. Dans l'app mobile (ou tout client web), configurez l'URL du serveur sur `http://<ip-du-nas>:5000/api`

### Déploiement via Portainer
1. Créez une nouvelle **Stack**, collez le contenu de `docker-compose.yml` (adapté avec vos chemins réels)
2. Déployez la stack ; le conteneur `audook-nas` écoute sur le port `5000`

### Protéger l'API avec un jeton (recommandé)
Par défaut l'API du NAS est ouverte à tout le réseau local. Pour la protéger :
1. Générez un jeton long et aléatoire, par exemple `openssl rand -hex 24`
2. Mettez-le dans un fichier `.env` à côté de `docker-compose.yml` : `AUDOOK_API_TOKEN=votre-jeton` (ou remplacez la valeur dans le compose), puis redéployez
3. Dans l'app, saisissez le même jeton dans l'écran de connexion (il s'affiche tout seul avec « Accès refusé ») ou dans Paramètres > Connexion au backend > Jeton d'accès

Toutes les requêtes doivent alors porter `Authorization: Bearer <jeton>` (ou l'en-tête `X-Audook-Token`). Seul `/health` reste public (sonde de vie, sans donnée). Le flux audio `/api/cast/local-audio` accepte aussi `?token=` car ExoPlayer et les Chromecast ne peuvent pas envoyer d'en-têtes ; le jeton est masqué dans les logs. L'app Windows locale n'en a pas besoin (le backend n'écoute que sur 127.0.0.1) : ne définissez pas la variable côté desktop. Sans HTTPS, le jeton circule en clair sur le réseau local : il protège contre les accès non voulus, pas contre quelqu'un qui écoute le réseau.

### Notes
- Le conteneur tourne en mode headless (`AUDOOK_HEADLESS=1`) : VLC utilise une sortie audio factice, la lecture audio se fait côté client (VLC/Chromecast desktop, ExoPlayer mobile), pas dans le conteneur
- Le port `5000` est exposé via un réseau bridge (pas de `network_mode: host`) ; adaptez le mapping de port si `5000` est déjà utilisé sur le NAS
- La progression de lecture sur des livres provenant d'un dossier local **propre au NAS** ne se synchronise pas vers le PC (limitation connue, acceptée) — seuls les livres Plex/Audiobookshelf se synchronisent entre les deux instances

## Application mobile Android (Capacitor)

Une app Android (APK) installable existe dans `android/`, générée via [Capacitor](https://capacitorjs.com/). Elle réutilise l'interface React existante (bibliothèque, collections, découvrir, historique, paramètres) et se connecte au backend NAS ci-dessus via l'adresse configurée dans **Paramètres > Connexion au backend**.

La lecture audio en arrière-plan (contrôles à l'écran de verrouillage, lecture continue app fermée/écran éteint) passe par un plugin natif Kotlin (`android/app/src/main/java/com/audook/app/AudookPlayerPlugin.kt` + `AudookPlaybackService.kt`) basé sur ExoPlayer + MediaSession — un `<audio>` de WebView ne survit pas de façon fiable à la mise en veille de l'écran sur Android.

### Générer l'APK

Cet environnement de développement n'a pas de SDK Android/Gradle/JDK installés — le code natif (plugin Kotlin, projet Gradle sous `android/`) et le code JS (hook `useMobilePlayerState`, wrapper de plugin) sont prêts et committés, mais la compilation de l'APK doit se faire manuellement :

1. Installez [Android Studio](https://developer.android.com/studio) (gratuit) — il installe le SDK Android et Gradle nécessaires
2. `npm run react-build` puis `npm run android-sync` (build web React + `cap sync android`)
3. `npm run android-open` (ou ouvrez directement le dossier `android/` dans Android Studio)
4. Dans Android Studio : **Build > Build Bundle(s) / APK(s) > Build APK(s)**
5. L'APK signé (debug) se trouve dans `android/app/build/outputs/apk/debug/`
6. Installez-le sur le téléphone (`adb install ...` ou transfert manuel + activation des sources inconnues), puis réglez l'adresse du serveur dans Paramètres vers l'IP LAN du NAS (ex: `http://192.168.1.50:5000/api`)

Pour une release signée (Play Store ou distribution directe), suivez le flux standard **Build > Generate Signed Bundle / APK** d'Android Studio (nécessite de créer un keystore).

## Build de release

Double-clique sur `build-release.bat` (ou lance-le depuis un terminal) : il construit l'installeur Windows (NSIS) et l'APK Android signé, puis les place dans le dossier `release/` (`Audook-Setup-<version>.exe` et `Audook-<version>.apk`).

- `build-release.bat -SkipAndroid` : seulement l'installeur Windows.
- `build-release.bat -SkipWindows` : seulement l'APK.
- `build-release.bat -RunTests` : lance les tests avant de construire.

Prérequis : Node.js, Python avec les dépendances de `requirements.txt` et PyInstaller, et pour l'APK le SDK Android, un JDK (celui d'Android Studio convient) et le fichier `android/keystore.properties` de la clé de signature (jamais commité).

### Changer de version

`package.json` est la seule source de la version : l'installeur Windows, l'APK (nom et code de version), les noms des fichiers de `release/`, la page Paramètres et le backend en dérivent. Pour passer à une nouvelle version :

```bash
npm version patch --no-git-tag-version   # ou minor / major / 1.2.3
```

Cela met aussi à jour `app/__init__.py`. Le code de version Android vaut `major*10000 + minor*100 + patch` (1.2.3 donne 10203) : il doit toujours augmenter pour qu'Android accepte la mise à jour, et minor/patch restent sous 100. Des tests vérifient que tout reste aligné.

## Tests

- Backend (pytest) : `pip install -r requirements-dev.txt` puis `npm run test:backend`. Les tests utilisent une base SQLite et un dossier de données temporaires : ta bibliothèque n'est jamais touchée.
- Frontend (Jest) : `npm run test:frontend`.
- Les deux d'un coup : `npm test`.

Couverture actuelle : table des routes HTTP, progression (pourcentage sur tout le livre), durcissement de `/api/cast/local-audio` et `/api/shutdown`, API bibliothèque (livres, marque-pages, collections, serveurs), minuteur de veille (fondu/annulation côté desktop, câblage côté mobile) et hook `usePolling`. Le code Kotlin n'a pas de tests automatisés.

## Références API

- [Documentation API Audiobookshelf](https://github.com/advplyr/audiobookshelf/wiki/API-Documentation)
- [Documentation API Plex](https://developer.plex.tv/)

## Contribution

Les contributions sont les bienvenues ! N'hésitez pas à soumettre des issues ou des pull requests.

### Directives de développement
- Respectez le guide de style PEP 8
- Utilisez les annotations de type
- Écrivez des docstrings pour toutes les méthodes publiques
- Gardez le code propre et bien organisé

## Licence

Ce projet est sous licence MIT - voir le fichier [LICENCE](LICENSE) pour plus de détails.

## Remerciements

- [Audiobookshelf](https://github.com/advplyr/audiobookshelf) - Le meilleur serveur auto-hébergé pour livres audio
- [Plex](https://www.plex.tv/) - Plateforme de serveur multimédia
- [PyQt6](https://www.riverbankcomputing.com/static/Docs/PyQt6/) - Liaisons Python pour Qt
- [PyInstaller](https://www.pyinstaller.org/) - Empaquetage d'applications Python

## Support

Pour obtenir de l'aide, veuillez ouvrir une issue sur le [dépôt GitHub](https://github.com/pxomaker-hue/Audook).

---

**Audook** - Votre compagnon parfait pour les livres audio sur Windows ! 📚🎧
