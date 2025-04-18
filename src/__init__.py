#!/usr/bin/python3

import os
import shutil
import hashlib
import http.client
import re
import io
import argparse
from urllib.parse import urljoin
from http.client import HTTPSConnection
from os import listdir
from os.path import isfile, join



def get(host, path):
    """
    Simple function to follow http redirects which are returned by libavatar if the user has a gravitar icon

    :param host: domain to make request to
    :param path: path to make request to
    :return: http client response

    """
    print(f'GET {path}')

    connection = HTTPSConnection(host)
    connection.request('GET', path)

    response = connection.getresponse()
    location_header = response.getheader('location')

    if location_header is None:
        return response
    else:
        location = urljoin(path, location_header)
        return get(host, location)

def download_libravatar(email: str) -> io.BytesIO:
    """
    Download an avatar from Libravatar using an email address and return it as a BytesIO object.

    :param email: Email address to fetch the avatar for.
    :return: In-memory file (BytesIO object) containing the avatar image.
    """
    # Normalize and hash the email address
    email = email.strip().lower()
    email_hash = hashlib.md5(email.encode("utf-8")).hexdigest()

    host = "seccdn.libravatar.org"
    path = f"/avatar/{email_hash}?s=512"
    url = f"https://{host}{path}"
    print(f"Downloading from URL: {url}")

    response = get(host, path)

    if response.status == 200:
        avatar_data = response.read()
        avatar_file = io.BytesIO(avatar_data)
        print("Avatar downloaded successfully.")
        return avatar_file
    else:
        print(f"Failed to download avatar. HTTP Status: {response.status}")
        raise

    conn.close()


def change_gnome_profile_icon(username: str, avatar_file: io.BytesIO):
    """
    Change the GNOME profile icon for the given user using an in-memory avatar file.

    :param username: The username whose profile icon needs to be changed.
    :param avatar_file: In-memory file (BytesIO) containing the new image data.
    """
    user_path = f"/var/lib/AccountsService/users/{username}"

    if not os.path.exists(user_path):
        with open(user_path, "wb") as f:
            string = f"""[User]
Icon=/var/lib/AccountsService/icons/{username}
"""
            f.write(string.encode())
            return

    icon_destination = f"/var/lib/AccountsService/icons/{username}"
    with open(icon_destination, "wb") as icon_file:
        avatar_file.seek(0)  # Rewind the file to the beginning
        shutil.copyfileobj(avatar_file, icon_file)

    os.chown(icon_destination, 0, 0)

    # Update the AccountsService user file to point to the new icon
    with open(user_path, "rb") as user_file:
        content = user_file.read().decode()
        if "Icon" in content:
            content_updated = re.sub(
                r"^Icon=.*", f"Icon={icon_destination}", content, flags=re.M
            )
        else:
            content_updated = content.rstrip("\n") + f"\nIcon={icon_destination}"

    with open(user_path, "wb") as user_file:
        user_file.write(content_updated.encode())
        print(content_updated)

    print(f"Profile icon updated successfully for {username}.")

if __name__ == "__main__":
    if os.geteuid() != 0:
        print("This script must be run with root privileges. Please run with 'sudo'.")
        exit(1)

    parser = argparse.ArgumentParser(
        description="Download and set a GNOME profile icon from an email address."
    )

    path = '/var/lib/AccountsService/users';
    users = [f for f in listdir(path) if isfile(join(path, f))]
    for user in users:
        with open(join(path, user)) as user_file:
            for line in user_file:
                if line.startswith("Email="):
                    email = line.split('=')[1]
                    print(f"Checking {user}:{email}")
                    avatar_file = download_libravatar(email)
                    if avatar_file:
                        change_gnome_profile_icon(user, avatar_file)


