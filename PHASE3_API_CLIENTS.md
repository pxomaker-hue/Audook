# Phase 3: API Clients et Synchronisation

## Vue d'ensemble

Phase 3 implémente les clients API pour découvrir et synchroniser les livres audio depuis Plex et Audiobookshelf vers la base de données locale.

## Architecture

```
Serveurs (NAS)
    ├── Plex
    │   └── PlexClient (http://server:32400)
    └── Audiobookshelf
        └── AudiobookshelfClient (http://server:80)
            ↓
        ServerScanner
            ↓
        Database (SQLite)
            ↓
        UI / Player
```

## Composants implémentés

### 1. Clients API

#### PlexClient (`app/clients/plex_client.py`)
- **Connexion**: URL + Token Plex
- **Fonctionnalités**:
  - Découvrir les bibliothèques audiobook
  - Récupérer les livres audio avec métadonnées
  - Générer les URLs de streaming
  - Récupérer la progression utilisateur
  - Mettre à jour la progression utilisateur
- **Dépendance**: `python-plexapi` (optional)

#### AudiobookshelfClient (`app/clients/audiobookshelf_client.py`)
- **Connexion**: URL + Username + Password
- **Fonctionnalités**:
  - Authentification OAuth
  - Lister les bibliothèques
  - Récupérer les audiobooks avec chapitres
  - Récupérer les couvertures
  - Gestion de la progression utilisateur
  - Synchronisation bidirectionnelle
- **Dépendance**: `requests` (déjà installé)

### 2. Scanner (`app/sync/scanner.py`)

Orchestrateur principal pour la synchronisation:

```python
from app.sync import scanner

# Scan tous les serveurs configurés
scanner.scan_all_servers()

# Scan un serveur spécifique
scanner.scan_server(server_object)

# Scanner en arrière-plan (toutes les heures)
scanner.start_background_scan(interval=3600)
scanner.stop_background_scan()
```

**Processus de scan**:
1. Récupère les paramètres du serveur depuis la DB
2. Initialise le client API approprié (Plex ou ABS)
3. Récupère les audiobooks du serveur
4. Stocke/met à jour les livres en base de données
5. Met à jour le timestamp de synchronisation

## Utilisation

### Configuration des serveurs

```python
from app.database import get_session, ServerRepository

session = get_session()
repo = ServerRepository(session)

# Audiobookshelf
abs_server = repo.create(
    server_id="nas_abs",
    type="audiobookshelf",
    name="My Audiobookshelf",
    url="http://192.168.1.100:80",
    username="admin",
    password="password"
)

# Plex
plex_server = repo.create(
    server_id="nas_plex",
    type="plex",
    name="My Plex Server",
    url="http://192.168.1.100:32400",
    api_key="xxxxx"
)

session.close()
```

### Synchronisation manuelle

```python
from app.sync import scanner

# Scan tout
scanner.scan_all_servers()

# Scan un serveur
server = session.query(Server).filter_by(id="nas_abs").first()
scanner.scan_server(server)
```

### Sync en arrière-plan

```python
from app.sync import scanner

# Démarrer (scan chaque heure)
scanner.start_background_scan(interval=3600)

# Plus tard...
scanner.stop_background_scan()
```

## Format des données

### Audiobook standard

Structure commune pour tous les serveurs:

```python
{
    "id": "server_type_unique_id",
    "title": "Book Title",
    "author": "Author Name",
    "narrator": "Narrator Name",
    "description": "Description...",
    "cover_url": "http://...",
    "duration": 34200.0,  # secondes
    "chapters": [
        {
            "id": "unique_chapter_id",
            "title": "Chapter 1",
            "index": 0,
            "duration": 1200.0,
            "audio_file": "http://streaming_url"
        }
    ],
    "extra_metadata": {
        "genre": ["Fiction"],
        "language": "en",
        "publish_year": 2020,
        "series": "Series Name"
    }
}
```

## Tests

### test_player_system.py
Test complet de la chaîne Player + Database + Progress

### test_api_demo.py
Démo de l'architecture API:
- Structures de données Plex/ABS
- Intégration base de données
- Exemple d'ajout de livres

```bash
python test_api_demo.py
```

## Prochaines étapes (Phase 4)

### UI moderne (Qt6)
- Affichage des bibliothèques
- Liste des audiobooks
- Lecteur intégré
- Synchronisation visible

### Sync multi-appareils (Phase 5)
- Synchroniser la progression entre appareils
- Bi-directionnel avec serveurs

## Points techniques importants

### Streaming URLs
- **Audiobookshelf**: `/api/books/{id}/stream?token={auth_token}`
- **Plex**: `/library/parts/{id}/file.mp3?X-Plex-Token={token}`
- VLC supporte les deux formats

### Authentification
- **Plex**: Token API (long terme)
- **Audiobookshelf**: Username/Password + JWT Token (en session)

### Gestion des sessions SQLAlchemy
- Fermer les sessions après utilisation
- Éviter les objets "detached" après fermeture de session
- Copier les données avant de fermer

## Dépendances

```
requests==2.31.0           # HTTP client (pour ABS)
python-plexapi==4.15.0     # Plex API (optional)
sqlalchemy==2.0.23         # ORM
```

## État actuel

✓ PlexClient - Implémenté
✓ AudiobookshelfClient - Implémenté
✓ ServerScanner - Implémenté
✓ Intégration Database - Testée
✓ Architecture de sync - Fonctionnelle

Prêt pour Phase 4: UI moderne et affichage des audiobooks
