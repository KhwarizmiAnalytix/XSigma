"""
XSigma Build System Helper Modules

This package contains modular helper modules for the XSigma build system,
extracted from setup.py for better organization and maintainability.

Modules:
    - cppcheck: Static analysis with cppcheck
    - build: Build operations
    - config: Configuration generation
    - test: Test execution
    - sanitizer: Sanitizer operations
    - cpu_isa: Runtime CPU ISA probes (test-run gating)

Coverage analysis is the coverage-tool PyPI package (pip install coverage-tool),
invoked from Scripts/setup.py when the coverage token is set.
"""

__version__ = "1.0.0"
__all__ = [
    "cppcheck",
    "build",
    "config",
    "test",
    "sanitizer",
    "cpu_isa",
]
