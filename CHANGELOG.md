# Changelog

## 1.0.5
- Corrige le démarrage de l'application Windows : en 1.0.4, le serveur intégré ne se lançait pas (« Serveur non disponible »), car le module `cryptography` n'était pas embarqué dans l'exécutable.
- Le script de build vérifie maintenant les modules Python nécessaires et teste le démarrage du backend compilé (`/health`) avant de produire l'installeur.

## 1.0.4
- Numéro de version affiché dans Réglages (source unique : `package.json`).
- Mises à jour automatiques (Windows et Android) : vérification au démarrage et bouton « Rechercher une mise à jour » dans Réglages. Le manifeste du dépôt est signé (Ed25519) et chaque fichier téléchargé est vérifié par SHA-256 avant installation ; l'installation demande toujours une confirmation.
- Le NAS (Docker) signale qu'une mise à jour existe mais se met à jour à la main.

## 1.0.3
- Version initiale suivie.
