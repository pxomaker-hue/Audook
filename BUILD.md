# Guide de Build pour Audook

Ce guide explique comment construire Audook et créer un installateur Windows.

## Méthodes de Build

### Méthode 1 : Utiliser le script tout-en-un (Recommandé) ⭐

Le moyen le plus simple de tout construire :

```bash
python build_installer.py
```

Ce script va :
1. ✅ Générer l'icône (si elle n'existe pas)
2. ✅ Construire l'exécutable avec PyInstaller
3. ✅ Créer l'installateur avec Inno Setup (si installé)

**Options :**
- `--no-icon` : Ne pas générer l'icône
- `--no-installer` : Ne pas créer l'installateur
- `--test` : Tester sans créer de fichiers finaux

---

### Méthode 2 : Build manuel

#### Étape 1 : Installer les dépendances

```bash
pip install -r requirements.txt
pip install pyinstaller pillow
```

#### Étape 2 : Générer l'icône (optionnel)

```bash
python assets/icons/generate_icon.py
```

Ou utilisez l'icône existante : `assets/icons/audook.ico`

#### Étape 3 : Construire l'exécutable

```bash
python build_spec.py
```

L'exécutable sera créé dans : `dist/Audook.exe`

#### Étape 4 : Créer l'installateur (optionnel)

1. **Installez Inno Setup** :
   - Téléchargez depuis : [https://jrsoftware.org/isinfo.php](https://jrsoftware.org/isinfo.php)
   - Installez-le (par défaut dans `C:\Program Files (x86)\Inno Setup 6\`)

2. **Exécutez Inno Setup** :
   ```bash
   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" /Qp installer.iss
   ```

3. **L'installateur sera créé** dans : `dist/Audook_Setup.exe`

---

### Méthode 3 : Utiliser le script batch

Double-cliquez simplement sur :
```
build.bat
```

Ce script va :
1. Vérifier que Python est installé
2. Installer les dépendances manquantes
3. Générer l'icône
4. Construire l'exécutable
5. Créer l'installateur (si Inno Setup est installé)

---

## Prérequis

### Pour l'exécutable (.exe)
- ✅ Python 3.10+
- ✅ pip
- ✅ PyInstaller (`pip install pyinstaller`)
- ✅ Pillow (`pip install pillow`) - pour générer l'icône

### Pour l'installateur (.exe)
- ✅ Inno Setup 6 (optionnel)
  - Téléchargement : [https://jrsoftware.org/isinfo.php](https://jrsoftware.org/isinfo.php)

---

## Structure des fichiers de build

```
Audook/
├── main.py                          # Point d'entrée
├── build_spec.py                    # Spécification PyInstaller
├── build.bat                        # Script batch Windows
├── build_installer.py              # Script Python tout-en-un
├── installer.iss                   # Script Inno Setup
└── assets/
    └── icons/
        ├── audook.ico              # Icône de l'application
        └── generate_icon.py        # Script pour générer l'icône
```

---

## Dépannage

### Problème : "Python is not installed"
**Solution :** Installez Python 3.10+ depuis [python.org](https://www.python.org/downloads/)

### Problème : "PyInstaller is not installed"
**Solution :** Exécutez `pip install pyinstaller`

### Problème : "PIL is not installed"
**Solution :** Exécutez `pip install pillow`

### Problème : "Inno Setup not found"
**Solution :** Installez Inno Setup depuis [jrsoftware.org](https://jrsoftware.org/isinfo.php)

### Problème : L'exécutable ne se lance pas
**Solution :**
1. Vérifiez que `dist/Audook.exe` existe
2. Essayez de l'exécuter depuis la ligne de commande : `dist/Audook.exe`
3. Vérifiez les logs dans le terminal

### Problème : L'icône ne s'affiche pas
**Solution :**
1. Vérifiez que `assets/icons/audook.ico` existe
2. Vérifiez que le chemin dans `build_spec.py` est correct : `--icon=assets/icons/audook.ico`

---

## Personnalisation

### Changer l'icône
1. Remplacez `assets/icons/audook.ico` par votre propre icône
2. Assurez-vous qu'elle est au format `.ico` avec plusieurs tailles (16x16, 32x32, 48x48, etc.)

### Changer le nom de l'application
Modifiez dans `build_spec.py` :
```python
'--name=Audook'  # Changez par votre nom
```

### Changer la version
Modifiez dans :
- `build_spec.py` : `--name=Audook`
- `installer.iss` : `AppVersion=1.0.0`
- `setup.py` : `version='1.0.0'`

---

## Fichiers générés

Après un build réussi, vous aurez :

```
dist/
├── Audook.exe          # Exécutable principal (≈ 50-100 Mo)
├── Audook_Setup.exe    # Installateur (si Inno Setup est installé)
└── _internal/          # Fichiers internes (si --onefile n'est pas utilisé)
```

---

## Distribution

### Pour partager l'exécutable
1. Compressez le dossier `dist/` en `.zip`
2. Partagez le fichier `.zip`
3. L'utilisateur n'a qu'à extraire et exécuter `Audook.exe`

### Pour partager l'installateur
1. Partagez simplement `dist/Audook_Setup.exe`
2. L'utilisateur n'a qu'à l'exécuter et suivre les instructions

---

## Notes

- **Taille de l'exécutable** : L'exécutable sera assez grand (50-100 Mo) car il inclut toutes les dépendances (PyQt6, pygame, etc.)
- **Temps de build** : Le premier build peut prendre plusieurs minutes
- **Antivirus** : Certains antivirus peuvent bloquer PyInstaller. Ajoutez une exception si nécessaire.
- **Windows Defender** : Peut ralentir le build. Désactivez-le temporairement si le build est trop lent.

---

## Aide supplémentaire

- **Documentation PyInstaller** : [https://pyinstaller.org/](https://pyinstaller.org/)
- **Documentation Inno Setup** : [https://jrsoftware.org/ishelp/](https://jrsoftware.org/ishelp/)
- **Problèmes ?** : Ouvrez une issue sur [GitHub](https://github.com/pxomaker-hue/Audook/issues)

---

**Bonne construction !** 🚀
