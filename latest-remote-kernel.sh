#! /bin/bash

curl https://raw.githubusercontent.com/LineageOS/android_build/cm-14.1/core/version_defaults.mk | grep "PLATFORM_SECURITY_PATCH :=" | grep -oP '\d+-\d+-\d+'
