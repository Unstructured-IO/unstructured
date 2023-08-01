import os
import importlib

# List all the files in the current directory
current_directory = os.path.dirname(__file__)
all_files = os.listdir(current_directory)
exclude_files = ["__init__.py", "utils.py"]

# Filter for Python files and exclude __init__.py and other excluded files
command_modules = [
    file[:-3] for file in all_files if file.endswith(".py") and file not in exclude_files
]

# Dynamically import the modules and create the __all__ list
__all__ = []
for module_name in command_modules:
    module = importlib.import_module("." + module_name, package=__name__)
    __all__.append(module_name)
    globals()[module_name] = module.get_cmd
