#!/usr/bin/env python3
"""Debug script to check what content is being indexed."""

import asyncio

from dnd5e.core.loaders.omnidexer import Omnidexer
from dnd5e.core.models.content import ContentType


async def main():
    omnidexer = Omnidexer(enable_deep_indexing=True)

    try:
        await omnidexer.load_all_data()
    except Exception as e:
        print(f"Error loading data: {e}")
        return

    # Check what adventures we have
    adventures = omnidexer.get_all_by_type(ContentType.ADVENTURE)
    print(f"Found {len(adventures)} adventures")
    if adventures:
        print(f"First adventure: {adventures[0].name}")

    # Check adventure nested content
    adventure_content_types = [
        ContentType.ADVENTURE_SECTION,
        ContentType.ADVENTURE_TABLE,
        ContentType.ADVENTURE_INSET,
    ]

    for content_type in adventure_content_types:
        content = omnidexer.get_all_by_type(content_type)
        print(f"Found {len(content)} {content_type.value}")
        if content:
            print(f"  First: {content[0].name}")

    # Check books too
    books = omnidexer.get_all_by_type(ContentType.BOOK)
    print(f"Found {len(books)} books")

    book_content_types = [
        ContentType.BOOK_SECTION,
        ContentType.VARIANT_RULE,
        ContentType.BOOK_TABLE,
        ContentType.BOOK_INSET,
    ]

    for content_type in book_content_types:
        content = omnidexer.get_all_by_type(content_type)
        print(f"Found {len(content)} {content_type.value}")


if __name__ == "__main__":
    asyncio.run(main())
