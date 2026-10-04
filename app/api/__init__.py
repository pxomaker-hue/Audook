"""HTTP API, split into Flask blueprints by area (see register_blueprints)."""


def register_blueprints(flask_app):
    from app.api import (authors, bookmarks, books, cast, collections, covers, equalizer,
                         history, player, progress, servers, sync, system)
    for module in (servers, books, bookmarks, progress, authors, history, collections,
                   player, equalizer, cast, sync, covers, system):
        flask_app.register_blueprint(module.bp)
