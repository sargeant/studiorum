# Reworking the Omnidexer for Deep Indexing

## 1. Introduction

The current Python `Omnidexer` in `src/core/loaders/omnidexer.py` uses a flat indexing model. It successfully loads and indexes top-level content items (spells, creatures, etc.) but fails to parse and index nested entities within them. This limitation causes significant compatibility issues with the 5e.tools data structure, where complex data like class features, monster spell lists, and sub-entities within adventures are defined inside parent objects.

The original 5e.tools JavaScript codebase uses a "deep indexing" pattern, primarily through a `pGetDeepIndex` method, to recursively discover and index these nested items. This document outlines a plan to refactor the Python `Omnidexer` to implement a similar, robust deep indexing system.

## 2. Core Problem

The key difference lies in how the two systems handle nested data:

-   **JavaScript `Omnidexer`**: The `pAddToIndex` function iterates through top-level items and calls `pGetDeepIndex` on each. This method is responsible for returning an array of additional, fully-formed index entries for any sub-items. This allows, for example, a `Class` to provide indexable entries for all its `ClassFeatures` and `SubclassFeatures`.

-   **Python `Omnidexer`**: The `_add_to_index` method is called once for each top-level item discovered by a `DataLoader`. It has no mechanism to inspect the item for nested content that should also be indexed. This results in an incomplete index, missing critical data for lookups and rendering.

**Examples of Missed Data:**
- Features for a class or subclass.
- Spells known by a creature.
- Individual tables or sections within an adventure or book chapter.

## 3. Proposed Solution

To align the Python implementation with the source data's structure, we will introduce a deep indexing protocol that allows content models to expose their own sub-entities for indexing.

### 3.1. The `DeepIndexable` Protocol

We will define a new protocol (e.g., using `typing.Protocol`) that content models can implement.

```python
# In a new file, e.g., src/core/loaders/protocols.py

from typing import List, Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from .omnidexer import Omnidexer
    from ..models.content import BaseContent

class DeepIndexable(Protocol):
    """
    A protocol for content models that contain indexable sub-entities.
    """
    def get_deep_index_entries(self, omnidexer: "Omnidexer") -> List["BaseContent"]:
        """
        Returns a list of sub-entities that should be indexed.

        Args:
            omnidexer: The omnidexer instance, providing access to the main index
                       for resolving references if needed.
        """
        ...
```

### 3.2. `Omnidexer` Modification

The `Omnidexer._add_to_index` method will be updated to recognize and utilize this protocol.

```python
# In src/core/loaders/omnidexer.py

class Omnidexer:
    # ... existing methods ...

    def _add_to_index(self, content: BaseContent, content_type: ContentType):
        """Add content item and its sub-entities to all indexes."""
        # Prevent duplicate processing in a single load operation
        if self._is_already_indexed(content):
            return

        entry = IndexEntry.create(content, content_type)
        # ... existing indexing logic for the primary entry ...
        self._index[entry.hash_id] = entry
        # ... etc ...

        # --- DEEP INDEXING LOGIC ---
        # Check if the content item can be deep-indexed
        if hasattr(content, "get_deep_index_entries"):
            try:
                # Pass the omnidexer instance to allow sub-entities to resolve references
                sub_entries = content.get_deep_index_entries(self)
                for sub_content in sub_entries:
                    # Recursively call _add_to_index for each sub-entity
                    # The sub-entity's type will be determined from its model
                    sub_content_type = ContentType.from_content(sub_content)
                    if sub_content_type:
                        self._add_to_index(sub_content, sub_content_type)
            except Exception as e:
                logger.error(f"Failed during deep indexing of {content.name}: {e}")

    def _is_already_indexed(self, content: BaseContent) -> bool:
        # Helper to avoid cycles and redundant processing
        # ... implementation using hash or object ID ...
        pass
```

### 3.3. Content Model Implementation

The core of the work will be implementing the `get_deep_index_entries` method on the relevant Pydantic models in `src/core/models/`.

-   **`Class` (`src/core/models/classes.py`)**:
    -   Iterate through `classFeature` and `subclassFeature` lists.
    -   Return these features as a list of `BaseContent` objects to be indexed.

-   **`Creature` (`src/core/models/creatures.py`)**:
    -   Parse the `spellcasting` trait entries.
    -   For each spell name mentioned, use the `omnidexer.find(ContentType.SPELL, ...)` method to look up the full spell object.
    -   Return the list of found `Spell` objects. This is critical for linking creatures to their spells.

-   **`Adventure` & `Book` (`src/core/models/adventures.py`, `books.py`)**:
    -   Iterate through chapters and their `entries`.
    -   Recursively parse the entry structure to find and yield indexable content like tables, lists, or other nested data types that should be searchable.

## 4. Implementation Steps

1.  **Create Protocol:** Define the `DeepIndexable` protocol in `src/core/loaders/protocols.py`.
2.  **Update Omnidexer:** Modify `Omnidexer._add_to_index` to include the recursive deep indexing logic. Implement a cycle-prevention mechanism (`_is_already_indexed`).
3.  **Implement on Models (Incremental):**
    -   Start with a simple case, like `Class` and its features.
    -   Write a unit test in `tests/unit/test_omnidexer.py` to confirm that after loading a class, its features can be found via `omnidexer.find()`.
    -   Proceed to more complex models like `Creature`, implementing the logic to resolve spell names to spell objects.
    -   Finally, tackle `Adventure` and `Book` models.
4.  **Refactor DataLoaders (If Needed):** The `DataLoader`s should continue to focus on loading raw data into Pydantic models. The deep indexing logic should remain encapsulated within the models themselves, triggered by the `Omnidexer`. No major changes to loaders are anticipated.

## 5. Conclusion

By implementing this deep indexing system, the Python `Omnidexer` will achieve much greater parity with the 5e.tools data model. This will resolve many of the edge cases caused by missing nested data, leading to a more complete, accurate, and useful content index for all downstream operations, including search, cross-referencing, and PDF rendering.
