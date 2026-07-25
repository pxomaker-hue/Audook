# Migration de PyQt6 à Electron + React

## Résumé

L'interface utilisateur complète a été migrée de PyQt6 (instable) vers Electron + React + TypeScript (moderne et stable).

## Changements

### ✅ Préservé

- **Backend complet** : Base de données (SQLAlchemy), lecteur VLC, services
- **Architecture** : Repository pattern, services layer, gestion du progress
- **Fonctionnalités** : Lecture audio, synchronisation, gestion de plusieurs serveurs

### 🔄 Remplacé

- **Interface utilisateur** : PyQt6 → Electron + React + TypeScript
- **API** : IPC limité → API REST HTTP (plus simple et robuste)
- **Styles** : PyQt6 stylesheets → CSS moderne avec variables CSS
- **Navigation** : Signaux/slots PyQt6 → React Router

### 📦 Nouvelle structure

```
audook/
├── electron/              # Configuration Electron
│   ├── main.js           # Processus principal
│   └── preload.js        # Bridge IPC (optionnel)
├── src/                  # Application React
│   ├── components/       # Composants réutilisables
│   ├── pages/           # Pages principales
│   ├── App.tsx          # Composant racine
│   └── index.tsx        # Point d'entrée
├── audook_backend.py    # Serveur Flask
├── app/                 # Logique métier Python (inchangée)
├── package.json         # Dépendances Node.js
├── tsconfig.json        # Configuration TypeScript
└── build_electron.py    # Script de build pour production
```

## Architecture de communication

### Développement

```
React UI (port 3000) <-HTTP-> Flask Backend (port 5000)
                                    ↓
                            Services Python
                                    ↓
                        SQLAlchemy ORM + SQLite
```

### Production

```
Electron App
├── IPC → Python Backend (PyInstaller executable)
│           ↓
│       Flask API (port 5000)
│           ↓
│       Services Python
└── UI (React compiled)
```

## Migration détaillée des pages

### HomePage (Bibliothèque)
- **PyQt6** : QGridLayout avec BookCard widgets
- **React** : BookCard grid avec CSS Grid
- ✓ Recherche en temps réel
- ✓ Clic sur livre → Détail page

### ExplorePage (Découvrir)
- **PyQt6** : Même layout que HomePage
- **React** : Même grid que HomePage
- ✓ Affichage en vedette

### BookDetailPage (Nouveau)
- **PyQt6** : N'existait pas (raison de la migration)
- **React** : Page complète avec :
  - Couverture du livre
  - Informations (titre, auteur, narrateur)
  - Progression de lecture
  - Liste des chapitres
  - Bouton "Lire"

### Player (Lecteur)
- **PyQt6** : Widget intégré, signaux cassés
- **React** : Composant Player avec :
  - Barre de lecture
  - Contrôles (play, pause, volume, vitesse)
  - Affichage du temps
  - Mise à jour en temps réel

### HistoryPage (Historique)
- **PyQt6** : N'existait pas
- **React** : Skeleton page prête pour implémentation

### SettingsPage (Paramètres)
- **PyQt6** : N'existait pas
- **React** : Page avec paramètres de base

## Traduction

Tout est en français :
- Interface utilisateur
- Labels des boutons
- Messages d'erreur
- Placeholders des champs

## Installation et utilisation

### Développement
```bash
npm install
npm start
```

### Production
```bash
npm run build
```

## Avantages de cette migration

1. **Stabilité** : Electron est plus stable que PyQt6 pour ce cas
2. **Modernité** : React + TypeScript = meilleure maintenabilité
3. **Performance** : Rendu DOM optimisé
4. **Développement** : Hot reload, DevTools intégrés
5. **Distribution** : Electron Builder gère les installers
6. **Écosystème** : Beaucoup plus de ressources/tutorials
7. **Navigabilité** : Les pages s'ouvrent enfin correctement
8. **Responsive** : L'interface s'adapte à la fenêtre

## Prochaines étapes

1. Tester en mode développement
2. Compiler le backend Python
3. Compiler l'application Electron
4. Tester l'exécutable final
5. Implémenter les fonctionnalités manquantes si nécessaire
