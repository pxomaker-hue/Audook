# Audook Electron - Guide de démarrage rapide

## 🚀 Installation rapide

### Prérequis
- **Node.js** 16+ (télécharger depuis https://nodejs.org/)
- **Python** 3.8+ (déjà installé)
- **pip** (gestionnaire de paquets Python)

### 1. Installation des dépendances

**Dépendances Python** :
```bash
pip install -r requirements.txt
```

**Dépendances Node.js** :
```bash
npm install
```

### 2. Lancer en développement

#### Option 1 : Batch (Recommandé pour Windows)
```bash
dev.bat
```

#### Option 2 : PowerShell
```powershell
.\dev.ps1
```

#### Option 3 : Ligne de commande manuelle
```bash
# Terminal 1 : Backend Python
python audook_backend.py

# Terminal 2 : Frontend React
npm run react-start
```

L'application devrait s'ouvrir automatiquement après ~10 secondes.

## 🏗️ Compiler pour la production

```bash
python build_electron.py
```

Cela créera les fichiers dans `dist/`:
- `Audook.exe` - Version portable
- `Audook Setup.exe` - Installateur

## 📝 Checkliste de démarrage

- [ ] Node.js installé et dans le PATH
- [ ] Python 3.8+ installé et dans le PATH
- [ ] `pip install -r requirements.txt` exécuté
- [ ] `npm install` exécuté
- [ ] `dev.bat` lancé (ou commandes manuelles)
- [ ] L'app React se charge sur http://localhost:3000
- [ ] Le backend Python démarre sans erreur
- [ ] Cliquer sur un livre ouvre la page de détail

## 🆘 Troubleshooting

### "npm: command not found"
→ Node.js n'est pas installé ou pas dans le PATH
→ Téléchargez depuis https://nodejs.org/

### "python: command not found"
→ Python n'est pas dans le PATH
→ Sur Windows : Lancez l'installeur Python et cochez "Add Python to PATH"

### "Port 3000 already in use"
→ Une autre app utilise le port 3000
→ Changez le port : `PORT=3001 npm run react-start`

### "Port 5000 already in use"
→ Une autre app utilise le port 5000
→ Arrêtez l'autre application ou changez le port dans `audook_backend.py`

### L'interface React ne charge pas
→ Vérifiez que `npm run react-start` s'exécute
→ Ouvrez http://localhost:3000 dans un navigateur
→ Consultez la console pour les erreurs

### Le backend ne répond pas
→ Vérifiez que `python audook_backend.py` s'exécute
→ Testez avec : `curl http://127.0.0.1:5000/api/health`
→ Vérifiez la console Python pour les erreurs

## 📖 Documentation

- `ELECTRON_README.md` - Documentation Electron complète
- `MIGRATION.md` - Détails sur la migration PyQt6 → Electron
