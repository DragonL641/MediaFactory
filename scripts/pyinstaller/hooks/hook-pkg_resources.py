"""
PyInstaller hook for pkg_resources.
Disables the pyi_rth_pkgres runtime hook to avoid jaraco.text issues.
"""

# Collect pkg_resources as a module
from PyInstaller.utils.hooks import collect_submodules
hiddenimports = collect_submodules('pkg_resources')
