# List of command modules (module names as strings)
__all__ = [
    "azure",
    "biomed",
    "confluence",
    "discord",
    "dropbox",
    "elasticsearch",
    "fsspec",
    "gcs",
    "github",
    "gitlab",
    "google_drive",
    "local",
    "onedrive",
    "outlook",
    "reddit",
    "s3",
    "slack",
    "wikipedia",
]

# Loop through the command modules and generate import statements and __all__ list
for module_name in __all__:
    import_statement = f"from .{module_name} import {module_name}"
    exec(import_statement)  # Execute the import statement to bring the module into the current namespace
