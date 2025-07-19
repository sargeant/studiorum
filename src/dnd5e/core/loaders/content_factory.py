"""Content factory for creating content instances without tight coupling."""

from typing import Any

from ..interfaces import ContentLoader, get_content_type_registry
from ..models.content import BaseContent, ContentType


class ContentFactory:
    """Factory for creating content instances based on content type."""

    def __init__(self):
        self._registry = get_content_type_registry()
        self._class_map: dict[ContentType, type[BaseContent]] = {}
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Ensure the factory is initialized with all content classes."""
        if self._initialized:
            return

        self._initialize_class_map()
        self._initialized = True

    def _initialize_class_map(self) -> None:
        """Initialize the content class mapping."""
        # Import all model classes
        from ..models.adventures import Adventure
        from ..models.backgrounds import Background
        from ..models.books import Book
        from ..models.classes import Class
        from ..models.creatures import Creature
        from ..models.feats import Feat
        from ..models.fluff import CreatureFluff, ItemFluff, SpellFluff
        from ..models.items import Item
        from ..models.races import Race
        from ..models.spells import Spell

        # Build class map
        self._class_map = {
            ContentType.ADVENTURE: Adventure,
            ContentType.BACKGROUND: Background,
            ContentType.BOOK: Book,
            ContentType.CLASS: Class,
            ContentType.CREATURE: Creature,
            ContentType.FEAT: Feat,
            ContentType.ITEM: Item,
            ContentType.RACE: Race,
            ContentType.SPELL: Spell,
            ContentType.CREATURE_FLUFF: CreatureFluff,
            ContentType.ITEM_FLUFF: ItemFluff,
            ContentType.SPELL_FLUFF: SpellFluff,
        }

    def create_content(
        self, data: dict[str, Any], content_type: ContentType
    ) -> BaseContent:
        """Create content instance from data.

        Args:
            data: Raw data dictionary
            content_type: Type of content to create

        Returns:
            Created content instance

        Raises:
            ValueError: If content type is not supported
        """
        self._ensure_initialized()

        if content_type not in self._class_map:
            raise ValueError(f"Unsupported content type: {content_type}")

        content_class = self._class_map[content_type]
        return content_class.model_validate(data)

    def get_supported_types(self) -> list[ContentType]:
        """Get list of supported content types.

        Returns:
            List of supported content types
        """
        self._ensure_initialized()
        return list(self._class_map.keys())

    def register_content_class(
        self, content_type: ContentType, content_class: type[BaseContent]
    ) -> None:
        """Register a content class for a content type.

        Args:
            content_type: Content type to register
            content_class: Content class to register
        """
        self._class_map[content_type] = content_class
        # Also register in the type registry
        self._registry.register(content_class, content_type)


# Global factory instance
_content_factory = ContentFactory()


def get_content_factory() -> ContentFactory:
    """Get the global content factory.

    Returns:
        Global content factory instance
    """
    return _content_factory
