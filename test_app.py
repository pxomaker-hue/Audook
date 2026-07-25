#!/usr/bin/env python3
"""
Script de test pour Audook
Exécutez ceci pour vérifier que l'application fonctionne correctement
"""

import sys
import asyncio
from pathlib import Path

# Ajouter le chemin du projet
sys.path.insert(0, str(Path(__file__).parent))


def test_imports():
    """Test que toutes les imports fonctionnent"""
    print("Test des imports...")

    try:
        from app import __version__, APP_NAME, DATA_DIR, CONFIG_FILE
        print(f"✓ Module App : v{__version__}")

        from app.models import Audiobook, Chapter, Library, Bookmark, PlaybackState, ServerConfig, AppConfig
        print("✓ Modèles")

        from app.utils import format_duration, format_time_short, generate_id, sanitize_filename
        print("✓ Utilitaires")

        from app.utils.config_manager import config_manager
        print("✓ Gestionnaire de configuration")

        from app.audiobookshelf.client import AudiobookshelfClient
        print("✓ Client Audiobookshelf")

        from app.plex.client import PlexClient
        print("✓ Client Plex")

        from app.player.player import player
        from app.player.queue import queue
        print("✓ Lecteur")

        from app.ui import get_stylesheet, apply_theme
        print("✓ Utilitaires UI")

        from app.ui.library_view import LibraryView
        from app.ui.player_view import PlayerView
        from app.ui.settings_view import SettingsView
        print("✓ Composants UI")

        from app.main_window import MainWindow
        print("✓ Fenêtre principale")

        print("\n✅ Tous les imports ont réussi !\n")
        return True

    except Exception as e:
        print(f"\n❌ Import échoué : {e}")
        import traceback
        traceback.print_exc()
        return False


def test_models():
    """Test des modèles de données"""
    print("Test des modèles...")

    try:
        from app.models import Audiobook, Chapter, Library, Bookmark, PlaybackState, ServerConfig
        from datetime import datetime

        # Test Audiobook
        audiobook = Audiobook(
            id="test123",
            library_id="lib123",
            title="Livre audio test",
            author="Auteur test",
            narrator="Narrateur test",
            description="Description test",
            duration=3600.0,
            source="audiobookshelf"
        )
        assert audiobook.display_title == "Livre audio test - Auteur test"
        print("✓ Modèle Audiobook")

        # Test Chapter
        chapter = Chapter(
            id="chap1",
            title="Chapitre 1",
            index=0,
            duration=1800.0,
            audio_file="/chemin/vers/audio.mp3"
        )
        assert chapter.display_title == "1. Chapitre 1"
        print("✓ Modèle Chapter")

        # Test Library
        library = Library(
            id="lib123",
            name="Bibliothèque test",
            source="audiobookshelf",
            server_url="http://localhost:13378"
        )
        print("✓ Modèle Library")

        # Test Bookmark
        bookmark = Bookmark(
            book_id="test123",
            library_id="lib123",
            chapter_id="chap1",
            position=600.0,
            title="Mon marque-page"
        )
        print("✓ Modèle Bookmark")

        # Test PlaybackState
        state = PlaybackState(
            book_id="test123",
            library_id="lib123",
            chapter_id="chap1",
            position=600.0,
            is_playing=True,
            speed=1.0
        )
        print("✓ Modèle PlaybackState")

        # Test ServerConfig
        server = ServerConfig(
            id="server1",
            name="Mon serveur",
            type="audiobookshelf",
            url="http://localhost:13378",
            api_key="clé-test"
        )
        print("✓ Modèle ServerConfig")

        print("\n✅ Tous les tests de modèles ont réussi !\n")
        return True

    except Exception as e:
        print(f"\n❌ Test de modèle échoué : {e}")
        import traceback
        traceback.print_exc()
        return False


def test_utils():
    """Test des fonctions utilitaires"""
    print("Test des utilitaires...")

    try:
        from app.utils import format_duration, format_time_short, generate_id, sanitize_filename

        # Test format_duration
        assert format_duration(0) == "00:00"
        assert format_duration(60) == "01:00"
        assert format_duration(3661) == "01:01:01"
        print("✓ format_duration")

        # Test format_time_short
        assert format_time_short(60) == "1m 0s"
        assert format_time_short(3661) == "1h 1m"
        print("✓ format_time_short")

        # Test generate_id
        id1 = generate_id("test_")
        id2 = generate_id("test_")
        assert id1 != id2
        assert id1.startswith("test_")
        print("✓ generate_id")

        # Test sanitize_filename
        assert sanitize_filename("Test: Fichier*Nom?.txt") == "Test_Fichier_Nom.txt"
        print("✓ sanitize_filename")

        print("\n✅ Tous les tests utilitaires ont réussi !\n")
        return True

    except Exception as e:
        print(f"\n❌ Test utilitaire échoué : {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config():
    """Test de la configuration"""
    print("Test de la configuration...")

    try:
        from app.utils.config_manager import config_manager
        from app.models import ServerConfig

        # Test du chargement de la configuration
        config = config_manager.config
        assert hasattr(config, 'servers')
        assert hasattr(config, 'theme')
        print("✓ Chargement de la configuration")

        # Test de la gestion des serveurs
        test_server = ServerConfig(
            id="test_server",
            name="Serveur test",
            type="audiobookshelf",
            url="http://localhost:13378",
            api_key="clé-test"
        )

        # Ajouter un serveur
        config_manager.add_server(test_server)
        assert len(config_manager.config.servers) > 0
        print("✓ Ajout d'un serveur")

        # Supprimer un serveur
        config_manager.remove_server("test_server")
        print("✓ Suppression d'un serveur")

        print("\n✅ Tous les tests de configuration ont réussi !\n")
        return True

    except Exception as e:
        print(f"\n❌ Test de configuration échoué : {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_clients():
    """Test des clients API (sans connexions réelles)"""
    print("Test des clients API...")

    try:
        from app.audiobookshelf.client import AudiobookshelfClient
        from app.plex.client import PlexClient

        # Test de l'instanciation d'AudiobookshelfClient
        abs_client = AudiobookshelfClient("http://localhost:13378", "clé-test")
        assert abs_client.base_url == "http://localhost:13378"
        assert abs_client.api_key == "clé-test"
        abs_client.close()
        print("✓ Client Audiobookshelf")

        # Test de l'instanciation de PlexClient
        plex_client = PlexClient("http://localhost:32400", "jeton-test")
        assert plex_client.base_url == "http://localhost:32400"
        assert plex_client.token == "jeton-test"
        plex_client.close()
        print("✓ Client Plex")

        print("\n✅ Tous les tests de clients ont réussi !\n")
        return True

    except Exception as e:
        print(f"\n❌ Test de client échoué : {e}")
        import traceback
        traceback.print_exc()
        return False


def test_player():
    """Test du lecteur (sans audio réel)"""
    print("Test du lecteur...")

    try:
        from app.player.player import player
        from app.player.queue import queue

        # Test de l'état du lecteur
        assert player.get_volume() == 0.8  # Par défaut
        assert player.get_speed() == 1.0  # Par défaut
        assert not player.is_playing()
        print("✓ État du lecteur")

        # Test de la file d'attente
        assert queue.is_empty()
        print("✓ File d'attente")

        print("\n✅ Tous les tests du lecteur ont réussi !\n")
        return True

    except Exception as e:
        print(f"\n❌ Test du lecteur échoué : {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Exécuter tous les tests"""
    print("=" * 60)
    print("Audook - Suite de tests")
    print("=" * 60)
    print()

    results = []

    # Exécuter les tests synchrones
    results.append(("Imports", test_imports()))
    results.append(("Modèles", test_models()))
    results.append(("Utilitaires", test_utils()))
    results.append(("Configuration", test_config()))
    results.append(("Lecteur", test_player()))

    # Exécuter les tests asynchrones
    results.append(("Clients", asyncio.run(test_clients())))

    # Résumé
    print("=" * 60)
    print("Résumé des tests")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ RÉUSSI" if result else "❌ ÉCHOUÉ"
        print(f"{name:20s} {status}")

    print()
    print(f"Résultats : {passed}/{total} tests réussis")

    if passed == total:
        print("\n🎉 Tous les tests ont réussi ! L'application est prête à être utilisée.")
        return 0
    else:
        print("\n⚠️ Certains tests ont échoué. Veuillez vérifier la sortie ci-dessus.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
