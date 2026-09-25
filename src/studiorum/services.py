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

from studiorum.core.config.unified_config import ApplicationConfig
from studiorum.core.loaders.data_dir import DataSet
from studiorum.core.loaders.omnidexer import Omnidexer
from studiorum.core.logging import get_logger
from studiorum.core.protocols.progress import ProgressCallback
from studiorum.core.services.content_list_writer import ContentListWriter
from studiorum.latex_engine.services.template_service import TemplateService
from studiorum.renderers.tags import TagResolver

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
    def _omnidexer(self) -> Omnidexer:
        return Omnidexer(self.data)

    def load_omnidexer(
        self, progress_callback: ProgressCallback | None = None
    ) -> Omnidexer:
        """The omnidexer with all data loaded.

        The first call loads, reporting to ``progress_callback`` if one is
        given; later calls return the same instance.
        """
        omnidexer = self._omnidexer
        with self._load_lock:
            if not self._loaded.is_set():
                _load(omnidexer, progress_callback)
                self._loaded.set()
        return omnidexer

    @property
    def omnidexer(self) -> Omnidexer:
        return self.load_omnidexer()

    @cached_property
    def tag_resolver(self) -> TagResolver:
        return TagResolver()

    @cached_property
    def template_service(self) -> TemplateService:
        return TemplateService(
            tag_resolver=self.tag_resolver,
            omnidexer=self.omnidexer,
        )

    @cached_property
    def content_list_writer(self) -> ContentListWriter:
        return ContentListWriter()


def build_services(config: ApplicationConfig) -> Services:
    """Services for ``config``. Nothing is loaded until a member is used."""
    return Services(config=config)


def _load(omnidexer: Omnidexer, progress_callback: ProgressCallback | None) -> None:
    if progress_callback is None:
        omnidexer.load_all_data()
    else:
        operation_id = progress_callback.start_operation(
            "Loading 5e content data", metadata={"stage": "lazy_loading"}
        )
        try:
            omnidexer.load_all_data(progress_callback=progress_callback)
        except Exception as e:
            progress_callback.complete_operation(operation_id, error=e)
            raise
        progress_callback.complete_operation(
            operation_id, result="Content data loaded successfully"
        )
