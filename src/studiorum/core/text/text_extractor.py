"""Text extraction component for 5etools entry structures."""

from typing import Any


class TextExtractor:
    """Extracts text from 5etools entry structures.

    This component handles all text extraction logic previously in TemplateService,
    focused purely on extracting readable text from various 5etools entry formats
    without any LaTeX formatting or tag processing.
    """

    def extract_from_entry(self, entry: Any) -> str:
        """Extract text content from various entry formats with names included.

        Args:
            entry: Entry object in various formats

        Returns:
            Extracted text content with entry names
        """
        if isinstance(entry, str):
            return entry

        if isinstance(entry, dict):
            # Handle common 5etools entry patterns
            if "entries" in entry and entry["entries"] is not None:
                # Recursively process nested entries
                parts = []
                # Include the name if present (for LaTeX formatting like \subsection{Name})
                # BUT skip for entries where the renderer already handles the name
                is_spell = (
                    "level" in entry and "school" in entry and "components" in entry
                )
                if "name" in entry and entry["name"] and not is_spell:
                    parts.append(entry["name"])
                # Include the "by" field if present (author attribution)
                if "by" in entry and entry["by"]:
                    parts.append(f"by {entry['by']}")
                for sub_entry in entry["entries"]:
                    text = self.extract_from_entry(sub_entry)
                    if text:  # Only add non-empty text
                        parts.append(text)
                return " ".join(parts)
            elif "text" in entry:
                # Include name if present for named text entries
                if "name" in entry and entry["name"]:
                    return f"{entry['name']} {entry['text']}"
                return entry["text"]
            elif "items" in entry and isinstance(entry["items"], list):
                # Handle list items including itemSub entries
                parts = []
                for item in entry["items"]:
                    if isinstance(item, dict) and item.get("type") == "itemSub":
                        # Extract itemSub content with proper formatting
                        item_name = item.get("name", "")
                        item_entry = item.get("entry", "") or item.get("text", "")
                        if item_name and item_entry:
                            parts.append(f"{item_name}. {item_entry}")
                        elif item_entry:
                            parts.append(item_entry)
                        elif item_name:
                            parts.append(f"{item_name}.")
                    else:
                        text = self.extract_from_entry(item)
                        if text:  # Only add non-empty text
                            parts.append(text)
                # Join itemSub entries with line breaks between items, but name+description on same line
                return " ".join(parts) if len(parts) <= 1 else "\n\n".join(parts)
            elif "entries" in entry and isinstance(entry["entries"], list):
                # Handle entries list
                parts = []
                for e in entry["entries"]:
                    text = self.extract_from_entry(e)
                    if text:  # Only add non-empty text
                        parts.append(text)
                return " ".join(parts)

        # Handle objects with get_description_text method (like test mocks)
        # But avoid circular calls - if this is a Pydantic model, process it directly
        if hasattr(entry, "get_description_text") and not hasattr(entry, "model_dump"):
            return entry.get_description_text()

        # Handle spellcasting objects specifically
        if hasattr(entry, "headerEntries") and hasattr(entry, "spells"):
            parts = []

            # Add header entries
            if entry.headerEntries:
                header_parts = []
                for header in entry.headerEntries:
                    header_parts.append(self.extract_from_entry(header))
                if header_parts:
                    parts.append(" ".join(header_parts))

            # Add spell lists if present
            if entry.spells:
                spell_parts = []
                for level, spell_group in entry.spells.items():
                    level_name = (
                        "Cantrips"
                        if level == "0"
                        else f"{level}{'st' if level == '1' else 'nd' if level == '2' else 'rd' if level == '3' else 'th'} level"
                    )
                    if hasattr(spell_group, "slots") and spell_group.slots:
                        level_name += f" ({spell_group.slots} slots)"

                    if hasattr(spell_group, "spells") and spell_group.spells:
                        spells_text = ", ".join(
                            str(spell) for spell in spell_group.spells
                        )
                        spell_parts.append(f"{level_name}: {spells_text}")

                if spell_parts:
                    # Join spell lists with double newline for paragraph breaks
                    parts.append("\n\n".join(spell_parts))

            # Add footer entries
            if hasattr(entry, "footerEntries") and entry.footerEntries:
                footer_parts = []
                for footer in entry.footerEntries:
                    footer_parts.append(self.extract_from_entry(footer))
                if footer_parts:
                    parts.append(" ".join(footer_parts))

            # Join major sections with paragraph breaks
            return "\n\n".join(parts)

        # Handle Pydantic models
        if hasattr(entry, "model_dump"):
            # Check for special attributes first
            if (
                hasattr(entry, "items")
                and entry.items
                and isinstance(entry.items, list)
            ):
                # Handle list items from Pydantic models including itemSub entries
                parts = []
                for item in entry.items:
                    if isinstance(item, dict) and item.get("type") == "itemSub":
                        # Extract itemSub content with proper formatting
                        item_name = item.get("name", "")
                        item_entry = item.get("entry", "") or item.get("text", "")
                        if item_name and item_entry:
                            parts.append(f"{item_name}. {item_entry}")
                        elif item_entry:
                            parts.append(item_entry)
                        elif item_name:
                            parts.append(f"{item_name}.")
                    else:
                        text = self.extract_from_entry(item)
                        if text:  # Only add non-empty text
                            parts.append(text)
                # Join itemSub entries with line breaks between items, but name+description on same line
                return " ".join(parts) if len(parts) <= 1 else "\n\n".join(parts)
            return self.extract_from_entry(entry.model_dump())

        # Handle list entries
        if isinstance(entry, list):
            parts = []
            for item in entry:
                text = self.extract_from_entry(item)
                if text:  # Only add non-empty text
                    parts.append(text)
            return " ".join(parts)

        # Handle table structures before fallback
        if isinstance(entry, dict) and entry.get("type") == "table":
            return self._extract_table_text(entry)

        # Handle None and empty cases
        if entry is None:
            return ""

        # Fallback to string representation
        return str(entry)

    def _extract_table_text(self, table: dict) -> str:
        """Extract meaningful text from table without JSON serialization."""
        parts = []

        # Add caption
        if table.get("caption"):
            parts.append(table["caption"])

        # Extract from rows (avoid serializing structure)
        if table.get("rows"):
            for row in table["rows"]:
                for cell in row:
                    if isinstance(cell, str):
                        parts.append(cell)
                    elif isinstance(cell, dict):
                        # Recursive extraction for complex cells
                        parts.append(self.extract_from_entry(cell))

        # Handle footnotes
        if table.get("footnotes"):
            for footnote in table["footnotes"]:
                parts.append(self.extract_from_entry(footnote))

        return " ".join(filter(None, parts))

    def extract_content_only_from_entry(self, entry: Any) -> str:
        """Extract text content from entry formats, excluding the entry name.

        Args:
            entry: Entry object in various formats

        Returns:
            Extracted text content without the entry name
        """
        if isinstance(entry, str):
            return entry

        if isinstance(entry, dict):
            # Handle common 5etools entry patterns
            if "entries" in entry and entry["entries"] is not None:
                # Recursively process nested entries, but skip the name
                parts = []
                # Skip the name for content-only extraction
                # Include the "by" field if present (author attribution)
                if "by" in entry and entry["by"]:
                    parts.append(f"by {entry['by']}")
                for sub_entry in entry["entries"]:
                    text = self.extract_from_entry(sub_entry)
                    if text:  # Only add non-empty text
                        parts.append(text)
                return " ".join(parts)
            elif "text" in entry:
                # Include name if present for named text entries
                if "name" in entry and entry["name"]:
                    return f"{entry['name']} {entry['text']}"
                return entry["text"]
            elif "items" in entry and isinstance(entry["items"], list):
                # Handle list items including itemSub entries
                parts = []
                for item in entry["items"]:
                    if isinstance(item, dict) and item.get("type") == "itemSub":
                        # Extract itemSub content with proper formatting
                        item_name = item.get("name", "")
                        item_entry = item.get("entry", "") or item.get("text", "")
                        if item_name and item_entry:
                            parts.append(f"{item_name}. {item_entry}")
                        elif item_entry:
                            parts.append(item_entry)
                        elif item_name:
                            parts.append(f"{item_name}.")
                    else:
                        text = self.extract_from_entry(item)
                        if text:  # Only add non-empty text
                            parts.append(text)
                # Join itemSub entries with line breaks between items, but name+description on same line
                return " ".join(parts) if len(parts) <= 1 else "\n\n".join(parts)
            elif "entries" in entry and isinstance(entry["entries"], list):
                # Handle entries list
                parts = []
                for e in entry["entries"]:
                    text = self.extract_from_entry(e)
                    if text:  # Only add non-empty text
                        parts.append(text)
                return " ".join(parts)

        # Handle Pydantic models
        if hasattr(entry, "model_dump"):
            # Check for EntriesEntry type - extract only the entries content
            if hasattr(entry, "entries") and entry.entries:
                parts = []
                for sub_entry in entry.entries:
                    text = self.extract_from_entry(sub_entry)
                    if text:
                        parts.append(text)
                return " ".join(parts)

        # Fallback to regular extraction
        return self.extract_from_entry(entry)
