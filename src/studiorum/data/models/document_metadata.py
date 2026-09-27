"""What a document says about itself: its title, kind and front and back matter."""

from enum import Enum

from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    """A book or an adventure; adventures set their headings as books do."""

    BOOK = "book"
    ADVENTURE = "adventure"


class DocumentMetadata(BaseModel):
    """The title page, table of contents and index of a document."""

    title: str = Field(..., description="Document title")
    subtitle: str | None = Field(None, description="Document subtitle")
    document_type: DocumentType = Field(
        default=DocumentType.BOOK, description="Type of document"
    )
    include_toc: bool = Field(True, description="Include table of contents")
    include_index: bool = Field(False, description="Include document index")
