"""New tag resolver facade providing backward compatibility."""

from typing import List, Dict, Any, Optional, Callable
from .tag_parser import TagParser, TagParseError
from .tag_renderer import TagRenderer, RendererContext
from .tag_handlers import TagHandler
from .content_tracker import ContentTracker


class NewTagResolverFacade:
    """Facade providing backward compatibility with the old TagResolver API."""
    
    def __init__(self, omnidexer=None):
        self.omnidexer = omnidexer
        self.parser = TagParser()
        self.renderer = TagRenderer(omnidexer)
        
        # For backward compatibility with custom handlers
        self._custom_handlers: Dict[str, Callable] = {}
    
    def process_text(self, text: str) -> str:
        """Process text with tags and return rendered output.
        
        This method maintains compatibility with the old TagResolver.process_text API.
        """
        if not text:
            return text
        
        try:
            # Parse text to AST
            document = self.parser.parse(text)
            
            # Render AST to output
            return self.renderer.render_document(document)
        
        except Exception as e:
            # Fallback to original text on parse/render failure
            # In production, you might want to log this error
            return text
    
    def register_tag_handler(self, tag_type: str, handler_func: Callable) -> None:
        """Register a custom tag handler function for backward compatibility.
        
        This maintains compatibility with the old API where users could register
        simple functions as tag handlers.
        """
        self._custom_handlers[tag_type] = handler_func
        
        # Create a wrapper handler that adapts the function to our new interface
        wrapper_handler = LegacyHandlerWrapper(tag_type, handler_func)
        self.renderer.register_handler(wrapper_handler)
    
    def register_handler(self, handler: TagHandler) -> None:
        """Register a new-style tag handler."""
        self.renderer.register_handler(handler)
    
    def get_tracked_content_for_appendix(self) -> List[tuple]:
        """Get tracked content for appendix generation.
        
        Returns content in the format: [(type, name, source), ...]
        """
        tracked_content = self.renderer.get_tracked_content()
        return [content.to_tuple() for content in tracked_content]
    
    def get_tracked_content_detailed(self) -> Dict[str, List[Dict[str, str]]]:
        """Get detailed tracked content for appendix generation."""
        return self.renderer.get_tracked_content_for_appendix()
    
    def clear_tracked_content(self) -> None:
        """Clear all tracked content."""
        self.renderer.clear_tracked_content()
    
    def get_content_statistics(self) -> Dict[str, int]:
        """Get statistics about tracked content."""
        return self.renderer.get_content_statistics()
    
    def track_document_content(self, text: str) -> None:
        """Track content in a document without rendering."""
        try:
            document = self.parser.parse(text)
            self.renderer.track_document_content(document)
        except Exception:
            # Ignore tracking errors
            pass
    
    def get_supported_tag_types(self) -> List[str]:
        """Get all supported tag types."""
        return self.renderer.get_supported_tag_types()
    
    def has_handler(self, tag_type: str) -> bool:
        """Check if a handler exists for the given tag type."""
        return self.renderer.has_handler(tag_type)
    
    # Backward compatibility properties and methods
    @property
    def _tag_handlers(self) -> Dict[str, Any]:
        """Backward compatibility property."""
        # Return a dict-like view of handlers for backward compatibility
        return self._custom_handlers


class LegacyHandlerWrapper(TagHandler):
    """Wrapper to adapt old-style handler functions to the new TagHandler interface."""
    
    def __init__(self, tag_type: str, handler_func: Callable):
        self.tag_type = tag_type
        self.handler_func = handler_func
    
    def handles(self, tag_type: str) -> bool:
        """Check if this handler handles the tag type."""
        return tag_type == self.tag_type
    
    def render(self, node, context: RendererContext) -> str:
        """Render using the legacy handler function."""
        try:
            # Create a legacy TagMatch-like object for compatibility
            legacy_tag = LegacyTagMatch(node)
            return self.handler_func(legacy_tag)
        except Exception:
            # Fallback to node name
            return getattr(node, 'name', str(node))
    
    def track_content(self, node, tracker: ContentTracker) -> None:
        """Legacy handlers don't track content."""
        pass


class LegacyTagMatch:
    """Compatibility class that mimics the old TagMatch interface."""
    
    def __init__(self, node):
        self.tag_type = node.tag_type
        self.name = getattr(node, 'name', '')
        self.source = getattr(node, 'source', None)
        self.page = getattr(node, 'page', None)
        
        # For display_text, try to extract from display_text_nodes
        if hasattr(node, 'display_text_nodes') and node.display_text_nodes:
            # Simple text extraction - in reality you might want more sophisticated handling
            self.display_text = ''.join(
                getattr(child, 'text', str(child))
                for child in node.display_text_nodes
            )
        else:
            self.display_text = None
    
    def get_display_text(self) -> str:
        """Get display text or fallback to name."""
        return self.display_text if self.display_text else self.name