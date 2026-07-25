# Documentation de l'API Audook

Ce document décrit l'API interne et l'architecture d'Audook.

## Aperçu de l'architecture

Audook suit une architecture modulaire avec les principaux composants suivants :

```
Audook/
├── main.py # Point d'entrée
├── app/
│ ├── __init__.py # Constantes et chemins de l'application
│ ├── main_window.py # Fenêtre principale de l'application
│ ├── models/ # Modèles de données (Pydantic)
│ │ └── __init__.py # Audiobook, Chapter, Library, etc.
│ ├── audiobookshelf/ # Intégration Audiobookshelf
│ │ ├── __init__.py
│ │ └── client.py # Client API Audiobookshelf
│ ├── plex/ # Intégration Plex
│ │ ├── __init__.py
│ │ └── client.py # Client API Plex
│ ├── player/ # Lecture audio
│ │ ├── __init__.py
│ │ ├── player.py # Lecteur principal (PyGame)
│ │ └── queue.py # File d'attente de lecture
│ ├── ui/ # Interface utilisateur
│ │ ├── __init__.py # Styles et thèmes
│ │ ├── keyboard_shortcuts.py
│ │ ├── library_view.py # Navigateur de bibliothèque
│ │ ├── player_view.py # Contrôles du lecteur
│ │ └── settings_view.py # Dialogue des paramètres
│ └── utils/ # Utilitaires
│ ├── __init__.py
│ ├── config_manager.py # Gestion de la configuration
│ ├── defaults.py # Valeurs par défaut
│ ├── downloader.py # Téléchargement de fichiers
│ ├── notifications.py # Notifications
│ └── sync.py # Synchronisation serveur
├── assets/ # Ressources statiques
│ └── icons/ # Icônes de l'application
├── dist/ # Exécutables (générés)
├── build/ # Fichiers de build (générés)
├── requirements.txt # Dépendances Python
├── setup.py # Script d'installation
├── build_spec.py # Spécification PyInstaller
├── build.bat # Script de build Windows
├── installer.iss # Script Inno Setup
├── README.md # Documentation utilisateur
├── LICENSE # Licence
└── test_app.py # Suite de tests
```

## Modèles de données

### Modèles principaux

#### Audiobook
Représente un livre audio avec métadonnées et chapitres.

```python
from app.models import Audiobook

audiobook = Audiobook(
 id="id-unique",
 library_id="id-bibliothèque",
 title="Titre du livre",
 author="Auteur",
 narrator="Narrateur",
 description="Description du livre",
 cover="/chemin/vers/couverture.jpg",
 duration=3600.0, # en secondes
 chapters=[...], # Liste de dictionnaires de chapitres
 metadata={...}, # Métadonnées supplémentaires
 source="audiobookshelf", # ou "plex"
 local_path=None, # Chemin si téléchargé
 is_downloaded=False
)
```

#### Chapter
Représente un chapitre dans un livre audio.

```python
chapter = {
 "id": "id-chapitre",
 "title": "Chapitre 1",
 "index": 0,
 "duration": 1800.0, # en secondes
 "start": 0.0, # position de départ dans le livre
 "audio_file": "/chemin/vers/audio.mp3"
}
```

#### Library
Représente une bibliothèque sur le serveur.

```python
from app.models import Library

library = Library(
 id="id-bibliothèque",
 name="Nom de la bibliothèque",
 source="audiobookshelf", # ou "plex"
 server_url="http://serveur:port",
 server_name="Nom du serveur"
)
```

#### ServerConfig
Configuration pour une connexion serveur.

```python
from app.models import ServerConfig

server = ServerConfig(
 id="id-serveur",
 name="Mon serveur",
 type="audiobookshelf", # ou "plex"
 url="http://localhost:13378",
 api_key="votre-clé-api", # Pour Audiobookshelf
 username="utilisateur", # Pour Plex
 password="motdepasse", # Pour Plex
 libraries=["bib1", "bib2"] # IDs des bibliothèques
)
```

### Modèles d'état

#### PlaybackState
État actuel de la lecture.

```python
from app.models import PlaybackState

state = PlaybackState(
 book_id="id-livre",
 library_id="id-bibliothèque",
 chapter_id="id-chapitre",
 position=600.0, # en secondes
 is_playing=True,
 speed=1.0,
 last_updated=datetime.now()
)
```

#### Bookmark
Position sauvegardée dans un livre audio.

```python
from app.models import Bookmark

bookmark = Bookmark(
 book_id="id-livre",
 library_id="id-bibliothèque",
 chapter_id="id-chapitre",
 position=600.0, # en secondes
 timestamp=datetime.now(),
 title="Mon marque-page"
)
```

## Clients API

### AudiobookshelfClient

Se connecte à un serveur Audiobookshelf.

```python
from app.audiobookshelf.client import AudiobookshelfClient

async with AudiobookshelfClient("http://localhost:13378", "clé-api") as client:
 # Obtenir les bibliothèques
 libraries = await client.get_libraries()
 
 # Obtenir les livres audio
 audiobooks = await client.get_audiobooks("id-bibliothèque", limit=100)
 
 # Obtenir un livre audio spécifique
 audiobook = await client.get_audiobook("id-bibliothèque", "id-livre")
 
 # Obtenir l'URL audio d'un chapitre
 url = await client.get_chapter_audio_url("id-bibliothèque", "id-livre", "id-chapitre")
 
 # Rechercher
 results = await client.search("id-bibliothèque", "requête", limit=20)
 
 # Obtenir la progression de l'utilisateur
 progress = await client.get_user_progress("id-bibliothèque", "id-livre")
 
 # Mettre à jour la progression de l'utilisateur
 await client.update_user_progress("id-bibliothèque", "id-livre", "id-chapitre", 600.0, 1800.0)
```

### PlexClient

Se connecte à un serveur Plex Media Server.

```python
from app.plex.client import PlexClient

async with PlexClient("http://localhost:32400", "jeton-plex") as client:
 # Obtenir les bibliothèques
 libraries = await client.get_libraries()
 
 # Obtenir les livres audio
 audiobooks = await client.get_audiobooks("id-bibliothèque", limit=100)
 
 # Obtenir un livre audio spécifique
 audiobook = await client.get_audiobook("id-bibliothèque", "id-livre")
 
 # Obtenir l'URL audio d'un chapitre
 url = await client.get_chapter_audio_url("id-bibliothèque", "id-livre", "id-chapitre")
 
 # Rechercher
 results = await client.search("id-bibliothèque", "requête", limit=20)
 
 # Obtenir la progression de l'utilisateur
 progress = await client.get_user_progress("id-livre")
 
 # Mettre à jour la progression de l'utilisateur
 await client.update_user_progress("id-livre", 600.0)
```

## Lecteur

### AudioPlayer

Gère la lecture audio avec PyGame.

```python
from app.player.player import player

# Lire un chapitre de livre audio
player.play(audiobook, chapter, start_position=0.0)

# Contrôler la lecture
player.pause()
player.resume()
player.stop()
player.toggle_play_pause()

# Rechercher
player.seek(600.0) # Position absolue en secondes
player.seek_relative(-10.0) # Recherche relative (recule de 10 secondes)

# Navigation
player.next_chapter()
player.previous_chapter()

# Volume et vitesse
player.set_volume(0.8) # 0.0 à 1.0
player.set_speed(1.25) # 0.5 à 2.0

# Obtenir l'état
position = player.get_current_position()
duration = player.get_current_duration()
is_playing = player.is_playing()
progress = player.get_progress_percent()
```

### PlaybackQueue

Gère la file d'attente de lecture.

```python
from app.player.queue import queue

# Ajouter des éléments
queue.add(audiobook, chapter)
queue.add_audiobook(audiobook) # Ajoute tous les chapitres

# Navigation
queue.get_current() # Élément actuel
queue.get_next() # Élément suivant (et avance)
queue.get_previous() # Élément précédent (et recule)
queue.set_current(index) # Définit l'index actuel

# Gestion de la file
queue.clear()
queue.remove(index)
queue.size()
queue.is_empty()

# Paramètres
queue.set_repeat(True)
queue.set_shuffle(True)
```

## Configuration

### ConfigManager

Gère la configuration de l'application.

```python
from app.utils.config_manager import config_manager

# Obtenir la configuration
config = config_manager.config

# Gestion des serveurs
config_manager.add_server(server_config)
config_manager.remove_server(server_id)
config_manager.set_current_server(server_id)
config_manager.get_current_server()
config_manager.get_server_by_id(server_id)

# État de lecture
config_manager.update_playback_state(state)
config_manager.save_playback_state()

# Marque-pages
config_manager.add_bookmark(bookmark)
config_manager.remove_bookmark(book_id)
config_manager.get_bookmark(book_id)

# Tout sauvegarder
config_manager.save_config()
```

## Utilitaires

### Mise en forme

```python
from app.utils import format_duration, format_time_short, time_ago

# Formater la durée
format_duration(3661) # "01:01:01"
format_duration(60) # "01:00"

# Format court
format_time_short(3661) # "1h 1m"
format_time_short(60) # "1m 0s"

# Temps écoulé
time_ago(datetime.now() - timedelta(hours=2)) # "il y a 2h"
```

### Downloader

```python
from app.utils.downloader import downloader

# Télécharger un fichier
task_id = downloader.download(
 url="http://exemple.com/fichier.mp3",
 output_path=Path("cache/fichier.mp3"),
 callback=lambda success, error: print(f"Terminé : {success}"),
 progress_callback=lambda downloaded, total: print(f"{downloaded}/{total}")
)

# Télécharger un chapitre
task_id = downloader.download_chapter(
 server_type="audiobookshelf",
 server_url="http://localhost:13378",
 api_key="clé-api",
 library_id="id-bib",
 book_id="id-livre",
 chapter_id="id-chapitre"
)

# Annuler un téléchargement
downloader.cancel_task(task_id)
```

### Sync Manager

```python
from app.utils.sync import sync_manager

# Démarrer/arrêter la synchronisation
sync_manager.start()
sync_manager.stop()

# Synchronisation manuelle
await sync_manager.sync_all()
await sync_manager.sync_playback_state()
await sync_manager.sync_bookmarks()

# Récupérer la progression du serveur
progress = await sync_manager.fetch_server_progress(library_id, book_id)
```

## Composants UI

### MainWindow

La fenêtre principale de l'application.

```python
from app.main_window import MainWindow

window = MainWindow()
window.show()
```

### LibraryView

Affiche la bibliothèque de livres audio.

```python
from app.ui.library_view import LibraryView

library_view = LibraryView()

# Définir les données
library_view.set_servers([server1, server2])
library_view.set_libraries([lib1, lib2])
library_view.set_audiobooks([book1, book2])

# Signaux
library_view.audiobook_selected.connect(lambda book, chapter: ...)
library_view.audiobook_double_clicked.connect(lambda book: ...)
library_view.library_changed.connect(lambda lib_id: ...)
library_view.server_changed.connect(lambda server_id: ...)
library_view.refresh_requested.connect(lambda: ...)
library_view.search_requested.connect(lambda query: ...)
library_view.download_requested.connect(lambda book: ...)
```

### PlayerView

Affiche les contrôles du lecteur et les informations de lecture actuelles.

```python
from app.ui.player_view import PlayerView

player_view = PlayerView()

# Définir le livre audio actuel
player_view.set_audiobook(audiobook, chapter)

# Signaux
player_view.play_pause_clicked.connect(lambda: ...)
player_view.previous_clicked.connect(lambda: ...)
player_view.next_clicked.connect(lambda: ...)
player_view.seek_backward_clicked.connect(lambda seconds: ...)
player_view.seek_forward_clicked.connect(lambda seconds: ...)
player_view.volume_changed.connect(lambda volume: ...)
player_view.speed_changed.connect(lambda speed: ...)
```

### SettingsView

Affiche les paramètres de l'application.

```python
from app.ui.settings_view import SettingsView

settings_view = SettingsView()
settings_view.show()

# Signaux
settings_view._server_settings.server_added.connect(lambda server: ...)
settings_view._server_settings.server_updated.connect(lambda server: ...)
settings_view._server_settings.server_removed.connect(lambda server_id: ...)
```

## Raccourcis clavier

```python
from app.ui.keyboard_shortcuts import KeyboardShortcuts

shortcuts = KeyboardShortcuts(main_window)

# Ajouter un raccourci individuel
shortcuts.add_shortcut("Ctrl+F", search_function)

# Ajouter les raccourcis du lecteur
shortcuts.setup_player_shortcuts(
 play_pause=player.toggle_play_pause,
 previous=player.previous_chapter,
 next_chapter=player.next_chapter,
 seek_backward_10=lambda: player.seek_relative(-10),
 seek_forward_10=lambda: player.seek_relative(10),
 seek_backward_30=lambda: player.seek_relative(-30),
 seek_forward_30=lambda: player.seek_relative(30),
 increase_volume=lambda: player.set_volume(min(1.0, player.get_volume() + 0.1)),
 decrease_volume=lambda: player.set_volume(max(0.0, player.get_volume() - 0.1))
)

# Ajouter les raccourcis de navigation
shortcuts.setup_navigation_shortcuts(
 search=lambda: ..., # Afficher la recherche
 settings=lambda: ..., # Afficher les paramètres
 library=lambda: ..., # Afficher la bibliothèque
 queue=lambda: ..., # Afficher la file d'attente
 bookmarks=lambda: ... # Afficher les marque-pages
)
```

## Thèmes

```python
from app.ui import apply_theme, get_stylesheet

# Appliquer un thème à l'application
apply_theme(app, "dark") # ou "light"

# Obtenir la feuille de style
stylesheet = get_stylesheet("dark")
```

## Notifications

```python
from app.utils.notifications import notification_manager

# Afficher des messages
notification_manager.show_info("Titre", "Message")
notification_manager.show_warning("Titre", "Message")
notification_manager.show_error("Titre", "Message")

# Message temporaire dans la barre de statut
notification_manager.show_temporary_message("Chargement...", 3000)

# Configurer l'icône de la barre des tâches
notification_manager.setup_tray_icon(QIcon("icon.png"), "Audook")
notification_manager.show_tray_notification("Titre", "Message")
```

## Gestion des erreurs

Audook utilise la gestion des exceptions intégrée de Python. Pour les opérations asynchrones :

```python
try:
 result = await some_async_function()
except Exception as e:
 logger.error(f"Erreur : {e}")
 notification_manager.show_error("Erreur", str(e))
```

## Journalisation

```python
from app.utils import logger

logger.debug("Message de débogage")
logger.info("Message d'information")
logger.warning("Message d'avertissement")
logger.error("Message d'erreur")
logger.critical("Message critique")
```

## Bonnes pratiques

1. **Opérations asynchrones** : Utilisez `asyncio` pour les opérations liées à l'E/S (appels API, téléchargements de fichiers)
2. **Threading** : Utilisez des threads pour les opérations liées au CPU qui bloqueraient l'UI
3. **Gestion des erreurs** : Attrapez et journalisez toujours les exceptions
4. **Gestion des ressources** : Utilisez des gestionnaires de contexte (`with`, `async with`) pour les ressources
5. **Mises à jour de l'UI** : Ne mettez à jour l'UI que depuis le thread principal
6. **Configuration** : Utilisez `config_manager` pour tous les besoins de configuration
7. **Gestion de l'état** : Utilisez les singletons player et queue pour l'état de lecture

## Étendre Audook

Pour ajouter une nouvelle fonctionnalité :

1. **Nouveau type de serveur** : Créez un nouveau client dans un nouveau module sous `app/`
2. **Nouveau composant UI** : Créez un nouveau widget dans `app/ui/`
3. **Nouvel utilitaire** : Ajoutez à `app/utils/`
4. **Nouveau modèle** : Ajoutez à `app/models/__init__.py`

Tout le nouveau code doit suivre les modèles et le style existants.
