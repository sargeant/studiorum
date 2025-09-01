"""LaTeX formatting component for character escaping and structure-based formatting."""

from typing import Any


class LaTeXFormatter:
    """Handles LaTeX character escaping and structure-based formatting.

    This component handles all LaTeX formatting logic previously in TemplateService,
    focused purely on LaTeX character escaping and structure-specific formatting
    without any text extraction or tag processing.
    """

    def format_text(self, text: str, original_entry: Any = None) -> str:
        """Apply LaTeX formatting to processed text.

        Args:
            text: Text content to format (already processed through tag resolver)
            original_entry: Original entry object for structure-based formatting

        Returns:
            LaTeX-formatted text with proper escaping and structure formatting
        """
        if not text:
            return text

        # Apply itemSub formatting if needed
        # Note: Text from TagResolver is already LaTeX-escaped, so we only
        # need to handle structure-specific formatting here
        if self.has_itemsub_entries(original_entry):
            return self.format_itemsub_entries(text, original_entry)

        return text

    def escape_latex_chars(self, text: str) -> str:
        """Escape LaTeX special characters in text.

        Args:
            text: Text to escape

        Returns:
            LaTeX-escaped text
        """
        if not text:
            return text

        # Match the original TemplateService._escape_latex method exactly
        replacements = {
            "&": r"\&",
            "%": r"\%",
            "$": r"\$",
            "#": r"\#",
            "^": r"\textasciicircum{}",
            "_": r"\_",
            "{": r"\{",
            "}": r"\}",
            "~": r"\textasciitilde{}",
            "\\": r"\textbackslash{}",
        }

        for char, replacement in replacements.items():
            text = text.replace(char, replacement)

        return text

    def format_itemsub_entries(self, processed_text: str, original_entry: Any) -> str:
        """Apply itemSub-specific LaTeX formatting after tag processing.

        Args:
            processed_text: Text after tag processing
            original_entry: Original entry object to check for itemSub structure

        Returns:
            Text with itemSub formatting applied
        """
        # Check if this entry contains itemSub entries
        has_itemsub = self.has_itemsub_entries(original_entry)
        if not has_itemsub:
            return processed_text

        # Format itemSub entries: make names italic and separate with line breaks
        lines = processed_text.split("\n\n")
        formatted_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if line starts with a name pattern (ends with .)
            if ". " in line and not line.startswith(" "):
                # Split at first '. ' to separate name from description
                parts = line.split(". ", 1)
                if len(parts) == 2:
                    name, description = parts
                    # Skip if this is just the intro line
                    if "following flaws" not in line.lower():
                        formatted_line = f"\\textit{{{name}.}} {description}"
                        formatted_lines.append(formatted_line)
                    else:
                        formatted_lines.append(line)
                else:
                    formatted_lines.append(line)
            else:
                formatted_lines.append(line)

        return "\n\n".join(formatted_lines)

    def has_itemsub_entries(self, entry: Any) -> bool:
        """Check if entry contains itemSub structures.

        Args:
            entry: Entry object to check

        Returns:
            True if entry contains itemSub structures
        """
        if hasattr(entry, "entries") and entry.entries:
            for subentry in entry.entries:
                if hasattr(subentry, "items") and subentry.items:
                    for item in subentry.items:
                        if isinstance(item, dict) and item.get("type") == "itemSub":
                            return True
        return False
