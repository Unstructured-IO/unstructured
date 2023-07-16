import msal
from office365.graph_client import GraphClient

from office365.onedrive.driveitems.driveItem import DriveItem
from office365.outlook.mail.folders.folder import MailFolder


def acquire_token():
    """
    Acquire token via MSAL
    """
    authority_url = 'https://login.microsoftonline.com/3d60a7e5-1e32-414e-839b-1c6e6782613d'
    app = msal.ConfidentialClientApplication(
        authority=authority_url,
        client_id='1be61e22-4213-4fc1-9e95-75c93866e2a3',
        client_credential='4~98Q~6bVqDpvJdxtmWnop_kZ.J4EqjZz2G0pb2B'
    )
    token = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    return token

client = GraphClient(acquire_token)


from pprint import pprint
from collections import defaultdict
folder_dict = defaultdict(list)
root_with_child_folder=[]


mf = client.users["devops@unstructuredio.onmicrosoft.com"].mail_folders.get().execute_query()
m = client.users["devops@unstructuredio.onmicrosoft.com"].messages.get().execute_query()

for root_folder in mf:
    folder_dict[root_folder.display_name].append(root_folder.id)
    if root_folder.get_property("childFolderCount") > 0:
        root_with_child_folder.append(root_folder.id)

pprint(folder_dict)

def recurse_folders(folder_id, main_folder_dict):
    child_folders = client.users["devops@unstructuredio.onmicrosoft.com"].mail_folders[folder_id].child_folders.get().execute_query()
    for child_folder in child_folders:
        for k,v in folder_dict.items():
            if child_folder.get_property("parentFolderId") in v:
                v.append(child_folder.id)
        if child_folder.get_property("childFolderCount") > 0:
            recurse_folders(child_folder.id,main_folder_dict)

for f in root_with_child_folder:
    recurse_folders(f,folder_dict)

pprint(folder_dict)

for item in m:
    print(item.subject)
    for k,v in folder_dict.items():
        if item.parent_folder_id in v:
            print(k)
    print("*********")