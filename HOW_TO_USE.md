# 🎧 Audook - Guide d'Utilisation Complet

## ✅ Status: ENTIÈREMENT FONCTIONNEL

Audook est maintenant une **application audiobook complète et fonctionnelle** pour Windows.

## 🚀 Démarrage Rapide

### 1. Préparation (première fois)

```bash
# Créer les fichiers de test
python create_test_audiobooks.py

# Installer les dépendances si ce n'est pas fait
pip install -r requirements.txt
```

### 2. Lancer l'application

```bash
python main.py
```

L'application devrait démarrer avec une interface moderne.

### 3. Charger une bibliothèque

**Option A: Dossier Local** (Recommandé pour débuter)
1. Dans le menu déroulant "Serveur", sélectionner **"Local"**
2. Un explorateur de fichiers s'ouvre
3. Naviger vers `test_audiobooks/` (ou votre dossier avec des audiobooks)
4. Cliquer "Sélectionner"
5. **Les audiobooks s'affichent automatiquement!** 🎉

**Option B: Serveur Audiobookshelf** (Avancé)
1. Dans Paramètres, ajouter un serveur Audiobookshelf
2. Entrer l'URL et la clé API
3. Sélectionner le serveur dans le menu

## 🎵 Utiliser l'Application

### Naviguer dans la Bibliothèque

```
┌─────────────────────────────────┐
│ Serveur ▼  Bibliothèque ▼ [↻]   │
├─────────────────────────────────┤
│  🔍 Rechercher...                │
├─────────────────────────────────┤
│  📚 Grille d'audiobooks avec     │
│     couvertures, titre, auteur   │
│                                 │
│  • Double-cliquer pour écouter  │
│  • Rechercher par titre/auteur  │
│  • Actualiser la bibliothèque   │
└─────────────────────────────────┘
```

### Lecteur Audio

```
🎵 Maintenant en écoute
├─ Couverture du livre
├─ Titre | Auteur | Chapitre
├─ Barre de progression: 00:45 / 01:00
│
Contrôles:
├─ 🔊 Volume (slider)
├─ ⏪ Recule 10s
├─ ⏮ Chapitre Précédent
├─ ▶️  Play / Pause
├─ ⏭ Chapitre Suivant
└─ ⏩ Avance 10s
```

## 📚 Fonctionnalités

### ✅ Bibliothèque Locale
- Charger un dossier avec audiobooks
- Affichage en grille avec couvertures
- Support formats: MP3, M4B, FLAC, OGG, WAV, AAC, OPUS
- Recherche par titre/auteur

### ✅ Lecture Audio
- Play, Pause, Stop
- Reprise à la dernière position
- Navigation chapitre précédent/suivant
- Seek: recule/avance de 10s ou 30s
- Contrôle du volume
- Vitesse de lecture (structure en place)

### ✅ Interface Moderne
- Grille d'audiobooks avec couvertures générées
- Lecteur élégant et intuitif
- Barre de statut pour feedback
- Responsive et coloré

### 🔄 À Venir
- [ ] Synchronisation avec Audiobookshelf
- [ ] Support Plex complet
- [ ] Signets/Marque-pages
- [ ] Interface refactorisée (selon tes designs)

## 🛠️ Commandes Utiles

```bash
# Générer les fichiers de test
python create_test_audiobooks.py

# Tester le scanner local
python test_local_scanner.py

# Test complet du workflow
python test_full_workflow.py

# Lancer l'application
python main.py

# Compiler l'exécutable Windows
python build_spec.py
```

## 📂 Structure des Audiobooks Locaux

L'application s'attend à une structure simple:

```
Mon_Dossier_Audiobooks/
├── Les Misérables/
│   ├── Book 1 - Fantine.wav
│   ├── Book 2 - Cosette.wav
│   └── Book 3 - Marius.wav
├── The Great Gatsby/
│   ├── Chapter 1.mp3
│   └── Chapter 2.mp3
└── Pride and Prejudice/
    ├── Volume 1.flac
    ├── Volume 2.flac
    └── Volume 3.flac
```

**Important:**
- 1 dossier = 1 audiobook
- 1 fichier audio = 1 chapitre
- Tous les formats audio supportés

## 🎨 Interface

### LibraryView (Gauche)
- Grille d'audiobooks
- Sélecteur de serveur
- Sélecteur de bibliothèque
- Barre de recherche

### PlayerView (Droit)
- Couverture du livre en écoute
- Informations: titre, auteur, chapitre
- Barre de progression
- Tous les contrôles de playback

## 🔧 Dépannage

### Pas de son
```bash
# Vérifier que les fichiers WAV existent
ls test_audiobooks/*/

# Vérifier les logs
grep "ERROR" app/logs/audook.log
```

### Application ne démarre pas
```bash
# Réinstaller les dépendances
pip install -r requirements.txt

# Vérifier la version Python (3.10+)
python --version
```

### Audiobooks ne s'affichent pas
1. Vérifier que le dossier est accessible
2. Vérifier qu'il contient des sous-dossiers avec fichiers audio
3. Cliquer "Actualiser" dans l'interface

## 📊 Commits Fonctionnalité Récents

```
588ee63 ✅ Test complet du workflow
66a0f6f ✅ Connexion complète UI ↔ Backend
7fc9101 ✅ Refonte UI (grille + lecteur)
4cc5a82 ✅ Génération de couvertures
```

## 🎯 Prochaines Étapes

1. **Court terme:**
   - [ ] Refonte UI selon tes designs
   - [ ] Sync avec Audiobookshelf
   - [ ] Support signets/marque-pages

2. **Moyen terme:**
   - [ ] Support Plex complet
   - [ ] Vitesse de lecture variable
   - [ ] Thème clair optionnel

3. **Long terme:**
   - [ ] Cache local
   - [ ] Synchronisation multi-appareils
   - [ ] Application mobile

## 💡 Tips

- **Créer des fichiers de test:** `python create_test_audiobooks.py`
- **Utiliser des vrais MP3/M4B:** Remplacer les fichiers WAV par les vôtres
- **Exporter en exe:** `python build_spec.py`

## 📞 Support

Pour toute question:
1. Vérifier les logs: `app/logs/audook.log`
2. Lancer le test: `python test_full_workflow.py`
3. Consulter QUICKSTART.md ou UI_REDESIGN.md

---

**Audook est prêt à utiliser! Bon écoute! 🎧📚**
