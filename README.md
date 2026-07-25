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
