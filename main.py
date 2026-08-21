# -*- coding: utf-8 -*-
"""
mayi-shenxiang App — 《麻衣神相》原书断语查询（Kivy / 安卓）
主模式：手动点选面部特征（离线、零依赖）
可选模式：填日日新 key 后自动拍照/选图识别
核心逻辑：lookup.lookup(text) 原书引擎，零改动。
"""
import os
import sys
import json

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserIconView
from kivy.utils import platform
from kivy.clock import Clock

# Android 存储权限
if platform == "android":
    from android.permissions import request_permissions, Permission
    from android.storage import primary_external_storage_path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import lookup
import vision_extract

# ---- 手动点选的特征维度定义（与 lookup.py 关键词对齐）----
DIM_GROUPS = [
    ("额头/上庭", ["宽阔", "饱满", "窄削"]),
    ("中庭/鼻", ["高挺", "直挺", "凹陷", "低平"]),
    ("下巴/下停", ["方圆", "饱满", "尖削"]),
    ("眉", ["浓", "淡", "顺", "上扬", "下垂", "旋螺"]),
    ("眼", ["有神", "游移", "细长", "双眼皮", "单眼皮", "大", "小"]),
    ("鼻头", ["圆润有肉", "尖削"]),
    ("嘴角", ["上扬", "下垂", "方正"]),
    ("唇", ["厚", "薄"]),
    ("耳", ["贴脑", "外张", "耳垂厚", "大", "小"]),
    ("脸型", ["偏圆", "较长", "方圆", "颧骨分明"]),
    ("气色", ["红润", "暗沉"]),
]

DISCLAIMER = "说明：依《麻衣神相》原书完整收录，非科学结论，仅供私人文化研究。"


class Chip(Button):
    """可切换选中的特征按钮"""
    def __init__(self, text, on_toggle, **kw):
        super().__init__(text=text, size_hint_y=None, height=38,
                         background_color=(0.9, 0.9, 0.9, 1), color=(0, 0, 0, 1), **kw)
        self._text = text
        self._on_toggle = on_toggle
        self.selected = False
        self.bind(on_release=self._press)

    def _press(self, *a):
        self.selected = not self.selected
        self.background_color = (0.2, 0.5, 0.9, 1) if self.selected else (0.9, 0.9, 0.9, 1)
        self.color = (1, 1, 1, 1) if self.selected else (0, 0, 0, 1)
        self._on_toggle(self._text, self.selected)


class MayiApp(App):
    def build(self):
        self.title = "麻衣神相 · 原书断语"
        self.selected = {}  # dim -> set(opt)
        self.auto_feats = ""

        root = BoxLayout(orientation="vertical", padding=8, spacing=6)

        # 标题
        root.add_widget(Label(text="《麻衣神相》原书断语", font_size=22,
                              size_hint_y=None, height=36, color=(0.8, 0.2, 0.2, 1)))

        # 模式切换 + 选图（自动模式）
        top = BoxLayout(size_hint_y=None, height=40, spacing=6)
        self.mode_btn = Button(text="模式：手动点选", on_press=self.toggle_mode)
        self.pick_btn = Button(text="选图识别", on_press=self.pick_image, disabled=True)
        top.add_widget(self.mode_btn)
        top.add_widget(self.pick_btn)
        root.add_widget(top)

        # 手动特征区（可滚动）
        self.feat_scroll = ScrollView(size_hint=(1, 0.55))
        self.feat_box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=4)
        self.feat_box.bind(minimum_height=self.feat_box.setter("height"))
        self._build_manual()
        self.feat_scroll.add_widget(self.feat_box)
        root.add_widget(self.feat_scroll)

        # 特征文本框（自动结果/手动预览可编辑）
        self.feat_input = TextInput(hint_text="特征文本（自动填充或可手动改，如：眉浓顺 眼有神 鼻头圆润有肉）",
                                    size_hint_y=None, height=48, multiline=False)
        root.add_widget(self.feat_input)

        # 查询按钮
        root.add_widget(Button(text="查原书断语", size_hint_y=None, height=46,
                               background_color=(0.8, 0.2, 0.2, 1), color=(1, 1, 1, 1),
                               on_press=self.do_lookup))

        # 结果区
        self.result_label = Label(text="", markup=True, size_hint_y=None,
                                  text_size=(None, None), halign="left", valign="top")
        self.result_label.bind(width=lambda *x: self.result_label.setter("text_size")(self.result_label, (self.result_label.width, None)))
        self.result_label.bind(texture_size=self.result_label.setter("size"))
        res_scroll = ScrollView(size_hint=(1, 0.35))
        res_scroll.add_widget(self.result_label)
        root.add_widget(res_scroll)

        # 免责声明
        root.add_widget(Label(text=DISCLAIMER, font_size=12, size_hint_y=None, height=28,
                              color=(0.5, 0.5, 0.5, 1)))

        if platform == "android":
            request_permissions([Permission.READ_EXTERNAL_STORAGE,
                                 Permission.WRITE_EXTERNAL_STORAGE])
        return root

    # ---------- 手动点选 ----------
    def _build_manual(self):
        self.chips = []
        for dim, opts in DIM_GROUPS:
            row = BoxLayout(size_hint_y=None, height=44, spacing=4)
            row.add_widget(Label(text=dim, size_hint_x=0.28, font_size=13,
                                 color=(0, 0, 0, 1)))
            chip_box = BoxLayout(size_hint_x=0.72, spacing=4)
            self.selected[dim] = set()
            for opt in opts:
                c = Chip(opt, self._toggle)
                self.chips.append(c)
                chip_box.add_widget(c)
            row.add_widget(chip_box)
            self.feat_box.add_widget(row)

    def _toggle(self, text, selected):
        # 找到所属 dim
        dim = None
        for d, opts in DIM_GROUPS:
            if text in opts:
                dim = d
                break
        if dim is None:
            return
        if selected:
            self.selected[dim].add(text)
        else:
            self.selected[dim].discard(text)
        self._sync_feat_text()

    def _sync_feat_text(self):
        parts = []
        for dim, opts in DIM_GROUPS:
            for t in self.selected[dim]:
                parts.append(t)
        if parts:
            self.feat_input.text = " ".join(parts)

    # ---------- 模式切换 ----------
    def toggle_mode(self, *a):
        if self.mode_btn.text.endswith("手动点选"):
            self.mode_btn.text = "模式：自动识别"
            self.pick_btn.disabled = False
            self.feat_scroll.disabled = True
        else:
            self.mode_btn.text = "模式：手动点选"
            self.pick_btn.disabled = True
            self.feat_scroll.disabled = False

    # ---------- 选图 ----------
    def pick_image(self, *a):
        if platform == "android":
            from plyer import filechooser
            filechooser.open_file(on_selection=self._on_image_selected,
                                  filters=[("Images", "*.jpg", "*.png")])
        else:
            self._open_desktop_picker()

    def _open_desktop_picker(self):
        fc = FileChooserIconView(filters=["*.jpg", "*.png"])
        btn = Button(text="确定", size_hint_y=None, height=40)
        box = BoxLayout(orientation="vertical")
        box.add_widget(fc)
        box.add_widget(btn)
        pop = Popup(title="选择照片", content=box, size_hint=(0.9, 0.9))
        btn.bind(on_release=lambda *x: (self._on_image_selected([fc.selection[0]]) if fc.selection else None, pop.dismiss()))
        pop.open()

    def _on_image_selected(self, selection):
        if not selection:
            return
        path = selection[0]
        self.feat_input.text = "识别中…"
        # 用 Clock 避免阻塞 UI
        Clock.schedule_once(lambda *x: self._run_vision(path), 0.1)

    def _run_vision(self, path):
        feats = vision_extract.extract_from_photo(path)
        if feats:
            self.feat_input.text = feats
            self.auto_feats = feats
        else:
            self.feat_input.text = "（自动识别未配置或失败，请手动点选/输入）"

    # ---------- 查询 ----------
    def do_lookup(self, *a):
        text = self.feat_input.text.strip()
        if not text or text in ("识别中…", "（自动识别未配置或失败，请手动点选/输入）"):
            self.result_label.text = "[color=884444]请先选择/输入面部特征。[/color]"
            return
        hits = lookup.lookup(text)
        if not hits:
            self.result_label.text = ("[color=888888]未命中原书断语。可补充维度，如："
                                      "眉浓/眉淡/眼有神/鼻丰耸直/嘴角上扬/上停饱满/山根丰满。[/color]")
            return
        lines = []
        for skill, verdict in hits:
            lines.append(f"[color=802020][b][{skill}][/b][/color]  {verdict}")
        self.result_label.text = "\n".join(lines)


if __name__ == "__main__":
    MayiApp().run()
