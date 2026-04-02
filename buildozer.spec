[app]
title = AOF Derslerim
package.name = aofderslerim
package.domain = org.aof
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.0
requirements = python3,kivy,pyjnius,android,pymupdf
orientation = portrait
fullscreen = 0
android.permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,MANAGE_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
android.ndk = 25b
android.arch = arm64-v8a
android.request_legacy_external_storage = True
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
