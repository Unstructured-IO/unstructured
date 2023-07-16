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

# def list_objects(folder, recursive=True):
#         drive_items = folder.children.get().execute_query()
#         files = [d for d in drive_items if d.is_file]
#         if not recursive:
#             return files
#         folders = [d for d in drive_items if d.is_folder]
#         for f in folders:
#             files += list_objects(f, recursive)
#         return files

# drive = client.users["devops@unstructuredio.onmicrosoft.com"].drive.get().execute_query()
# files = list_objects(drive.root)
# print(drive)
# print(files)
from pprint import pprint
from collections import defaultdict
folder_dict = defaultdict(list)
folder_with_child_folder=[]

# mail_folders is from user.py
# m = client.users["devops@unstructuredio.onmicrosoft.com"].mail_folders.get().execute_query()
m = client.users["devops@unstructuredio.onmicrosoft.com"].messages.get().execute_query()
mf = client.users["devops@unstructuredio.onmicrosoft.com"].mail_folders.get().execute_query()
iif = client.users["devops@unstructuredio.onmicrosoft.com"].mail_folders["Inbox"].get().execute_query()
cf2 = client.users["devops@unstructuredio.onmicrosoft.com"].mail_folders["Inbox"].child_folders.get().execute_query()
cf = client.users["devops@unstructuredio.onmicrosoft.com"].mail_folders["AQMkAGE2MmEwNzFlLWVjYwAwLTQzYWUtOGRjNS0xY2JjM2Q4YjJiNDAALgAAA9zUx8lh61JDpBme1isj2TgBANlif_V_e8tKohxb9iw3x5sAAAIBDAAAAA=="].get().execute_query()
# sif = client.users["devops@unstructuredio.onmicrosoft.com"].mail_folders["Inbox/sss"].get().execute_query()

ou = client.users["devops@unstructuredio.onmicrosoft.com"].outlook.get().execute_query()
# m = client.users["devops@unstructuredio.onmicrosoft.com"].mail_folders.messages.get().execute_query()
for fold in mf:
    # print(fold.display_name)
    # print(fold.get_property("childFolderCount"))
    # print(fold.child_folders)
    # folder_dict[fold.id] = fold.display_name
    # if fold.display_name == "Inbox":
    #     breakpoint()
    # print("Folder Name")
    # print(fold.display_name)
    # print("total item count")
    # print(fold.total_item_count)
    # print("id")
    # print(fold.get_property("id"))
    # print(fold.id)
    # print("parent id")
    # print(fold.get_property("parentFolderId"))
    folder_dict[fold.display_name].append(fold.id)
    if fold.get_property("childFolderCount") > 0:
        folder_with_child_folder.append(fold.id)

pprint(folder_dict)
print("*****")
print(folder_with_child_folder)
for f in folder_with_child_folder:
    cfs = client.users["devops@unstructuredio.onmicrosoft.com"].mail_folders[f].child_folders.get().execute_query()
    # breakpoint()
    print("bob")
    for cf in cfs:
        for k,v in folder_dict.items():
            if cf.get_property("parentFolderId") in v:
                v.append(cf.id)
        breakpoint()
    

#     print(fold)
# print(m)
for item in m:
    # breakpoint()
    # print(item.subject)
    # print(item.has_attachments)
    # print(item.body.content)
    # print(item.get_property("subject"))
    # print(item.get_property("from"))
    # print(item.get_property("body").content)
    # print("item id")
    # print(item.id)
    # print("parent folder id")
    # print(item.parent_folder_id)
    print(item.subject)
    # print(item.parent_folder_id)
    for k,v in folder_dict.items():
        if item.parent_folder_id in v:
            print(k)
    # print(FOLDER_DICT.get(item.parent_folder_id,"NO FOLDER ID"))
    print("*********")