# Audook Electron - Installation et Utilisation

## Structure du projet

- `electron/` - Processus principal Electron et config
- `src/` - Application React + TypeScript
- `audook_backend.py` - Serveur Flask pour l'API backend
- `app/` - Logique métier Python (inchangée)

## Installation

### 1. Installer les dépendances Node.js

```bash
npm install
```

### 2. Installer les dépendances Python (si nécessaire)

```bash
pip install flask flask-cors python-vlc sqlalchemy requests
```

## Développement

### Lancer l'application en mode développement

```bash
npm start
```

Cela lancera :
1. Le serveur React sur http://localhost:3000
2. Le serveur Python backend sur http://127.0.0.1:5000
3. L'application Electron

### Notes de développement

- React DevTools sera automatiquement ouvert
- Les modifications du code React se rechargeront automatiquement
- Pour modifier le backend Python, redémarrez l'app

## Production

### Compiler l'application

```bash
npm run build
```

Cela créera :
1. Un bundle React optimisé dans `build/`
2. Un exécutable Windows installable dans `dist/`

### Fichiers générés

- `dist/Audook.exe` - Exécutable portable
- `dist/Audook Setup.exe` - Installateur

## Configuration IPC

L'architecture utilise deux canaux de communication :

### Mode développement
- React communique avec le backend via HTTP sur `http://localhost:5000/api`
- C'est la configuration par défaut dans les composants

### Mode production
- Même architecture HTTP (plus simple et robuste que IPC pour cette app)
- Le backend Python est inclus dans le bundle PyInstaller

## Fichiers importants

- `electron/main.js` - Point d'entrée Electron
- `electron/preload.js` - Bridge IPC (optionnel, HTTP utilisé par défaut)
- `src/App.tsx` - Composant principal React
- `audook_backend.py` - Serveur Flask exposant l'API
- `package.json` - Configuration npm et Electron Builder

## Troubleshooting

### Le backend Python ne démarre pas
- Vérifiez que Python est dans le PATH
- Vérifiez que les dépendances Python sont installées
- Vérifiez la console pour les erreurs

### React ne charge pas
- Vérifiez que npm start a finalisé
- Vérifiez que le port 3000 est libre
- Consultez la console d'Electron (Dev Tools)

### L'API ne répond pas
- Vérifiez que le backend Python est en cours d'exécution
- Vérifiez que le port 5000 est libre
- Vérifiez les logs Flask dans la console

## Traduction

Toute l'interface utilisateur est en français. Les clés de traduction sont directement dans les composants React.

## Prochaines étapes

1. ✅ Structure de base Electron + React + TypeScript
2. ✅ Composants UI (Sidebar, Player, Pages)
3. ✅ Intégration HTTP API backend
4. ⬜ Tester en mode développement
5. ⬜ Compiler PyInstaller pour le backend
6. ⬜ Compiler Electron Builder pour l'application
7. ⬜ Tester l'exécutable final
