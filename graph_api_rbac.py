import os

from unstructured.ingest.connector.sharepoint import ConnectorRBAC

# Follow here for setup on a new tenant/app:
# tsmatz.wordpress.com/2016/10/07/application-permission-with-v2-endpoint-and-microsoft-graph

# For granting admin permissions to the app:
# https://login.microsoftonline.com/030rx.onmicrosoft.com/adminconsent?
# client_id={client_id}&
# state=12345&
# redirect_uri=https%3A%2F%2Flogin.microsoftonline.com%2Fcommon%2Foauth2%2Fnativeclient

tenant = "030rx.onmicrosoft.com"
client_id = os.environ["SHAREPOINT_RBAC_CLIENT_APPLICATION_ID"]
client_secret = os.environ["SHAREPOINT_RBAC_CLIENT_SECRET"]


def main():
    rbac_connector = ConnectorRBAC(tenant, client_id, client_secret)
    rbac_connector.print_all_permissions()


if __name__ == "__main__":
    main()
