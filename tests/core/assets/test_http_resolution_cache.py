from pathlib import Path

import pytest

from studiorum.core.assets.image_sources import (
    HttpApiImageSourceConfig,
    ImageSourceRegistry,
)


@pytest.mark.fast
def test_http_resolution_uses_cached_file(tmp_path: Path) -> None:
    registry = ImageSourceRegistry(cache_dir=tmp_path)
    cfg = HttpApiImageSourceConfig(
        name="test-http",
        base_url="https://example.com/images",
        priority=10,
        path_template="{image_path}",
        timeout_seconds=5,
    )
    assert registry.add_source(cfg).is_success()

    image_path = "creatures/dragon.png"
    key = registry._generate_cache_key(image_path, cfg.name)  # type: ignore[attr-defined]
    cache_dir = tmp_path / cfg.name / "http"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"{key}.png"
    cache_file.write_bytes(b"dummy")

    import asyncio

    result = asyncio.get_event_loop().run_until_complete(
        registry.resolve_image(image_path)
    )
    assert result.is_success()
    asset = result.value  # type: ignore[attr-defined]
    assert asset.local_path == cache_file
    assert asset.source_name == cfg.name


def test_http_resolution_uses_cached_file_sync_alias(tmp_path: Path) -> None:
    # Alias test to ensure stability across different test names
    test_http_resolution_uses_cached_file(tmp_path)
