[app]

# (str) Title of your application
title = 麻衣神相

# (str) Package name
package.name = mayishenxiang

# (str) Package domain (needed for android/ios packaging)
package.domain = com.private.mayi

# (str) Source code where the main file lives
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,json,txt,md

# (list) Application versioning (method 1)
version = 1.0

# (list) Application requirements
# 自动识别用 requests；plyer 用于安卓选图
# 注意：不要写具体 kivy 版本，让 buildozer 选兼容版本（写版本会去拉不存在的 wheel）
requirements = python3,kivy,requests,plyer

# (str) Supported orientation (one of landscape/portrait/portrait-reverse/landscape-reverse)
orientation = portrait

# (list) Permissions
android.permissions = INTERNET,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,CAMERA

# (int) Android API to use
android.api = 34
android.minapi = 24
android.ndk = 25b
android.accept_sdk_license = True

# (str) Presplash/icon (optional)
# presplash.filename = %(source.dir)s/presplash.png
# icon.filename = %(source.dir)s/icon.png

# (str) Entry point
main.py.filename = main.py

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

[buildozer]

# (int) Log level (0 ~ 3)
log_level = 2

# (str) Path to build artifact storage, absolute or relative to spec
build_dir = ./.buildozer

# (str) Target Android version (used by cloud build services)
android.target = apk
