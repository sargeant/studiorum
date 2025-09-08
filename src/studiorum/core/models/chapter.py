"""Shared chapter model for books and adventures."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ChapterType(str, Enum):
    """Type of chapter for special LaTeX handling."""

    INTRODUCTION = (
        "introduction"  # Unnumbered, in ToC (Introduction, Foreword, Preface, etc.)
    )
    CHAPTER = "chapter"  # Standard numbered chapter
    APPENDIX = "appendix"  # Appendix section
    PART = "part"  # Part (for multi-part books)


class Chapter(BaseModel):
    """Represents a chapter within a book or adventure."""

    name: str = Field(..., description="Chapter name")
    ordinal: dict[str, Any] | None = Field(None, description="Chapter numbering")
    headers: list[str | dict[str, Any]] | None = Field(
        None, description="Section headers"
    )
    entries: list[Any] = Field(default_factory=list, description="Chapter content")

    def get_chapter_number(self) -> str:
        """Get formatted chapter number."""
        if self.ordinal:
            if isinstance(self.ordinal, dict):
                ordinal_type = self.ordinal.get("type", "chapter")
                identifier = self.ordinal.get("identifier", "")
                if ordinal_type == "chapter" and identifier:
                    return f"Chapter {identifier}"
                elif ordinal_type == "part" and identifier:
                    return f"Part {identifier}"
                elif ordinal_type == "appendix" and identifier:
                    return f"Appendix {identifier}"
                elif identifier:
                    return str(identifier)
            return str(self.ordinal)
        return ""

    def get_clean_title(self, strip_manual_numbering: bool = False) -> str:
        """Get chapter title, optionally stripped of manual numbering.

        Args:
            strip_manual_numbering: If True, remove "Chapter X:" prefixes

        Returns:
            Clean chapter title for LaTeX native numbering
        """
        title = self.name

        if strip_manual_numbering:
            # Remove common manual numbering patterns
            import re

            # Match "Chapter X:" or "Part X:" at the start
            title = re.sub(r"^(Chapter|Part)\s+\d+:\s*", "", title)
            # Match "Appendix X:" at the start
            title = re.sub(r"^Appendix\s+[A-Z]:\s*", "", title)

        return title

    @field_validator("headers", mode="before")
    @classmethod
    def parse_headers(cls, v: Any) -> Any:
        """Parse headers from various formats."""
        if not v:
            return v

        if isinstance(v, list):
            result = []
            for item in v:
                if isinstance(item, str):
                    result.append(item)
                elif isinstance(item, dict):
                    # Extract header text from dict format
                    if "header" in item:
                        result.append(item["header"])
                    else:
                        result.append(str(item))
                else:
                    result.append(str(item))
            return result
        return v

    def get_formatted_headers(self) -> list[str]:
        """Get formatted header texts."""
        if not self.headers:
            return []

        result = []
        for header in self.headers:
            if isinstance(header, str):
                result.append(header)
            elif isinstance(header, dict):
                if "header" in header:
                    result.append(header["header"])
                else:
                    result.append(str(header))
            else:
                result.append(str(header))
        return result

    def get_chapter_type(self) -> ChapterType:
        """Determine chapter type from name pattern and content.

        Logic:
        - If name contains "Chapter N:" or "Ch. N:" → CHAPTER (numbered)
        - If name contains "Appendix X:" or "App. X:" → APPENDIX
        - Smart content detection for common appendix types → APPENDIX
        - Introduction-like content → INTRODUCTION
        - Otherwise → INTRODUCTION (default)
        """
        import re

        # Check for explicit numbered chapter pattern
        if re.search(r"(?:Chapter|Ch\.)\s+\d+:", self.name):
            return ChapterType.CHAPTER

        # Check for explicit appendix pattern
        if re.search(r"(?:Appendix|App\.)\s+[A-Z]:", self.name):
            return ChapterType.APPENDIX

        # Check ordinal field for additional hints (if present)
        if self.ordinal and isinstance(self.ordinal, dict):
            ordinal_type = self.ordinal.get("type", "").lower()
            if ordinal_type == "appendix":
                return ChapterType.APPENDIX
            elif ordinal_type == "part":
                return ChapterType.PART
            elif ordinal_type == "chapter":
                return ChapterType.CHAPTER

        # Smart content-based detection for 5etools data
        title_lower = self.name.lower()

        # Appendix-like content (should become lettered appendices)
        appendix_like_names = [
            "creatures",
            "npcs",
            "monsters",
            "bestiary",
            "magic items",
            "items",
            "equipment",
            "treasures",
            "spells",
            "artifacts",
            "credits",
            "handouts",
            "maps",
            "poster map",
            "story concept art",
            "concept art",
            "medals of merit",
            "fragments of suffering",
            "dm materials",
            "dungeon master",
            "bibliography",
        ]

        # Introduction-like content (should be unnumbered but in ToC)
        introduction_like_names = [
            "introduction",
            "foreword",
            "preface",
            "prologue",
            "epilogue",
            "conclusion",
            "afterword",
            "world of",
            "what is",
            "story overview",
            "running the adventure",
            "character advancement",
            "how to use",
            "about this",
        ]

        # Check for appendix-like content
        if any(appendix_name in title_lower for appendix_name in appendix_like_names):
            return ChapterType.APPENDIX

        # Check for introduction-like content
        if any(intro_name in title_lower for intro_name in introduction_like_names):
            return ChapterType.INTRODUCTION

        # Check if title starts with "appendix" (catch-all)
        if title_lower.startswith("appendix"):
            return ChapterType.APPENDIX

        # Default to CHAPTER (numbered) for regular content chapters
        # Only specific introduction-like content should be unnumbered
        return ChapterType.CHAPTER

    def get_appendix_letter(self) -> str | None:
        """Extract appendix letter (A, B, C, etc.) from name."""
        import re

        match = re.match(r"^(?:Appendix|App\.)\s+([A-Z]):", self.name)
        return match.group(1) if match else None
