# 🔨 Instructions de Compilation Audook

**Date de mise à jour**: 2026-07-25  
**État**: Prêt pour build

---

## ✅ Prérequis

- [x] Node.js 16+ installé
- [x] Python 3.8+ installé  
- [x] Port 3000 libre (dev) / 5000 libre (backend)
- [x] VLC installé sur le système (pour python-vlc)

---

## 📦 Étape 1 : Installation des Dépendances

### 1.1 Dépendances Python

```powershell
cd "X:\Travail\Apprentissage\Codage\Audook"
pip install -r requirements.txt --upgrade
```

**Attendez** que toutes les dépendances s'installent (Flask, SQLAlchemy, python-vlc, etc.)

### 1.2 Dépendances Node.js

```powershell
# Nettoyer les anciennes installations
rm node_modules -Recurse -Force -ErrorAction SilentlyContinue
rm package-lock.json -ErrorAction SilentlyContinue

# Installer les nouvelles dépendances
npm install
```

**Attendez** que npm finisse (2-3 minutes)

---

## 🚀 Étape 2 : Mode Développement (Test)

```powershell
cd "X:\Travail\Apprentissage\Codage\Audook"
.\dev.bat
```

Cela lancera :
1. ✓ Backend Python sur http://127.0.0.1:5000
2. ✓ React dev server sur http://localhost:3000
3. ✓ Electron application

**Attendre 10-15 secondes** pour que tout démarre.

### Test de la Démo

1. Ouvrir l'application Electron
2. Cliquer sur **Bibliothèque** → Les livres doivent s'afficher
3. Cliquer sur un livre → La page de détail doit s'ouvrir
4. Cliquer sur le bouton **Lire** → Le lecteur doit répondre
5. Tester les contrôles (volume, vitesse, barre de progression)

**Si ça fonctionne :** ✅ Prêt pour le build !

---

## 📦 Étape 3 : Build Production

```powershell
cd "X:\Travail\Apprentissage\Codage\Audook"
python build_electron.py
```

Le script fera:
1. ✓ Compile le backend Python → `dist/audook_backend/audook_backend.exe`
2. ✓ Compile React → `build/` folder
3. ✓ Compile Electron → `dist/Audook.exe` + `dist/Audook Setup.exe`

**Durée:** 5-10 minutes

### Résultat

Les fichiers se trouvent dans `dist/`:
- `Audook.exe` (150-200MB) - Version portable, double-clic pour lancer
- `Audook Setup.exe` (100MB) - Installateur Windows classique

---

## 🧪 Étape 4 : Test de l'Exécutable

```powershell
# Lancer la version portable
cd "X:\Travail\Apprentissage\Codage\Audook\dist"
.\Audook.exe
```

L'application doit :
1. Se lancer sans console Python visible
2. Montrer l'interface React dans Electron
3. Charger les livres depuis la base de données
4. Répondre aux clics sans erreurs

**Si tout fonctionne :** ✅ L'application est prête à être distribuée !

---

## 🆘 Troubleshooting

### `npm install` échoue avec erreur de version

**Symptôme**: "ERESOLVE could not resolve"

**Solution**:
```powershell
npm install --legacy-peer-deps
```

### Port 5000 déjà utilisé

**Symptôme**: "Address already in use"

**Solution**:
```powershell
# Trouver le processus
netstat -ano | findstr :5000

# Tuer le processus (remplacer PID par le numéro)
taskkill /PID [PID] /F
```

### Port 3000 déjà utilisé

**Symptôme**: "Port 3000 is in use"

**Solution**:
```powershell
# Utiliser un autre port
set PORT=3001
npm run react-start
```

### plexapi n'installe pas

**Symptôme**: "Could not find version python-plexapi==4.15.0"

**Solution**: ✅ **Déjà corrigé** dans `requirements.txt` (version 4.16.2)

### Les livres ne s'affichent pas

**Symptôme**: Page vide dans Electron

**Solutions**:
1. Vérifier que le backend Python est en cours d'exécution
2. Ouvrir http://localhost:5000/api/health dans le navigateur
3. Vérifier que `~/.audook/audook.db` existe
4. Consulter la console Python pour les erreurs

### Electron affiche "Serveur non disponible"

**Symptôme**: "Vérifiez que: Le serveur Python est en cours d'exécution"

**Solutions**:
1. Ouvrir PowerShell
2. Taper : `python audook_backend.py`
3. Attendre le message "Running on http://127.0.0.1:5000"
4. Recharger l'application Electron (Ctrl+R ou F5)

---

## 📋 Checklist Finale

Avant de distribuer l'application :

```
[ ] npm install s'exécute sans erreurs
[ ] pip install -r requirements.txt s'exécute sans erreurs
[ ] dev.bat lance l'app sans problèmes
[ ] La démo React fonctionne (livres chargent)
[ ] python build_electron.py se termine avec succès
[ ] Audook.exe se lance depuis dist/
[ ] L'app charge les livres
[ ] Les contrôles du lecteur fonctionnent
[ ] Aucune erreur Python dans la console
[ ] Aucune erreur JavaScript dans DevTools (F12)
```

✅ Si tout est coché : **L'application est prête pour la distribution !**

---

## 📚 Documentation

- `DEMARRAGE.md` - Guide simple en français
- `QUICKSTART.md` - Démarrage rapide  
- `ELECTRON_README.md` - Doc technique Electron
- `MIGRATION.md` - Contexte de la migration
- `AUDIT_PROJECT.md` - Audit complet du projet

---

## 🎯 Commandes Rapides

```powershell
# Dev mode
.\dev.bat

# Build complet
python build_electron.py

# Lancer exécutable
.\dist\Audook.exe

# Nettoyer les builds
rm dist -Recurse -Force
rm build -Recurse -Force
rm node_modules -Recurse -Force
rm .\build\audook_backend -Recurse -Force

# Réinstaller tout
npm install
pip install -r requirements.txt --upgrade
```

---

**Bon build ! 🚀**
