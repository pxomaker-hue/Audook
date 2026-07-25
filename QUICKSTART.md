# 🎧 Audook - Quick Start Guide

## Installation

```bash
# Installer les dépendances
pip install -r requirements.txt

# OU via le fichier de développement
pip install -r requirements.txt
pip install qasync pathvalidate
```

## Lancer l'Application

```bash
python main.py
```

L'application va démarrer avec une interface vide.

## Test avec une Bibliothèque Locale

### 1. Créer des Fichiers de Test

```bash
python create_test_audiobooks.py
```

Cela créera un dossier `test_audiobooks/` avec :
- 3 audiobooks de test (Les Misérables, The Great Gatsby, Pride and Prejudice)
- 8 fichiers WAV au total (60 secondes chacun)

### 2. Utiliser la Bibliothèque Local

Dans Audook:
1. Ouvrir le dropdown "Sélectionner un serveur"
2. Cliquer sur "Local"
3. Sélectionner le dossier `test_audiobooks`
4. Attendre le chargement automatique des audiobooks

### 3. Écouter un Audiobook

1. Double-cliquer sur un audiobook dans la liste
2. L'application charge automatiquement le premier chapitre
3. Cliquer sur Play pour démarrer la lecture

## Contrôles

| Bouton | Action |
|--------|--------|
| ▶️ / ⏸️ | Play / Pause |
| ⏮️ | Chapitre précédent |
| ⏭️ | Chapitre suivant |
| ⏪ | Recule de 10s |
| ⏩ | Avance de 10s |
| 🔊 | Contrôle du volume |

## Tester le Scanner Local

```bash
python test_local_scanner.py
```

Cela affichera :
- Nombre d'audiobooks trouvés
- Détails de chaque audiobook
- Chapitres détectés

## Fonctionnalités Implémentées ✅

### Architecture
- ✅ Intégration Qt6 + asyncio (qasync)
- ✅ Lecteur audio avec pygame.mixer
- ✅ Support complet des appels asynchrones

### Bibliothèques Locales
- ✅ Scanner récursif de dossiers
- ✅ Détection automatique des fichiers audio
- ✅ Support: MP3, M4B, FLAC, OGG, WAV, AAC, OPUS

### Lecture Audio
- ✅ Play / Pause / Stop
- ✅ Navigation chapitre suivant/précédent
- ✅ Seek avant/arrière (10s, 30s)
- ✅ Contrôle du volume
- ✅ Sauvegarde automatique de la position

### Serveurs Distants
- ✅ Client Audiobookshelf (structure prête)
- ✅ Client Plex (structure prête)
- 🔄 Synchronisation avec le serveur (à implémenter)

## Prochaines Étapes

### Phase 4: Synchronisation Serveur
- [ ] Implémenter la sauvegarde de position sur Audiobookshelf
- [ ] Charger la position depuis le serveur
- [ ] Support des signets (bookmarks)

### Phase 5: Améliorations UI
- [ ] Afficher les images de couverture
- [ ] Meilleur affichage de la durée
- [ ] Barre de progression en temps réel
- [ ] Miniatures de chapitres

### Phase 6: Fonctionnalités Avancées
- [ ] Vitesse de lecture (0.5x à 2.0x)
- [ ] Édition de marquepages
- [ ] Recherche par titre/auteur
- [ ] Intégration Plex complète
- [ ] Cache local des chapitres
- [ ] Synchronisation multi-appareils

## Dépannage

### Application qui ne démarre pas
```bash
# Vérifier l'installation des dépendances
pip install -r requirements.txt

# Vérifier la version de Python (3.10+)
python --version
```

### Erreurs d'import
```bash
# Réinstaller dans un venv propre
python -m venv venv
venv\Scripts\activate  # ou source venv/bin/activate
pip install -r requirements.txt
```

### Pas de son
- Vérifier les fichiers WAV dans le dossier `test_audiobooks/`
- Vérifier le volume du système
- Vérifier que pygame.mixer est bien initialisé

## Architecture du Code

```
app/
├── main_window.py          # Fenêtre principale
├── models/                 # Modèles de données
├── audiobookshelf/         # Client Audiobookshelf
├── plex/                   # Client Plex
├── local/                  # Support répertoires locaux
│   ├── scanner.py          # Scanner de fichiers audio
│   └── client.py           # Client abstrait
├── player/                 # Lecteur audio
│   ├── player.py           # Implémentation pygame
│   └── queue.py            # File d'attente
├── ui/                     # Composants UI
│   ├── library_view.py     # Navigateur de bibliothèque
│   ├── player_view.py      # Contrôles de lecteur
│   └── settings_view.py    # Dialogue de paramètres
└── utils/                  # Utilitaires
```

## Support

Pour toute question ou problème, consultez les logs :
```
app/logs/audook.log
```
