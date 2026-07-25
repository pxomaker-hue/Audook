# Contribuer à Audook

Merci de votre intérêt à contribuer à Audook ! Nous accueillons les contributions de tous.

## Comment contribuer

### Signaler des problèmes

1. **Vérifiez les problèmes existants** : Avant de créer un nouveau problème, vérifiez si un problème similaire existe déjà.
2. **Fournissez des détails** : Incluez autant d'informations que possible :
 - Votre système d'exploitation (version de Windows)
 - Version de Python
 - Étapes pour reproduire le problème
 - Comportement attendu
 - Comportement réel
 - Captures d'écran (si applicable)
 - Messages d'erreur ou logs

### Suggérer des fonctionnalités

1. **Vérifiez la feuille de route** : Consultez les demandes de fonctionnalités existantes et la feuille de route du projet.
2. **Créez une issue** : Décrivez la fonctionnalité que vous aimeriez voir, y compris :
 - Le problème qu'elle résout
 - Comment elle fonctionnerait
 - Toutes les alternatives potentielles

### Contributions de code

#### Configuration de l'environnement de développement

1. **Forkez le dépôt** : Créez un fork du dépôt Audook.
2. **Clonez votre fork** :
 ```bash
 git clone https://github.com/votre-nom-utilisateur/Audook.git
 cd Audook
 ```
3. **Créez une branche** :
 ```bash
 git checkout -b fonctionnalite/votre-fonctionnalité
 ```
4. **Configurez un environnement virtuel** :
 ```bash
 python -m venv venv
 source venv/bin/activate # Sur Windows : venv\Scripts\activate
 ```
5. **Installez les dépendances** :
 ```bash
 pip install -r requirements.txt
 ```
6. **Installez les dépendances de développement** :
 ```bash
 pip install pytest pyinstaller
 ```

#### Effectuer des modifications

1. **Respectez le style de codage** :
 - Utilisez le guide de style PEP 8
 - Utilisez les annotations de type pour toutes les fonctions et méthodes
 - Écrivez des docstrings pour toutes les méthodes publiques
 - Gardez les lignes sous 100 caractères
 - Utilisez des noms de variables et de fonctions descriptifs

2. **Écrivez des tests** :
 - Ajoutez des tests pour les nouvelles fonctionnalités
 - Exécutez les tests existants pour vous assurer que rien ne casse
 - Les tests se trouvent dans `test_app.py`

3. **Mettez à jour la documentation** :
 - Mettez à jour `README.md` si vous ajoutez de nouvelles fonctionnalités
 - Mettez à jour `API.md` si vous ajoutez de nouvelles méthodes API
 - Ajoutez des commentaires pour le code complexe

4. **Gardez les commits atomiques** :
 - Chaque commit doit représenter un changement logique unique
 - Écrivez des messages de commit clairs et descriptifs
 - Utilisez le présent ("Ajouter une fonctionnalité" et non "Ajouté une fonctionnalité")

#### Soumettre des modifications

1. **Exécutez les tests** :
 ```bash
 python test_app.py
 ```

2. **Exécutez l'application** :
 ```bash
 python main.py
 ```

3. **Validez vos modifications** :
 ```bash
 git add .
 git commit -m "Ajouter la description de votre fonctionnalité"
 ```

4. **Poussez vers votre fork** :
 ```bash
 git push origin fonctionnalite/votre-fonctionnalité
 ```

5. **Créez une Pull Request** :
 - Allez sur le dépôt Audook sur GitHub
 - Cliquez sur "New Pull Request"
 - Sélectionnez votre branche
 - Fournissez une description claire de vos modifications
 - Liez à toutes les issues connexes

## Processus de révision de code

1. **Révision initiale** : Un mainteneur examinera votre PR dans quelques jours.
2. **Retour** : Vous pourriez recevoir des retours ou des demandes de modifications.
3. **Révisions** : Effectuez les modifications demandées et poussez-les vers votre branche.
4. **Approbation** : Une fois approuvée, votre PR sera fusionnée.

## Directives de codage

### Code Python

- **Imports** : Regroupez les imports par type (bibliothèque standard, tierce partie, locale) avec une ligne vide entre les groupes
- **Nommage** : Utilisez `snake_case` pour les variables et fonctions, `CamelCase` pour les classes
- **Constantes** : Utilisez `MAJUSCULES` pour les constantes
- **Membres privés** : Préférez avec `_` pour un usage interne
- **Annotations de type** : Utilisez les annotations de type Python pour tous les paramètres et valeurs de retour des fonctions

### Code Qt

- **Signaux et Slots** : Utilisez la syntaxe nouvelle `pyqtSignal` et `connect`
- **Dispositions** : Préférez utiliser des dispositions plutôt que le positionnement absolu
- **Styles** : Utilisez des feuilles de style pour un style cohérent
- **Threading** : Ne mettez jamais à jour l'UI depuis un thread non-UI

### Code asynchrone

- **Fonctions asynchrones** : Marquez avec `async def` et utilisez `await` pour les appels asynchrones
- **Threading** : Utilisez `asyncio` pour les opérations liées à l'E/S
- **Opérations bloquantes** : Utilisez des threads pour les opérations liées au CPU

### Gestion des erreurs

- **Exceptions** : Attrapez des exceptions spécifiques lorsque c'est possible
- **Journalisation** : Utilisez le `logger` de `app.utils` pour la journalisation
- **Retour utilisateur** : Affichez des messages d'erreur conviviaux

## Tests

### Exécution des tests

```bash
python test_app.py
```

### Écriture des tests

- Ajoutez des tests à `test_app.py`
- Testez à la fois les cas de succès et d'échec
- Utilisez des instructions `assert` pour la vérification
- Regroupez les tests connexes

### Couverture des tests

Visez une bonne couverture des tests, en particulier pour :
- Les fonctionnalités principales
- La gestion des erreurs
- Les cas limites

## Documentation

### Documentation du code

- **Docstrings** : Utilisez des docstrings de style Google pour toutes les méthodes publiques
- **Commentaires** : Ajoutez des commentaires pour le code complexe ou non évident
- **Annotations de type** : Utilisez les annotations de type pour documenter les types attendus

### Documentation utilisateur

- **README.md** : Documentation principale de l'utilisateur
- **API.md** : Documentation API pour les développeurs
- **CONTRIBUTING.md** : Ce fichier

## Traduction

Audook prend actuellement en charge uniquement l'anglais. Si vous souhaitez ajouter des traductions :

1. Créez un nouveau répertoire `app/translations/`
2. Ajoutez des fichiers de traduction (fichiers `.qm` pour Qt)
3. Mettez à jour le code de chargement de la langue dans la fenêtre principale

## Construction de l'application

### Build de développement

```bash
python main.py
```

### Build de production

```bash
python build_spec.py
```

Ou utilisez le fichier batch :
```bash
build.bat
```

### Création d'un installateur

1. Installez [Inno Setup](https://jrsoftware.org/isinfo.php)
2. Exécutez :
 ```bash
 build.bat
 ```

## Licence

En contribuant à Audook, vous acceptez que vos contributions seront sous licence MIT.

## Code de conduite

Soyez respectueux et inclusif. Suivez le [Code de conduite Python](https://www.python.org/community/conduct/).

## Obtenir de l'aide

Si vous avez besoin d'aide pour contribuer :
- Ouvrez une issue avec votre question
- Rejoignez la discussion (si disponible)
- Consultez le code existant pour des exemples

## Reconnaissance

Tous les contributeurs seront reconnus dans le fichier `CONTRIBUTORS.md` (à créer).

---

Merci de contribuer à Audook ! Votre aide rend ce projet meilleur pour tous.
