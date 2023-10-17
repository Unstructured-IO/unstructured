# Make sure this is importing the official dropbox python package,
# not unstructured/ingest/connector/dropbox
import dropbox
from dropbox import DropboxOAuth2FlowNoRedirect

"""
This example walks through a basic oauth flow using the existing long-lived token type
Populate your app key and app secret in order to run this locally
https://www.dropboxforum.com/t5/Dropbox-API-Support-Feedback/Get-refresh-token-from-access-token/m-p/596755
https://www.dropboxforum.com/t5/Dropbox-API-Support-Feedback/Oauth2-refresh-token-question-what-happens-when-the-refresh/td-p/486241
"""


def get_access_and_refresh_token():
    print("You will need your Dropbox app_key and app_secret.")

    app_key = input("Enter app key: ").strip()
    app_secret = input("Enter app secret: ").strip()

    auth_flow = DropboxOAuth2FlowNoRedirect(
        app_key,
        app_secret,
        token_access_type="offline",
    )

    authorize_url = auth_flow.start()
    print("****************************************************")
    print("1. Go to: " + authorize_url)
    print('2. Click "Allow" (you might have to log in first).')
    print("3. Copy the authorization code.")
    auth_code = input("Enter the authorization code here: ").strip()

    try:
        oauth_result = auth_flow.finish(auth_code)
    except Exception as e:
        print("Error: %s" % (e,))
        exit(1)

    with dropbox.Dropbox(oauth2_access_token=oauth_result.access_token) as dbx:
        dbx.users_get_current_account()
        print("Successfully set up client!")
        print(f"Here is your access_token: {oauth_result.access_token}")
        print(f"Here is your refresh_token: {oauth_result.refresh_token}")


def refresh_token():
    print("You will need your app_key, app_secret and refresh token.")

    app_key = input("Enter app_key: ").strip()
    app_secret = input("Enter app_secret: ").strip()
    refresh_token = input("Enter refresh token: ").strip()
    print("****************************************************")

    refresh_flow = dropbox.Dropbox(
        app_key=app_key,
        app_secret=app_secret,
        oauth2_refresh_token=refresh_token,
    )
    print("Refreshing access token")
    refresh_flow.refresh_access_token()
    print("Here is your new access_token:")
    print(refresh_flow._oauth2_access_token)


has_refresh = input("Do you have an access and refresh token? (Y/n) ").strip().lower()
if has_refresh == "y":
    refresh_token()
elif has_refresh == "n":
    get_access_and_refresh_token()
else:
    print("Sorry. Bad input.")
