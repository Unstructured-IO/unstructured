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

# Function to get the 'get_cmd'
def get_command_function(command_name):
    return getattr(__import__(f"{__name__}.{command_name}", fromlist=["get_cmd"]), "get_cmd")

for command in __all__:
    globals()[command] = get_command_function(command)