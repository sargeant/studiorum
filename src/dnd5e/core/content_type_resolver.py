"""Content type resolution without circular dependencies."""

from .interfaces import ContentTypeResolver, get_content_type_registry
from .models.content import BaseContent, ContentType


class RegistryBasedContentTypeResolver:
    """Content type resolver using registry pattern to avoid circular imports."""

    def __init__(self) -> None:
        self._registry = get_content_type_registry()
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Ensure the registry is initialized with all content types."""
        if self._initialized:
            return

        # Import and register all content types
        # This is done lazily to avoid circular imports
        self._register_all_types()
        self._initialized = True

    def _register_all_types(self) -> None:
        """Register all content types in the registry."""
        # Import all model classes
        from .models.adventures import Adventure
        from .models.backgrounds import Background
        from .models.books import Book
        from .models.classes import Class, ClassFeature, SubclassFeature
        from .models.creatures import Creature
        from .models.feats import Feat
        from .models.fluff import CreatureFluff, ItemFluff, SpellFluff
        from .models.items import Item
        from .models.nested_content import (
            Inset,
            Section,
            Table,
            VariantRule,
        )
        from .models.races import Race
        from .models.spells import Spell

        # Register all content types
        self._registry.register(Adventure, ContentType.ADVENTURE)
        self._registry.register(Background, ContentType.BACKGROUND)
        self._registry.register(Book, ContentType.BOOK)
        self._registry.register(Class, ContentType.CLASS)
        self._registry.register(ClassFeature, ContentType.CLASS_FEATURE)
        self._registry.register(SubclassFeature, ContentType.SUBCLASS_FEATURE)
        self._registry.register(Creature, ContentType.CREATURE)
        self._registry.register(Feat, ContentType.FEAT)
        self._registry.register(Item, ContentType.ITEM)
        self._registry.register(Race, ContentType.RACE)
        self._registry.register(Spell, ContentType.SPELL)
        self._registry.register(CreatureFluff, ContentType.CREATURE_FLUFF)
        self._registry.register(ItemFluff, ContentType.ITEM_FLUFF)
        self._registry.register(SpellFluff, ContentType.SPELL_FLUFF)

        # Register nested content types
        self._registry.register(Section, ContentType.ADVENTURE_SECTION)
        self._registry.register(Table, ContentType.ADVENTURE_TABLE)
        self._registry.register(Inset, ContentType.ADVENTURE_INSET)
        self._registry.register(Section, ContentType.BOOK_SECTION)
        self._registry.register(VariantRule, ContentType.VARIANT_RULE)
        self._registry.register(Table, ContentType.BOOK_TABLE)
        self._registry.register(Inset, ContentType.BOOK_INSET)

    def resolve_type(self, content: BaseContent) -> ContentType:
        """Resolve content type from content instance.

        Args:
            content: Content instance to analyze

        Returns:
            Resolved content type
        """
        self._ensure_initialized()
        result = self._registry.get_type(content)
        if result is None:
            raise ValueError(f"Unknown content type for {type(content).__name__}")
        return result

    def register_type(
        self, content_class: type[BaseContent], content_type: ContentType
    ) -> None:
        """Register a content class with its type.

        Args:
            content_class: Content class to register
            content_type: Associated content type
        """
        self._registry.register(content_class, content_type)


# Global resolver instance
_content_type_resolver = RegistryBasedContentTypeResolver()


def get_content_type_resolver() -> ContentTypeResolver:
    """Get the global content type resolver.

    Returns:
        Global content type resolver instance
    """
    return _content_type_resolver


def reset_content_type_resolver() -> None:
    """Reset the global content type resolver (for testing).

    This recreates the global resolver instance to ensure clean state.
    """
    global _content_type_resolver
    _content_type_resolver = RegistryBasedContentTypeResolver()
