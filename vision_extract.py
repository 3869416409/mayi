# -*- coding: utf-8 -*-
"""
vision_extract.py — 视觉前端（安卓版）：照片 -> 面部特征文本
复用桌面版逻辑，仅将 .env 读取改为优先从同目录 config.json 读取（便于 APP 内填 key）。

链路：照片 -> 日日新 SenseNova 多模态模型 -> 结构化特征文本
未配置 key 时返回 None（由上层降级为手动点选）。
"""
import sys
import os
import json
import re
import base64

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))

# ---- 维度与候选（单一数据源）----
DIM_ORDER = [
    "额头", "中庭", "下巴", "眉", "眼",
    "鼻头", "嘴角", "唇", "耳", "脸型", "气色",
]
DIM_OPTS = {
    "额头": ["宽阔", "饱满", "窄削"],
    "中庭": ["高挺", "直挺", "凹陷", "低平"],
    "下巴": ["方圆", "饱满", "尖削"],
    "眉": ["旋螺", "上扬", "下垂", "浓", "淡", "顺", "散"],
    "眼": ["双眼皮", "单眼皮", "细长", "有神", "游移", "大", "小"],
    "鼻头": ["圆润有肉", "尖削"],
    "嘴角": ["上扬", "下垂", "方正"],
    "唇": ["厚", "薄"],
    "耳": ["耳垂厚", "贴脑", "外张", "大", "小"],
    "脸型": ["颧骨分明", "较长", "偏圆", "方圆"],
    "气色": ["红润", "暗沉"],
}
DIM_ALIASES = {
    "中庭": ["鼻", "鼻梁", "山根"],
    "鼻头": ["鼻尖", "鼻头"],
    "眉": ["眉毛"],
    "眼": ["眼睛"],
    "嘴角": ["嘴", "口"],
    "唇": ["嘴唇"],
    "下巴": ["下庭", "下颌"],
    "脸型": ["脸", "轮廓", "脸庞"],
    "气色": ["肤色", "面色"],
    "额头": ["上庭", "天庭"],
}

_NEG = ["不", "没", "无", "非", "否", "未", "并非", "不太", "不明显"]


def _build_prompt_dims_json():
    obj = {k: DIM_OPTS[k] for k in DIM_ORDER}
    return json.dumps(obj, ensure_ascii=False)


def _read_image_b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


def _scan_dim_in_text(raw, dim, opts):
    names = [dim] + DIM_ALIASES.get(dim, [])
    best = None
    best_dist = 999
    for name in names:
        for mm in re.finditer(re.escape(name), raw):
            start = mm.end()
            seg = raw[start: start + 25]
            for opt in sorted(opts, key=len, reverse=True):
                idx = seg.find(opt)
                if idx == -1:
                    continue
                pre = seg[max(0, idx - 3):idx]
                post = seg[idx + len(opt): idx + len(opt) + 3]
                if any(neg in pre or neg in post for neg in _NEG):
                    continue
                if idx < best_dist:
                    best = opt
                    best_dist = idx
    return best


def _clean_features(raw):
    result = {}
    for dim in DIM_ORDER:
        opts = DIM_OPTS[dim]
        hit = _scan_dim_in_text(raw, dim, opts)
        if hit:
            result[dim] = hit
    for dim in DIM_ORDER:
        if dim in result:
            continue
        for opt in DIM_OPTS[dim]:
            if opt in raw and opt not in result.values():
                result[dim] = opt
                break
    return " ".join(result[d] for d in DIM_ORDER if d in result)


def _parse_json_features(raw):
    m = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", raw)
    if not m:
        m = re.search(r"\{[\s\S]*\}", raw)
    if not m:
        return None
    try:
        blob = m.group(1) if (m.group(1) and m.group(1).strip().startswith("{")) else m.group(0)
        obj = json.loads(blob)
    except Exception:
        return _clean_features(raw)
    result = {}
    for dim in DIM_ORDER:
        val = obj.get(dim)
        if isinstance(val, list) and val:
            for v in val:
                v = str(v)
                if v in DIM_OPTS[dim]:
                    result[dim] = v
                    break
            if dim not in result and val:
                result[dim] = str(val[0])
        elif isinstance(val, str) and val in DIM_OPTS[dim]:
            result[dim] = val
    for dim in DIM_ORDER:
        if dim not in result:
            hit = _scan_dim_in_text(raw, dim, DIM_OPTS[dim])
            if hit:
                result[dim] = hit
    if not result:
        return None
    return " ".join(result[d] for d in DIM_ORDER if d in result)


def _load_config():
    """优先 config.json（APP 内用户填），其次 .env，其次环境变量。"""
    cfg = {}
    cfg_path = os.path.join(HERE, "config.json")
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            cfg = {}
    env_path = os.path.join(HERE, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                cfg.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    for k in ("SENSENOVA_API_KEY", "SENSENOVA_BASE_URL", "SENSENOVA_MODEL"):
        if k not in cfg and os.environ.get(k):
            cfg[k] = os.environ[k]
    return cfg


def extract_from_photo(photo_path):
    cfg = _load_config()
    api_key = cfg.get("SENSENOVA_API_KEY", "")
    if not api_key or api_key.startswith("sk-xxxxxxxx"):
        return None  # 未配置 -> 上层降级手动

    base_url = cfg.get("SENSENOVA_BASE_URL", "https://token.sensenova.cn/v1")
    model = cfg.get("SENSENOVA_MODEL", "sensenova-6.7-flash-lite")

    if photo_path.startswith("http://") or photo_path.startswith("https://"):
        image_url = photo_path
    else:
        if not os.path.exists(photo_path):
            return None
        data_uri = "data:image/jpeg;base64," + _read_image_b64(photo_path)
        image_url = data_uri

    prompt = (
        "你是面相特征提取器。只看图，严格输出一个 JSON 对象，键为维度，值为从候选中选的1-2个词组成的数组。"
        "禁止任何解释、禁止复述、禁止判断性格、禁止输出 JSON 以外的任何文字（不要 markdown、不要代码块标记）。\n"
        "维度与候选（必须从这些词里选，不要自创）：\n"
        + _build_prompt_dims_json() + "\n"
        "只输出这个 JSON 本身，不要其他任何文字。示例：\n"
        '{"额头":["宽阔"],"中庭":["直挺"],"下巴":["方圆"],"眉":["淡","顺"],"眼":["细长","有神"],"鼻头":["圆润有肉"],"嘴角":["上扬"],"唇":["厚"],"耳":["耳垂厚"],"脸型":["偏圆"],"气色":["红润"]}'
    )

    try:
        import requests
        url = base_url.rstrip("/") + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                }
            ],
            "max_tokens": 400,
            "temperature": 0,
            "reasoning": False,
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        msg = data["choices"][0]["message"]
        raw = (
            msg.get("content")
            or msg.get("reasoning_content")
            or msg.get("reasoning")
            or ""
        ).strip()
        if not raw:
            raw = msg.get("content") or ""
        text = _parse_json_features(raw)
        if not text:
            text = _clean_features(raw)
        return text or None
    except Exception:
        return None
