"""Small helpers shared across blueprints."""


def format_chapter_title(index, title):
    """Prefix the chapter number before its title wherever the "currently
    playing chapter" is shown - some sources (and our own fallback naming)
    give every chapter the same/generic title, which is otherwise
    impossible to tell apart on the player."""
    if title is None:
        return None
    return f"{index + 1}. {title}"
