# Phase 4: Modern UI Implementation

## Vue d'ensemble

Phase 4 implémente une interface utilisateur moderne et épurée basée sur PyQt6, avec:
- Navigation latérale intuitive
- Affichage des audiobooks en grille
- Lecteur intégré avec contrôles complets
- Recherche et exploration
- Design minimaliste avec beaucoup d'espace blanc

## Architecture UI

```
MainWindow (QMainWindow)
    ├── Sidebar Navigation
    │   ├── My Library
    │   ├── Explore
    │   ├── History
    │   └── Settings
    │
    ├── Pages (QStackedWidget)
    │   ├── HomePage
    │   │   ├── BookCard (grid)
    │   │   └── Search box
    │   │
    │   ├── ExplorePage
    │   │   ├── Featured book section
    │   │   ├── Recommended books grid
    │   │   └── Search box
    │   │
    │   └── Future pages...
    │
    └── PlayerWidget (Bottom bar)
        ├── Now playing info
        ├── Progress slider
        ├── Playback controls
        └── Volume control
```

## Composants implémentés

### 1. **MainWindow** (`app/ui/main_window.py`)

Fenêtre principale orchestrant l'application:
- Création du sidebar
- Gestion des pages via QStackedWidget
- Intégration du lecteur
- Gestion des signaux et événements

```python
from app.ui import MainWindow
from PyQt6.QtWidgets import QApplication

app = QApplication(sys.argv)
window = MainWindow()
window.show()
app.exec()
```

### 2. **Pages**

#### HomePage (`app/ui/pages/home.py`)
- Affichage de la bibliothèque personnelle
- Grille de livres avec couvertures
- Recherche en temps réel
- Bouton de synchronisation

#### ExplorePage (`app/ui/pages/explore.py`)
- Section "Book of the Day" en vedette
- Livres recommandés en grille horizontale
- Recherche globale
- Descriptions et noter des livres

### 3. **Widgets**

#### BookCard (`app/ui/widgets/book_card.py`)
Composant réutilisable affichant un audiobook:
```python
card = BookCard(
    book_id="book_123",
    title="The Great Gatsby",
    author="F. Scott Fitzgerald",
    rating=4.5,
    cover_url="/path/to/cover.jpg"
)

# Signaux
card.play_clicked.connect(on_play)
card.cover_clicked.connect(on_book_click)
```

Affiche:
- Couverture avec icône de lecture
- Titre et auteur
- Note avec étoiles
- Bouton Play

#### PlayerWidget (`app/ui/widgets/player_widget.py`)
Barre de lecteur intégrée en bas de l'écran:

```python
player = PlayerWidget()

# Mise à jour
player.set_now_playing("Title", "Artist")
player.update_progress(current_ms, duration_ms)

# Signaux
player.play_pause.connect(handler)
player.seek.connect(handler)
player.volume_changed.connect(handler)
```

Fonctionnalités:
- Affichage du livre en cours
- Barre de progression avec temps
- Boutons Play/Pause/Suivant/Précédent
- Contrôle de volume
- Temps formaté MM:SS

### 4. **Styles** (`app/ui/styles.py`)

Stylesheet QSS global et palettes de couleurs:

```python
from app.ui.styles import MAIN_STYLESHEET, COLORS

# Couleurs
COLORS = {
    "primary": "#000000",
    "accent": "#ffd700",
    "background": "#fafafa",
    "text": "#000000",
    "text_secondary": "#666666",
}
```

Design principles:
- Palette noir/blanc/or
- Beaucoup d'espace blanc
- Transitions fluides
- Boutons arrondis (8px)
- Icônes Unicode

## Lancement de l'application

### Ligne de commande
```bash
python audook.py
```

### Comme module
```python
from app.ui import MainWindow
from PyQt6.QtWidgets import QApplication

app = QApplication([])
window = MainWindow()
window.show()
app.exec()
```

## Flux utilisateur actuel

1. **Lancement** → Initialisation de la DB → Affichage UI
2. **Sélection du livre** → Chargement en base → Affichage du lecteur
3. **Lecture** → Contrôles du lecteur → Mise à jour du progress
4. **Navigation** → Changement de page via sidebar

## Prochaines intégrations (Phase 5)

### Backend - UI
- [x] Charger les livres depuis la base de données
- [ ] Afficher les données réelles des serveurs
- [ ] Mise en cache des couvertures
- [ ] Threading pour requêtes DB

### Player - UI
- [ ] Affichage live de la progression
- [ ] Mise à jour en temps réel du lecteur
- [ ] Gestion des chapitres
- [ ] Sauvegarde automatique de la progression

### Recherche
- [ ] Requête DB en temps réel
- [ ] Filtrage par auteur/genre
- [ ] Historique de recherche

### Fonctionnalités avancées
- [ ] Page d'historique de lecture
- [ ] Marques-pages
- [ ] Notes personnelles
- [ ] Partage de progression
- [ ] Historique d'écoute

## Structure des fichiers

```
app/ui/
├── __init__.py              # Exports du module
├── main_window.py           # Fenêtre principale
├── styles.py                # Stylesheet et couleurs
│
├── pages/
│   ├── __init__.py
│   ├── home.py             # Page bibliothèque
│   ├── explore.py          # Page exploration
│   └── ...                 # Pages futures
│
└── widgets/
    ├── __init__.py
    ├── book_card.py        # Composant livre
    ├── player_widget.py    # Lecteur
    └── ...                 # Widgets futurs

audook.py                    # Point d'entrée principal
```

## State & Signals

Chaque page et widget utilise les signaux PyQt6 pour la communication:

```python
# Pages émettent des signaux
home_page.book_selected.connect(window.on_book_selected)

# Widgets émettent des signaux
player.play_pause.connect(window.on_play_pause)
player.seek.connect(window.on_seek)

# MainWindow gère les connexions
window.connect_signals()
```

## Responsive Design

L'interface s'adapte à différentes tailles:
- Minimum: 1400x900 (testé)
- Scalable: QScrollArea pour long lists
- Sidebar fixe: 200px
- Grille adaptative: 4 colonnes

## Performance Notes

- Lazy loading des couvertures
- QScrollArea pour optimiser la mémoire
- Signals/Slots pour événements asynchrones
- Threading potentiel pour requêtes DB

## État actuel

✓ Interface complète
✓ Navigation fonctionnelle
✓ Lecteur intégré
✓ Design moderne
✓ Composants réutilisables

Prêt pour Phase 5: Intégration complète du backend et dynamique
