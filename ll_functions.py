﻿"""
Set of functions for load.link (https://github.com/deuiore/load.link) API
"""
import json
from os import remove
from os.path import expanduser, isfile
from requests_toolbelt import MultipartEncoder
import re
import requests
import sys
import yaml

try:
    f = open(expanduser("~/.ll_config"), 'r+')
except Exception:
    print("No config file found at: " + expanduser("~/.ll_config"))

CONFIG = yaml.load(f)
try:
    ROOT_URL = CONFIG["URL"]
except IndexError:
    print("No URL setting found in " + expanduser("~/.ll_config"))

    i = input("Do you want to set this now? [Y]")

    if i not in ('', 'Y'):
        sys.exit(1)
        return

    CONFIG["URL"] = input("What is your /api URL? ")

    f.write(yaml.dump(CONFIG))

if not re.match("^https?://.*/|\?api$", CONFIG["URL"]):
    print("Invalid URL passed")
    sys.exit(1)
    return

f.close()


def post_data(action, json_dict={}, data_tuple=None):
    """
        Generic function handling all POSTs to /api endpoint
    """
    payload = {"action": action}

    payload.update(json_dict)

    if "username" not in payload:
        payload["token"] = get_token()

    payload = {
        "headers": (
            "headers",
            bytes(
                payload,
                "utf-8"),
            "application/json")}

    if data_tuple:
        payload["data"] = data_tuple

    m = MultipartEncoder(payload)

    response = requests.post(
        ROOT_URL,
        data=m,
        headers={
            "content-type": m.content_type})

    if response.status_code >= 200:
        raise Exception(
            "Error {error_code} with {action}: {error}".format(
                error_code=response.status_code,
                action=action,
                error=response.text))

    return response


def get_token(token_path=expanduser("~/.ll_token")):
    """
        Check token_path for token it exists or retrieve token from user input
    """
    if isfile(token_path):
        with open(token_path, 'r') as f:
            token = f.readline()
            if token:
                return token

    username = input("What is your username? ")
    password = input("What is your password? ")

    response = post_data(
        "get_token", {
            "username": username, "password": password})

    token = response.json()["token"]

    with open(token_path, 'w') as f:
        f.write(token)

    return token


def get_links(limit, offset):
    """
        Get <limit> links starting from <offset>
    """
    response = post_data(
        "get_links", {"limit": limit, "offset": offset})

    return response.json()["links"]


def count():
    """
        Return count of all uploaded items
    """
    response = post_data("count")

    return response.json()["count"]


def get_thumbnail(uid):
    """
        Return thumbnail and associated details for a given uid
    """
    response = post_data("get_thumbnail", {"uid": uid})

    return response.json()["thumbnail"]


def upload(file):
    """
        Upload a file
    """
    with open(file, 'rb') as f:
        response = post_data("upload", {"filename": file}, ("data", f, ''))

    if response.status_code == 202:
        print("Failed to upload " + file)
        return
    # Might change to return whole dictionary
    return response.json()["link"]


def shorten_url(url):
    """
        Shorten a url
    """
    response = post_data("upload", {"url": url})

    return response.json()["link"]


def delete(uid):
    """
        Delete uploaded item by its uid
    """
    response = post_data("delete", {"uid": uid})

    if response.status_code != 200:
        print("Failed to remove uid: " + uid)


def edit_settings(settings_dict):
    """
        Edit load.link settings
    """
    password = input("What is your password? ")

    response = post_data(
        "edit_settings", {
            "password": password, "settings": json.dumps(settings_dict)})

    if response.status_code != 200:
        print("Failed to update settings: " + response.json()["message"])


def release_token(token_path=expanduser("~/.ll_token")):
    """
        Release token given by token_path and removes it
    """
    if not token_path or not isfile(token_path):
        print(token_path + " doesn't exist to release")
        return
    response = post_data("release_token")

    if response.status_code == 200:
        remove(token_path)
        return

    print("Failed to release token")


def release_all_tokens(token_path=expanduser("~/.ll_token")):
    """
        Release all authentication tokens and deletes given token_path
    """
    if not token_path or not isfile(token_path):
        print(token_path + " doesn't exist to release")
        return
    response = post_data("release_all_tokens")

    if response.status_code == 200:
        remove(token_path)
        return

    print("Failed to release all tokens")


def prune_unused():
    """
        Prune unused links
    """
    response = post_data("prune_unused")

    return response.json()["pruned"]