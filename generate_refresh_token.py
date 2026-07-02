"""
One-time helper: generate a Google Ads API refresh token.

Run this ON YOUR OWN COMPUTER (it opens a browser for Google sign-in):

    pip install google-auth-oauthlib
    python generate_refresh_token.py

You'll be asked for the OAuth Client ID and Client Secret of a
"Desktop app" OAuth client created in Google Cloud Console
(APIs & Services → Credentials → Create Credentials → OAuth client ID).
Sign in with a Google account that has access to the Google Ads account,
approve the consent screen, and the refresh token is printed at the end.

Copy it into .streamlit/secrets.toml as GOOGLE_ADS_REFRESH_TOKEN.
"""
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/adwords"]


def main():
    client_id     = input("OAuth Client ID: ").strip()
    client_secret = input("OAuth Client Secret: ").strip()

    flow = InstalledAppFlow.from_client_config(
        {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
    )
    creds = flow.run_local_server(port=0, prompt="consent")

    print("\n" + "=" * 60)
    print("SUCCESS — add this to .streamlit/secrets.toml:")
    print(f'\nGOOGLE_ADS_REFRESH_TOKEN = "{creds.refresh_token}"')
    print("=" * 60)


if __name__ == "__main__":
    main()
