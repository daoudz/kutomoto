"""
kutomoto.designer.exceptions
Exception hierarchy for visual form designer and workflow compilation.
Copyrights reserved to 90Studio
"""


class CompilationError(Exception):
    """Base exception for all visual designer and compiler errors."""

    pass


class EmptyLayoutError(CompilationError, ValueError):
    """Raised when a visual form layout contains no visual boxes."""

    pass


class GeometryError(CompilationError, ValueError):
    """Raised when canvas or box geometry is non-positive, negative, or exceeds boundaries."""

    pass


class DuplicateBoxIdError(CompilationError, ValueError):
    """Raised when multiple visual boxes share an identical identifier."""

    pass


class OptimizationError(CompilationError):
    """Raised when peephole optimization fails or encounters an invalid step graph."""

    pass
