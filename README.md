# 麻衣神相 App（安卓）

基于 `mayi-shenxiang-skill` 原书断语引擎的安卓 APP。拍照/点选面部特征 → 输出《麻衣神相》原书断语。

## 功能
- **手动点选**（默认，离线零依赖）：按维度点选眉/眼/鼻/唇/耳/脸型等特征，拼接成特征文本查原书。
- **自动识别**（可选）：在 `config.json` 填入日日新 API key 后，选图自动提取特征。
- 核心 `lookup.py` 为原书引擎，**逻辑零改动**。

## 本地调试（Windows 需 Python 3.11，本机 3.15 装不了 Kivy）
```bash
pip install kivy requests plyer
python main.py
```

## 云端打包（无需本机 Linux）
代码已含 `buildozer.spec`。两种方式：

### 方式 A：GitHub Actions（推荐，免费）
1. 把本 `android/` 目录推到 GitHub 仓库（含 `main.py` / `lookup.py` / `vision_extract.py` / `buildozer.spec`）。
2. 仓库里加 `.github/workflows/build.yml`：
```yaml
name: Build APK
on: [push]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install buildozer cython
      - run: sudo apt-get update && sudo apt-get install -y git zip unzip openjdk-17-jdk
      - run: buildozer android debug
      - uses: actions/upload-artifact@v4
        with: { name: apk, path: "bin/*.apk" }
```
3. Actions 跑完下载 `apk` 产物安装即可。

### 方式 B：在线打包服务
- [buildozer.io](https://buildozer.io) 或 Kivy 官方 Discord 的云端构建机器人，上传本目录即可。

## 配置自动识别（可选）
在 APP 同目录放 `config.json`：
```json
{
  "SENSENOVA_API_KEY": "sk-xxx",
  "SENSENOVA_BASE_URL": "https://token.sensenova.cn/v1",
  "SENSENOVA_MODEL": "sensenova-6.7-flash-lite"
}
```
> 注意：key 存在手机本地，仅私人使用建议；公开分发请勿内置 key。

## 免责声明
依《麻衣神相》原书完整收录，非科学结论，仅供私人文化研究。
