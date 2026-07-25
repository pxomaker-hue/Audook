# 🚀 Guide de Démarrage Audook

## 1️⃣ Prérequis (à installer d'abord)

### Node.js
Télécharger et installer depuis : https://nodejs.org/
- Vérifier l'installation : `node --version` et `npm --version`

### Python (déjà installé)
- Vérifier : `python --version` (doit être 3.8+)

## 2️⃣ Installation (une seule fois)

Ouvrir PowerShell et exécuter :

```powershell
# Aller dans le dossier du projet
cd "X:\Travail\Apprentissage\Codage\Audook"

# Installer les dépendances Python
pip install -r requirements.txt

# Installer les dépendances Node.js
npm install
```

**Important** : Attendez que npm install se termine (peut prendre 2-3 minutes).

## 3️⃣ Lancer l'Application

### Mode Développement (Recommandé pour tester)

```powershell
cd "X:\Travail\Apprentissage\Codage\Audook"
.\dev.bat
```

Cela lancera automatiquement :
1. ✓ Le serveur Python (http://127.0.0.1:5000)
2. ✓ Le serveur React (http://localhost:3000)
3. ✓ L'application Electron

**Attendez 10-15 secondes** pour que tout démarre.

### Mode Production (Créer l'exécutable)

```powershell
cd "X:\Travail\Apprentissage\Codage\Audook"
python build_electron.py
```

Cela créera deux fichiers dans `dist/` :
- `Audook.exe` (version portable, ~100MB)
- `Audook Setup.exe` (installateur)

## 🧪 Tests Rapides

### Vérifier que ça fonctionne
1. Ouvrir http://localhost:3000 dans le navigateur
2. Vérifier que la page React charge
3. Cliquer sur "Bibliothèque" → Les livres doivent s'afficher
4. Cliquer sur un livre → La page de détail doit s'ouvrir
5. Cliquer sur le bouton "Lire" → Le lecteur doit répondre

### Si ça ne fonctionne pas
- **Port 3000 occupé** : Fermer les autres apps Chrome/Electron
- **Port 5000 occupé** : Tuer le processus Python : `netstat -ano | findstr :5000`
- **npm not found** : Node.js n'est pas installé ou pas dans le PATH
- **Pas de livres** : Vérifier que `~/.audook/audook.db` existe

## 📁 Fichiers Importants

- `dev.bat` - Lancer en développement
- `build_electron.py` - Compiler pour production
- `audook_backend.py` - Serveur Flask Python
- `src/` - Code React
- `electron/` - Configuration Electron
- `app/` - Services backend

## 🎯 Prochaines Étapes

1. **Développement** : `dev.bat` → Tester les pages et fonctionnalités
2. **Correction de bugs** : Éditer `src/` et recharger (hot reload)
3. **Production** : `python build_electron.py` → Créer l'exécutable
4. **Distribution** : Partager `dist/Audook Setup.exe`

## ❓ Besoin d'Aide ?

- Lire `QUICKSTART.md` pour plus de détails
- Vérifier les logs dans la console Python et navigateur (F12)
- Consulter `ELECTRON_README.md` pour la documentation complète

**Bon développement ! 🎧**
