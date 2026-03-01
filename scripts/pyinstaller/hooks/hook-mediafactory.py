"""
PyInstaller hook for MediaFactory package.
This hook ensures all resources and dynamically imported modules are included.
"""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Include all mediafactory modules
hiddenimports = collect_submodules('mediafactory')

# Explicitly include LLM modules (OpenAI compatible backend)
hiddenimports += [
    'openai',
]

# Include resources
datas = collect_data_files('mediafactory')
