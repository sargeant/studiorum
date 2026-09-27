"""The objects the CLI and the MCP server share, built from one configuration.

``build_services(config)`` returns a frozen ``Services``. Each member is built
on first use and then kept, so a command that never touches content never
loads the data set. The CLI builds one per invocation in the Typer callback;
the MCP server builds one per process.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from functools import cached_property

from studiorum.config import ApplicationConfig
from studiorum.data.catalogue import Catalogue
from studiorum.data.content_list_writer import ContentListWriter
from studiorum.data.loaders.data_dir import DataSet
from studiorum.data.progress import ProgressCallback
from studiorum.log import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class Services:
    """Configuration plus the long-lived objects built from it."""

    config: ApplicationConfig
    _load_lock: threading.Lock = field(
        default_factory=threading.Lock, init=False, repr=False, compare=False
    )
    _loaded: threading.Event = field(
        default_factory=threading.Event, init=False, repr=False, compare=False
    )

    @cached_property
    def data(self) -> DataSet:
        return DataSet.from_config(self.config.data)

    @cached_property
    def _catalogue(self) -> Catalogue:
        return Catalogue(self.data)

    def load_catalogue(
        self, progress_callback: ProgressCallback | None = None
    ) -> Catalogue:
        """The catalogue with all data loaded.

        The first call loads, reporting to ``progress_callback`` if one is
        given; later calls return the same instance.
        """
        catalogue = self._catalogue
        with self._load_lock:
            if not self._loaded.is_set():
                _load(catalogue, progress_callback)
                self._loaded.set()
        return catalogue

    @property
    def catalogue(self) -> Catalogue:
        return self.load_catalogue()

    @cached_property
    def content_list_writer(self) -> ContentListWriter:
        return ContentListWriter()


def build_services(config: ApplicationConfig) -> Services:
    """Services for ``config``. Nothing is loaded until a member is used."""
    return Services(config=config)


def _load(catalogue: Catalogue, progress_callback: ProgressCallback | None) -> None:
    if progress_callback is None:
        catalogue.load_all_data()
    else:
        operation_id = progress_callback.start_operation(
            "Loading 5e content data", metadata={"stage": "lazy_loading"}
        )
        try:
            catalogue.load_all_data(progress_callback=progress_callback)
        except Exception as e:
            progress_callback.complete_operation(operation_id, error=e)
            raise
        progress_callback.complete_operation(
            operation_id, result="Content data loaded successfully"
        )
