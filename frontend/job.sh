#!/bin/sh

env

mkdir -p "$ONEDATA_MOUNT_POINT"

ONECLIENT_AUTHORIZATION_TOKEN="$ONECLIENT_ACCESS_TOKEN" ONECLIENT_PROVIDER_HOSTNAME="$ONECLIENT_ACCESS_TOKEN" oneclient --no_check_certificate --authentication token -o rw "$ONEDATA_MOUNT_POINT" || exit 1
