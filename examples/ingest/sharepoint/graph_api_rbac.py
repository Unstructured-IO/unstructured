import os
from pprint import PrettyPrinter

import requests

# Follow here for setup on a new tenant/app:
# tsmatz.wordpress.com/2016/10/07/application-permission-with-v2-endpoint-and-microsoft-graph

# For granting admin permissions to the app:
# https://login.microsoftonline.com/030rx.onmicrosoft.com/adminconsent?
# client_id={client_id}&
# state=12345&
# redirect_uri=https%3A%2F%2Flogin.microsoftonline.com%2Fcommon%2Foauth2%2Fnativeclient


def get_access_token(tenant: str, client_id: str, client_secret: str):
    url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    data = {
        "client_id": client_id,
        "scope": "https://graph.microsoft.com/.default",
        "client_secret": client_secret,
        "grant_type": "client_credentials",
    }

    response = requests.post(url, headers=headers, data=data)
    return response.json()["access_token"]


def validated_response(response):
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Request failed with status code {response.status_code}:")
        print(response.text)


def get_sites(tenant):
    url = "https://graph.microsoft.com/v1.0/sites"
    params = {
        "$select": "webUrl, id",
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    response = requests.get(url, params=params, headers=headers)
    return validated_response(response)


def get_drives(site):
    url = f"https://graph.microsoft.com/v1.0/sites/{site}/drives"

    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    response = requests.get(url, headers=headers)

    return validated_response(response)


def get_drive_items(site, drive_id):
    url = f"https://graph.microsoft.com/v1.0/sites/{site}/drives/{drive_id}/root/children"

    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    response = requests.get(url, headers=headers)

    return validated_response(response)


def get_permissions_for_drive_item(site, drive_id, item_id):
    url = f"https://graph.microsoft.com/v1.0/sites/{site} \
            /drives/{drive_id}/items/{item_id}/permissions"

    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    response = requests.get(url, headers=headers)

    return validated_response(response)


tenant = "030rx.onmicrosoft.com"
client_id = os.environ["SHAREPOINT_RBAC_CLIENT_APPLICATION_ID"]
client_secret = os.environ["SHAREPOINT_RBAC_CLIENT_SECRET"]

access_token = get_access_token(tenant, client_id, client_secret)


def main():
    sites = [(site["id"], site["webUrl"]) for site in get_sites(tenant)["value"]]
    drive_ids = []

    for site_id, site_url in sites:
        drives = get_drives(site_id)
        if drives:
            print(f"Working on site {site_url}")
            drives_for_site = drives["value"]
            drive_ids.extend([(site_id, drive["id"]) for drive in drives_for_site])

    item_ids = []
    for site, drive_id in drive_ids:
        drive_items = get_drive_items(site, drive_id)
        if drive_items:
            item_ids.extend(
                [(site, drive_id, item["id"], item["name"]) for item in drive_items["value"]],
            )

    p = PrettyPrinter(indent=2)
    for site, drive_id, item_id, item_name in item_ids:
        print(item_name)
        p.pprint(get_permissions_for_drive_item(site, drive_id, item_id)["value"])
        print("\n\n")


if __name__ == "__main__":
    main()
