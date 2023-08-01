import os

exlude_files = ["__init__.py", "utils.py"]
# Get a list of all Python files in the current directory (excluding __init__.py)
__all__ = [
    filename[:-3]
    for filename in os.listdir(os.path.dirname(__file__))
    if filename.endswith(".py") and filename not in exlude_files
]

# Loop through the command modules and generate import statements and __all__ list
for module_name in __all__:
    import_statement = f"from .{module_name} import {module_name}"
    exec(import_statement)  # Execute the import statement to bring the module into the current namespace
