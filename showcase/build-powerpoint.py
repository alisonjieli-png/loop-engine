#!/usr/bin/env python3
"""Build the Loop Engine showcase as native editable Impress shapes.

This intentionally uses LibreOffice UNO instead of python-pptx. The source of
truth remains showcase-data.js; tools/export-slide-data.mjs exports that object
to temporary JSON for this builder.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Iterable

uno: Any = None


SLIDE_W = 33867
SLIDE_H = 19050
INCH = 2540
FONT = "Liberation Sans"
TITLE_FONT = "Liberation Sans Narrow"


def ins(value: float) -> int:
    return int(round(value * INCH))


def color(value: str | int) -> int:
    if isinstance(value, int):
        return value
    return int(value.removeprefix("#"), 16)


def point(x: int, y: int) -> Any:
    value = uno.createUnoStruct("com.sun.star.awt.Point")
    value.X, value.Y = int(x), int(y)
    return value


def size(w: int, h: int) -> Any:
    value = uno.createUnoStruct("com.sun.star.awt.Size")
    value.Width, value.Height = int(w), int(h)
    return value


def prop(name: str, value: Any) -> Any:
    item = uno.createUnoStruct("com.sun.star.beans.PropertyValue")
    item.Name, item.Value = name, value
    return item


def enum(type_name: str, member: str) -> Any:
    return uno.Enum(type_name, member)


def set_if(obj: Any, name: str, value: Any) -> bool:
    try:
        setattr(obj, name, value)
        return True
    except Exception:
        return False


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class UnoOffice:
    def __init__(self) -> None:
        self.profile_dir = Path(tempfile.mkdtemp(prefix="loop-engine-pptx-lo-"))
        self.port = free_port()
        self.process: subprocess.Popen[str] | None = None
        self.context: Any = None

    def __enter__(self) -> "UnoOffice":
        profile_url = self.profile_dir.resolve().as_uri()
        soffice = os.environ.get("LO_SOFFICE", "/usr/bin/soffice")
        command = [
            soffice,
            "--headless",
            "--nologo",
            "--nodefault",
            "--nofirststartwizard",
            f"-env:UserInstallation={profile_url}",
            f"--accept=socket,host=127.0.0.1,port={self.port};urp;StarOffice.ComponentContext",
        ]
        self.process = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        # Importing pyuno before starting a locally extracted soffice process
        # causes that process to fail during UNO deployment. Start the isolated
        # office first, then load pyuno in this controller process.
        global uno
        import importlib

        uno = importlib.import_module("uno")
        local = uno.getComponentContext()
        resolver = local.ServiceManager.createInstanceWithContext(
            "com.sun.star.bridge.UnoUrlResolver", local
        )
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                stderr = self.process.stderr.read() if self.process.stderr else ""
                raise RuntimeError(f"LibreOffice exited before UNO connected: {stderr}")
            try:
                self.context = resolver.resolve(
                    f"uno:socket,host=127.0.0.1,port={self.port};urp;StarOffice.ComponentContext"
                )
                return self
            except Exception:
                time.sleep(0.2)
        raise TimeoutError("LibreOffice UNO did not become ready within 20 seconds")

    def desktop(self) -> Any:
        service_manager = self.context.ServiceManager
        return service_manager.createInstanceWithContext(
            "com.sun.star.frame.Desktop", self.context
        )

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        shutil.rmtree(self.profile_dir, ignore_errors=True)


class DeckBuilder:
    def __init__(self, doc: Any, data: dict[str, Any]) -> None:
        self.doc = doc
        self.data = data
        self.palette = data["palette"]
        self.roles = data["roles"]
        self.modes = data["modes"]
        self.notes_added = 0

    def new_slide(self, index: int) -> Any:
        pages = self.doc.getDrawPages()
        slide = pages.getByIndex(0) if index == 0 else pages.insertNewByIndex(index)
        set_if(slide, "Width", SLIDE_W)
        set_if(slide, "Height", SLIDE_H)
        set_if(slide, "Layout", 0)
        return slide

    def shape(self, slide: Any, service: str, x: float, y: float, w: float, h: float) -> Any:
        obj = self.doc.createInstance(service)
        obj.Position = point(ins(x), ins(y))
        obj.Size = size(ins(w), ins(h))
        slide.add(obj)
        return obj

    def rect(
        self,
        slide: Any,
        x: float,
        y: float,
        w: float,
        h: float,
        *,
        fill: str = "paper",
        line: str = "line",
        line_width: int = 40,
        radius: float = 0.08,
    ) -> Any:
        obj = self.shape(slide, "com.sun.star.drawing.RectangleShape", x, y, w, h)
        set_if(obj, "FillStyle", enum("com.sun.star.drawing.FillStyle", "SOLID"))
        set_if(obj, "FillColor", color(self.palette.get(fill, fill)))
        if line == "none":
            set_if(obj, "LineStyle", enum("com.sun.star.drawing.LineStyle", "NONE"))
        else:
            set_if(obj, "LineStyle", enum("com.sun.star.drawing.LineStyle", "SOLID"))
            set_if(obj, "LineColor", color(self.palette.get(line, line)))
            set_if(obj, "LineWidth", line_width)
        set_if(obj, "CornerRadius", ins(radius))
        return obj

    def ellipse(
        self,
        slide: Any,
        x: float,
        y: float,
        w: float,
        h: float,
        *,
        fill: str,
        line: str,
        line_width: int = 55,
        dashed: bool = False,
    ) -> Any:
        obj = self.shape(slide, "com.sun.star.drawing.EllipseShape", x, y, w, h)
        set_if(obj, "FillStyle", enum("com.sun.star.drawing.FillStyle", "SOLID"))
        set_if(obj, "FillColor", color(self.palette.get(fill, fill)))
        set_if(
            obj,
            "LineStyle",
            enum("com.sun.star.drawing.LineStyle", "DASH" if dashed else "SOLID"),
        )
        set_if(obj, "LineColor", color(self.palette.get(line, line)))
        set_if(obj, "LineWidth", line_width)
        return obj

    def text(
        self,
        slide: Any,
        text: str,
        x: float,
        y: float,
        w: float,
        h: float,
        *,
        font_size: float = 18,
        font_color: str = "ink",
        bold: bool = False,
        align: str = "LEFT",
        valign: str = "CENTER",
        margin: float = 0.04,
        font_name: str = FONT,
        scale_width: int = 100,
        wrap: bool = True,
    ) -> Any:
        obj = self.shape(slide, "com.sun.star.drawing.TextShape", x, y, w, h)
        obj.String = text
        set_if(obj, "FillStyle", enum("com.sun.star.drawing.FillStyle", "NONE"))
        set_if(obj, "LineStyle", enum("com.sun.star.drawing.LineStyle", "NONE"))
        set_if(obj, "TextLeftDistance", ins(margin))
        set_if(obj, "TextRightDistance", ins(margin))
        set_if(obj, "TextUpperDistance", ins(0.02))
        set_if(obj, "TextLowerDistance", ins(0.02))
        set_if(obj, "TextWordWrap", wrap)
        set_if(obj, "TextAutoGrowHeight", False)
        set_if(obj, "TextHorizontalAdjust", enum("com.sun.star.drawing.TextHorizontalAdjust", align))
        set_if(obj, "TextVerticalAdjust", enum("com.sun.star.drawing.TextVerticalAdjust", valign))
        cursor = obj.createTextCursor()
        cursor.gotoEnd(True)
        set_if(cursor, "CharFontName", font_name)
        set_if(cursor, "CharHeight", float(font_size))
        set_if(cursor, "CharScaleWidth", int(scale_width))
        set_if(cursor, "CharColor", color(self.palette.get(font_color, font_color)))
        set_if(cursor, "CharWeight", 150.0 if bold else 100.0)
        set_if(cursor, "ParaAdjust", enum("com.sun.star.style.ParagraphAdjust", align))
        return obj

    def label_box(
        self,
        slide: Any,
        text: str,
        x: float,
        y: float,
        w: float,
        h: float,
        *,
        fill: str,
        line: str,
        font_color: str = "ink",
        font_size: float = 17,
        bold: bool = True,
        align: str = "CENTER",
    ) -> Any:
        self.rect(slide, x, y, w, h, fill=fill, line=line, line_width=36)
        return self.text(
            slide,
            text,
            x + 0.05,
            y + 0.03,
            w - 0.10,
            h - 0.06,
            font_size=font_size,
            font_color=font_color,
            bold=bold,
            align=align,
        )

    def line(
        self,
        slide: Any,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        *,
        line: str = "static",
        width: int = 45,
        arrow: bool = True,
        dashed: bool = False,
    ) -> Any:
        obj = self.shape(
            slide,
            "com.sun.star.drawing.LineShape",
            min(x1, x2),
            min(y1, y2),
            abs(x2 - x1) or 0.001,
            abs(y2 - y1) or 0.001,
        )
        obj.Position = point(ins(x1), ins(y1))
        obj.Size = size(ins(x2 - x1), ins(y2 - y1))
        set_if(
            obj,
            "LineStyle",
            enum("com.sun.star.drawing.LineStyle", "DASH" if dashed else "SOLID"),
        )
        set_if(obj, "LineColor", color(self.palette.get(line, line)))
        set_if(obj, "LineWidth", width)
        if arrow:
            set_if(obj, "LineEndName", "Arrow")
            set_if(obj, "LineEndWidth", ins(0.12))
        return obj

    def role_colors(self, role: str) -> tuple[str, str]:
        details = self.roles.get(role, self.roles["static"])
        return str(details["color"]), str(details["soft"])

    def loop_node(
        self,
        slide: Any,
        label: str,
        x: float,
        y: float,
        w: float,
        h: float,
        *,
        role: str = "practitioner",
        mode: str = "deterministic",
        font_size: float = 17,
    ) -> None:
        line_key, fill_key = self.role_colors(role)
        dashed = mode in {"nonDeterministic", "non-deterministic", "llm"}
        if mode == "hybrid":
            self.ellipse(slide, x, y, w, h, fill="background", line=line_key, line_width=65)
            self.ellipse(
                slide,
                x + 0.09,
                y + 0.09,
                w - 0.18,
                h - 0.18,
                fill=fill_key,
                line=line_key,
                line_width=38,
            )
        else:
            self.ellipse(
                slide,
                x,
                y,
                w,
                h,
                fill=fill_key,
                line=line_key,
                line_width=60,
                dashed=dashed,
            )
        self.text(
            slide,
            label,
            x + 0.12,
            y + 0.12,
            w - 0.24,
            h - 0.24,
            font_size=font_size,
            bold=True,
            align="CENTER",
        )

    def base(self, slide: Any, scene: dict[str, Any], index: int, total: int) -> None:
        self.rect(slide, 0, 0, 13.334, 7.5, fill="background", line="none", radius=0)
        self.rect(slide, 0, 0, 13.334, 0.08, fill="practitioner", line="none", radius=0)
        self.text(slide, scene.get("kicker", "LOOP ENGINE").upper(), 0.68, 0.23, 8.8, 0.25, font_size=11, font_color="practitioner", bold=True)
        self.text(slide, f"{index + 1:02d} / {total:02d}", 11.70, 0.22, 0.95, 0.25, font_size=11, font_color="muted", bold=True, align="RIGHT")
        self.text(
            slide,
            scene["title"],
            0.68,
            0.50,
            11.20,
            0.52,
            font_size=36,
            bold=True,
            font_name=TITLE_FONT,
            scale_width=82,
            wrap=False,
        )
        self.text(slide, scene.get("subtitle", ""), 0.68, 1.03, 12.0, 0.55, font_size=18, font_color="muted")
        self.rect(slide, 0.68, 6.66, 11.97, 0.43, fill="staticSoft", line="none")
        self.text(slide, scene.get("annotation", ""), 0.80, 6.70, 11.72, 0.34, font_size=13, font_color="muted")
        self.text(slide, scene.get("caption", ""), 0.68, 7.14, 10.85, 0.22, font_size=10.5, font_color="muted")
        self.text(slide, "LOOP ENGINE", 11.55, 7.14, 1.10, 0.22, font_size=10.5, font_color="static", bold=True, align="RIGHT")

    def title_slide(self, slide: Any, scene: dict[str, Any]) -> None:
        self.rect(slide, 0, 0, 13.334, 7.5, fill="background", line="none", radius=0)
        self.rect(slide, 0, 0, 0.16, 7.5, fill="practitioner", line="none", radius=0)
        self.text(slide, scene.get("kicker", "").upper(), 0.88, 0.72, 7.0, 0.32, font_size=14, font_color="practitioner", bold=True)
        self.text(slide, scene["title"], 0.88, 1.30, 9.2, 0.90, font_size=64, bold=True)
        self.text(slide, scene.get("subtitle", ""), 0.92, 2.27, 8.8, 0.52, font_size=28, font_color="muted")
        self.text(slide, scene["visual"]["statement"], 0.92, 3.33, 7.8, 0.55, font_size=24, bold=True)
        marks = scene["visual"].get("marks", [])
        roles = ["practitioner", "intelligence", "solution"]
        for index, label in enumerate(marks):
            x = 1.02 + index * 2.55
            self.loop_node(slide, label, x, 4.42, 1.72, 1.18, role=roles[index], font_size=16)
            if index < len(marks) - 1:
                self.line(slide, x + 1.72, 5.01, x + 2.55, 5.01, line="line")
        self.text(slide, scene.get("annotation", ""), 0.92, 6.45, 10.9, 0.36, font_size=14, font_color="muted")
        self.text(slide, scene.get("caption", ""), 0.92, 7.06, 11.45, 0.24, font_size=11, font_color="muted")

    def overview(self, slide: Any, scene: dict[str, Any]) -> None:
        v = scene["visual"]
        self.line(slide, 3.50, 3.20, 6.70, 3.20, line="static")
        self.loop_node(slide, v["flow"][0]["label"], 1.15, 2.45, 2.35, 1.50, role="practitioner", font_size=19)
        self.loop_node(slide, v["flow"][1]["label"], 6.72, 2.45, 2.35, 1.50, role="solution", font_size=19)
        self.text(slide, v["flow"][0]["detail"], 1.05, 4.02, 2.55, 0.36, font_size=16, font_color="muted", align="CENTER")
        self.text(slide, v["flow"][1]["detail"], 6.62, 4.02, 2.55, 0.36, font_size=16, font_color="muted", align="CENTER")
        self.label_box(slide, v["intelligence"]["label"], 1.08, 1.77, 7.98, 0.53, fill="intelligenceSoft", line="intelligence", font_color="intelligence", font_size=19)
        self.text(slide, "   •   ".join(v["intelligence"]["items"]), 1.17, 2.15, 7.82, 0.30, font_size=14, font_color="muted", align="CENTER")
        self.rect(slide, 9.60, 1.90, 2.45, 3.62, fill="staticSoft", line="static", line_width=50)
        self.text(slide, v["staticArchitecture"]["label"], 9.82, 2.20, 2.02, 0.56, font_size=21, font_color="static", bold=True, align="CENTER")
        self.text(slide, "\n".join(f"• {item}" for item in v["staticArchitecture"]["items"]), 9.88, 3.00, 1.90, 2.05, font_size=16, align="CENTER")

    def loop_object(self, slide: Any, scene: dict[str, Any]) -> None:
        v = scene["visual"]
        self.line(slide, 1.62, 3.67, 4.20, 3.67, line="practitioner")
        self.line(slide, 7.15, 3.67, 9.70, 3.67, line="practitioner")
        self.label_box(slide, v["input"], 0.95, 3.25, 1.80, 0.85, fill="staticSoft", line="static", font_size=17)
        self.loop_node(slide, v["loopLabel"], 4.18, 2.60, 2.98, 2.12, role="practitioner", font_size=25)
        self.label_box(slide, v["output"], 9.68, 3.25, 1.80, 0.85, fill="staticSoft", line="static", font_size=17)
        fields = v["fields"]
        for i, item in enumerate(fields):
            col = i % 4
            row = i // 4
            x = 0.88 + col * 2.91
            y = 1.75 if row == 0 else 5.05
            self.label_box(slide, item, x, y, 2.58, 0.58, fill="paper", line="line", font_size=16, bold=False)

    def typed_flow(self, slide: Any, scene: dict[str, Any]) -> None:
        v = scene["visual"]
        self.line(slide, 3.45, 3.32, 5.13, 3.32, line="solution")
        self.line(slide, 7.48, 3.32, 9.17, 3.32, line="solution")
        for x, value in [(0.88, v["input"]), (9.18, v["output"])]:
            self.rect(slide, x, 2.45, 2.55, 1.74, fill="paper", line="static", line_width=45)
            self.text(slide, value["label"], x + 0.15, 2.62, 2.25, 0.38, font_size=20, bold=True, align="CENTER")
            self.text(slide, value["type"], x + 0.15, 3.10, 2.25, 0.30, font_size=16, font_color="practitioner", bold=True, align="CENTER")
            self.text(slide, value["example"], x + 0.15, 3.51, 2.25, 0.30, font_size=16, font_color="muted", align="CENTER")
        loop = v["loop"]
        self.loop_node(slide, loop["label"], 5.10, 2.20, 2.40, 2.22, role=loop["role"], mode=loop["mode"], font_size=20)
        self.text(slide, loop["profile"], 5.10, 4.45, 2.40, 0.28, font_size=14, font_color="solution", bold=True, align="CENTER")
        self.label_box(slide, v["check"], 3.65, 5.18, 5.25, 0.62, fill="solutionSoft", line="solution", font_color="solution", font_size=18)

    def two_column(self, slide: Any, scene: dict[str, Any]) -> None:
        columns = scene["visual"]["columns"]
        for i, column in enumerate(columns):
            x = 0.85 + i * 6.08
            role = column.get("role", "static")
            line_key, fill_key = self.role_colors(role)
            self.rect(slide, x, 1.82, 5.62, 4.38, fill=fill_key, line=line_key, line_width=48)
            self.text(slide, column["label"], x + 0.28, 2.10, 5.05, 0.45, font_size=26, font_color=line_key, bold=True)
            for j, item in enumerate(column["items"]):
                self.text(slide, f"{j + 1:02d}", x + 0.32, 2.88 + j * 0.70, 0.46, 0.34, font_size=16, font_color=line_key, bold=True)
                self.text(slide, item, x + 0.84, 2.80 + j * 0.70, 4.32, 0.51, font_size=17)

    def mode_slide(self, slide: Any, scene: dict[str, Any]) -> None:
        v = scene["visual"]
        mode = v["mode"]
        self.loop_node(slide, v["loopLabel"], 0.95, 2.34, 2.55, 2.06, role="practitioner", mode=mode, font_size=20)
        steps = v["steps"]
        for i in range(len(steps) - 1):
            self.line(slide, 4.15 + i * 2.62, 3.38, 4.72 + i * 2.62, 3.38, line="static")
        for i, step in enumerate(steps):
            x = 4.75 + i * 2.62
            self.label_box(slide, step, x, 2.85, 2.05, 1.02, fill="paper", line="line", font_size=17, bold=False)
            self.text(slide, str(i + 1), x + 0.74, 2.58, 0.57, 0.28, font_size=14, font_color="practitioner", bold=True, align="CENTER")
        self.label_box(slide, v["control"], 1.62, 5.15, 10.10, 0.64, fill="staticSoft", line="static", font_color="static", font_size=17, bold=False)

    def comparison(self, slide: Any, scene: dict[str, Any]) -> None:
        v = scene["visual"]
        headers = v["headers"]
        rows = v["rows"]
        x0, y0 = 0.78, 1.78
        widths = [2.15, 3.16, 3.16, 3.16]
        row_h = 0.82
        x = x0
        for i, header in enumerate(headers):
            fill = ["staticSoft", "paper", "paper", "paper"][i]
            line = ["static", "practitioner", "practitioner", "practitioner"][i]
            self.label_box(slide, header, x, y0, widths[i], 0.72, fill=fill, line=line, font_size=17)
            x += widths[i]
        for r, row in enumerate(rows):
            x = x0
            for c, value in enumerate(row):
                fill = "staticSoft" if c == 0 else "paper"
                line = "line"
                self.rect(slide, x, y0 + 0.72 + r * row_h, widths[c], row_h, fill=fill, line=line, line_width=25, radius=0)
                self.text(slide, value, x + 0.10, y0 + 0.78 + r * row_h, widths[c] - 0.20, row_h - 0.12, font_size=16, bold=c == 0, align="CENTER")
                x += widths[c]

    def hierarchy(self, slide: Any, scene: dict[str, Any]) -> None:
        v = scene["visual"]
        centers = [2.55, 6.67, 10.77]
        for cx in centers:
            self.line(slide, 6.67, 2.72, cx, 3.35, line="static")
        self.loop_node(slide, v["trunk"], 5.60, 1.72, 2.14, 1.10, role="static", font_size=24)
        for index, branch in enumerate(v["branches"]):
            cx = centers[index]
            self.loop_node(slide, branch["label"], cx - 1.15, 3.10, 2.30, 1.20, role=branch["role"], font_size=19)
            self.text(slide, "\n".join(f"• {item}" for item in branch["items"]), cx - 1.48, 4.50, 2.96, 1.45, font_size=16, font_color="muted", valign="TOP")

    def steps(self, slide: Any, scene: dict[str, Any]) -> None:
        v = scene["visual"]
        xs = [0.86, 3.20, 5.54, 7.88, 10.22]
        for i in range(4):
            self.line(slide, xs[i] + 1.58, 3.17, xs[i + 1], 3.17, line="practitioner")
        for i, step in enumerate(v["steps"]):
            self.loop_node(slide, step, xs[i], 2.45, 1.58, 1.42, role="practitioner", font_size=17)
        self.line(slide, 11.00, 4.15, 1.65, 4.95, line="practitioner", arrow=True, dashed=True)
        self.text(slide, v["repeatLabel"], 4.25, 4.64, 4.95, 0.34, font_size=16, font_color="practitioner", bold=True, align="CENTER")
        self.label_box(slide, v["exitLabel"], 5.04, 5.32, 3.20, 0.58, fill="solutionSoft", line="solution", font_color="solution", font_size=18)

    def spawn(self, slide: Any, scene: dict[str, Any]) -> None:
        v = scene["visual"]
        ys = [1.98, 3.45, 4.92]
        for y in ys:
            self.line(slide, 4.20, 3.62, 7.45, y + 0.56, line="practitioner")
        self.loop_node(slide, v["starting"]["label"], 1.15, 2.58, 3.06, 2.05, role="practitioner", mode=v["starting"]["mode"], font_size=21)
        for index, spawned_loop in enumerate(v["spawned"]):
            y = ys[index]
            self.loop_node(slide, spawned_loop["label"], 7.45, y, 2.80, 1.12, role=spawned_loop["role"], mode=spawned_loop["mode"], font_size=17)
            self.text(slide, spawned_loop["relation"], 5.20, y + 0.27, 1.78, 0.28, font_size=16, font_color="muted", bold=True, align="CENTER")
        self.line(slide, 9.75, 6.08, 3.52, 5.43, line="solution", arrow=True, dashed=True)
        self.text(slide, v["returnLabel"], 5.45, 5.73, 3.20, 0.32, font_size=16, font_color="solution", bold=True, align="CENTER")

    def access(self, slide: Any, scene: dict[str, Any]) -> None:
        v = scene["visual"]
        ys = [1.94, 3.42, 4.90]
        for y in ys:
            self.line(slide, 3.55, y + 0.50, 6.40, 3.75, line="static")
        for i, item in enumerate(v["loops"]):
            self.loop_node(slide, item["label"], 1.00, ys[i], 2.56, 1.00, role=item["role"], font_size=18)
        context = v["context"]
        self.rect(slide, 6.40, 1.83, 5.34, 4.22, fill="staticSoft", line="static", line_width=55)
        self.text(slide, context["label"], 6.72, 2.10, 4.72, 0.54, font_size=26, font_color="static", bold=True, align="CENTER")
        for i, item in enumerate(context["items"]):
            col = i % 2
            row = i // 2
            self.label_box(slide, item, 6.82 + col * 2.25, 2.92 + row * 0.70, 2.02, 0.52, fill="paper", line="line", font_size=16, bold=False)

    def pillars(self, slide: Any, scene: dict[str, Any]) -> None:
        pillars = scene["visual"]["pillars"]
        for i, item in enumerate(pillars):
            x = 0.78 + i * 3.10
            self.rect(slide, x, 1.88, 2.77, 4.15, fill="intelligenceSoft", line="intelligence", line_width=48)
            self.text(slide, f"0{i + 1}", x + 0.22, 2.14, 0.42, 0.34, font_size=16, font_color="intelligence", bold=True)
            self.text(slide, item["label"], x + 0.24, 2.66, 2.29, 1.10, font_size=22, font_color="intelligence", bold=True, align="CENTER")
            self.text(slide, item["detail"], x + 0.26, 4.15, 2.25, 1.02, font_size=17, align="CENTER")
            self.text(slide, "Intelligence Loop", x + 0.28, 5.58, 2.20, 0.28, font_size=16, font_color="intelligence", bold=True, align="CENTER")

    def intelligence_branch(self, slide: Any, scene: dict[str, Any]) -> None:
        v = scene["visual"]
        operations = v["operations"]
        op_width = 1.40 if len(operations) <= 3 else 1.15
        available = 5.75
        gap = (available - len(operations) * op_width) / max(1, len(operations) - 1)
        op_xs = [3.75 + i * (op_width + gap) for i in range(len(operations))]
        self.line(slide, 3.33, 3.18, op_xs[0], 3.18, line="intelligence")
        for i in range(len(op_xs) - 1):
            self.line(slide, op_xs[i] + op_width, 3.18, op_xs[i + 1], 3.18, line="intelligence")
        self.loop_node(slide, v["branch"], 0.82, 2.35, 2.55, 1.72, role="intelligence", font_size=19)
        for x, operation in zip(op_xs, operations):
            self.label_box(slide, operation, x, 2.75, op_width, 0.86, fill="intelligenceSoft", line="intelligence", font_size=16)
        self.rect(slide, 9.86, 1.86, 2.36, 4.26, fill="paper", line="line", line_width=35)
        self.text(slide, "Selected details", 10.05, 2.10, 1.98, 0.36, font_size=18, font_color="intelligence", bold=True, align="CENTER")
        self.text(slide, "\n".join(f"• {item}" for item in v["items"]), 10.04, 2.68, 1.98, 3.02, font_size=16, valign="TOP")

    def matrix(self, slide: Any, scene: dict[str, Any]) -> None:
        v = scene["visual"]
        columns = v["columns"]
        rows = v["rows"]
        x0, y0 = 1.42, 1.85
        label_w, cell_w, header_h, row_h = 1.20, 2.08, 0.60, 1.04
        for i, header in enumerate(columns):
            self.label_box(slide, header, x0 + label_w + i * cell_w, y0, cell_w, header_h, fill="solutionSoft", line="solution", font_color="solution", font_size=16)
        for r, row in enumerate(rows):
            y = y0 + header_h + r * row_h
            self.label_box(slide, row["label"], x0, y, label_w, row_h, fill="staticSoft", line="static", font_size=16)
            for c, value in enumerate(row["cells"]):
                fill = "solutionSoft" if r == 1 else "paper"
                self.label_box(slide, value, x0 + label_w + c * cell_w, y, cell_w, row_h, fill=fill, line="line", font_size=16, bold=False)
        self.text(slide, "   •   ".join(v.get("status", [])), 3.86, 5.74, 5.55, 0.32, font_size=16, font_color="solution", bold=True, align="CENTER")

    def dag(self, slide: Any, scene: dict[str, Any]) -> None:
        v = scene["visual"]
        vertices = {item["id"]: item for item in v["vertices"]}

        def xy(item: dict[str, Any]) -> tuple[float, float]:
            return 0.82 + (item["x"] / 1920) * 11.15, 1.65 + (item["y"] / 1080) * 4.25

        for edge in v["edges"]:
            start, end = vertices[edge["from"]], vertices[edge["to"]]
            x1, y1 = xy(start)
            x2, y2 = xy(end)
            self.line(slide, x1 + 1.12, y1 + 0.48, x2, y2 + 0.48, line="static")
            label_w = max(0.86, min(1.75, 0.11 * len(edge["label"])))
            self.label_box(
                slide,
                edge["label"],
                (x1 + x2) / 2 - label_w / 2,
                (y1 + y2) / 2 - 0.22,
                label_w,
                0.30,
                fill="background",
                line="none",
                font_size=16,
            )
        for item in v["vertices"]:
            x, y = xy(item)
            self.loop_node(slide, item["label"], x, y, 2.18, 0.96, role=item["role"], font_size=16)

    def services(self, slide: Any, scene: dict[str, Any]) -> None:
        v = scene["visual"]
        cx, cy = 6.62, 2.80
        positions = [(0.82, 4.78), (4.67, 4.78), (8.52, 4.78)]
        for x, y in positions:
            self.line(slide, cx, cy + 0.75, x + 1.50, y, line="static", arrow=False)
        self.loop_node(slide, v["center"]["label"], 5.13, 2.05, 2.98, 1.50, role="practitioner", font_size=20)
        for (x, y), label in zip(positions, v["groups"]):
            self.label_box(slide, label, x, y, 3.00, 0.92, fill="staticSoft", line="static", font_color="static", font_size=17)

    def workflow(self, slide: Any, scene: dict[str, Any]) -> None:
        steps = scene["visual"]["steps"]
        coords = [(0.75 + i * 3.02, 2.10) for i in range(4)] + [(9.81 - i * 3.02, 4.55) for i in range(4)]
        for i in range(len(coords) - 1):
            x1, y1 = coords[i]
            x2, y2 = coords[i + 1]
            self.line(slide, x1 + 2.20, y1 + 0.48, x2, y2 + 0.48, line="static")
        for i, (item, (x, y)) in enumerate(zip(steps, coords)):
            line_key, fill_key = self.role_colors(item["role"])
            self.rect(slide, x, y, 2.20, 0.98, fill=fill_key, line=line_key, line_width=40)
            self.text(slide, f"{i + 1:02d}", x + 0.10, y + 0.10, 0.35, 0.24, font_size=13, font_color=line_key, bold=True)
            self.text(slide, item["label"], x + 0.30, y + 0.22, 1.62, 0.52, font_size=16, bold=True, align="CENTER")

    def worked_stage(self, slide: Any, scene: dict[str, Any]) -> None:
        v = scene["visual"]
        xs = [0.72, 3.74, 6.76, 9.78]
        for i in range(3):
            self.line(slide, xs[i] + 2.10, 2.78, xs[i + 1], 2.78, line="static")
        for x, item in zip(xs, v["loops"]):
            self.loop_node(slide, item["label"], x, 2.18, 2.10, 1.22, role=item["role"], mode=item["mode"], font_size=16)
        self.label_box(slide, v["questionsLabel"], 0.86, 4.12, 3.15, 0.54, fill="intelligenceSoft", line="intelligence", font_color="intelligence", font_size=17)
        for i, question in enumerate(v["questions"]):
            self.text(slide, f"{i + 1:02d}", 4.35, 4.07 + i * 0.59, 0.40, 0.28, font_size=16, font_color="intelligence", bold=True)
            self.text(slide, question, 4.83, 4.00 + i * 0.59, 7.22, 0.44, font_size=17)

    def verify_compile(self, slide: Any, scene: dict[str, Any]) -> None:
        v = scene["visual"]
        self.line(slide, 2.63, 2.75, 4.06, 2.75, line="practitioner")
        self.line(slide, 6.40, 2.75, 7.78, 2.75, line="solution")
        self.line(slide, 5.20, 3.42, 5.20, 4.67, line="danger")
        self.line(slide, 4.15, 5.22, 3.38, 4.20, line="danger", arrow=False, dashed=True)
        self.line(slide, 3.38, 4.20, 4.25, 3.42, line="danger", dashed=True)
        self.loop_node(slide, v["candidate"]["label"], 0.76, 2.12, 1.88, 1.26, role="practitioner", font_size=16)
        self.loop_node(slide, v["verifier"]["label"], 4.05, 2.06, 2.38, 1.38, role="practitioner", mode="deterministic", font_size=17)
        self.loop_node(slide, v["accepted"]["label"], 7.76, 2.12, 2.02, 1.26, role="solution", font_size=17)
        self.loop_node(slide, v["repair"]["label"], 4.10, 4.65, 2.18, 1.14, role="practitioner", mode="hybrid", font_size=17)
        self.text(slide, v["accepted"]["relation"], 6.58, 2.43, 1.06, 0.26, font_size=16, font_color="solution", bold=True, align="CENTER")
        self.text(slide, v["repair"]["relation"], 5.45, 3.92, 1.25, 0.26, font_size=16, font_color="danger", bold=True, align="CENTER")
        run_history = v["runHistory"]
        self.rect(slide, 10.12, 1.84, 2.08, 4.24, fill="staticSoft", line="static", line_width=45)
        self.text(slide, run_history["label"], 10.36, 2.12, 1.60, 0.42, font_size=23, font_color="static", bold=True, align="CENTER")
        self.text(slide, "\n".join(f"• {item}" for item in run_history["items"]), 10.32, 2.83, 1.67, 2.72, font_size=16, valign="TOP")

    def final_slide(self, slide: Any, scene: dict[str, Any]) -> None:
        v = scene["visual"]
        self.rect(slide, 0.82, 1.82, 5.24, 4.22, fill="practitionerSoft", line="practitioner", line_width=48)
        self.text(slide, "Practitioner task profiles", 1.12, 2.11, 4.64, 0.48, font_size=24, font_color="practitioner", bold=True, align="CENTER")
        for i, item in enumerate(v["practitionerTasks"]):
            self.text(slide, f"{i + 1:02d}", 1.18, 2.91 + i * 0.66, 0.42, 0.28, font_size=16, font_color="practitioner", bold=True)
            self.text(slide, item, 1.78, 2.82 + i * 0.66, 3.72, 0.44, font_size=17)
        self.text(slide, v["reviewLabel"].upper(), 1.14, 5.56, 4.58, 0.28, font_size=14, font_color="static", bold=True, align="CENTER")
        for i, statement in enumerate(v["statements"]):
            role = ["practitioner", "intelligence", "solution"][i]
            line_key, fill_key = self.role_colors(role)
            self.rect(slide, 6.65, 2.00 + i * 1.27, 5.20, 0.92, fill=fill_key, line=line_key, line_width=42)
            self.text(slide, statement, 6.96, 2.13 + i * 1.27, 4.58, 0.62, font_size=19, bold=True, align="CENTER")

    def add_notes(self, slide: Any, scene: dict[str, Any]) -> None:
        try:
            notes = slide.getNotesPage()
            source_text = (
                "[Sources]\n"
                "- Repository slide source: showcase/showcase-data.js\n"
                "- Repository overview: README.md\n"
                "- Architecture review: docs/architecture/"
                "LOOP-ENGINE-ARCHITECTURE-DRIFT-AUDIT-2026-08-25.md\n"
                f"\nSlide implementation note: {scene.get('annotation', '')}"
            )
            obj = self.doc.createInstance("com.sun.star.drawing.TextShape")
            obj.Position = point(ins(0.65), ins(4.50))
            obj.Size = size(ins(11.8), ins(2.20))
            obj.String = source_text
            notes.add(obj)
            cursor = obj.createTextCursor()
            cursor.gotoEnd(True)
            set_if(cursor, "CharFontName", FONT)
            set_if(cursor, "CharHeight", 12.0)
            self.notes_added += 1
        except Exception:
            pass

    def build(self) -> None:
        slides = self.data["slides"]
        dispatch = {
            "overview": self.overview,
            "loop-object": self.loop_object,
            "typed-flow": self.typed_flow,
            "two-column": self.two_column,
            "mode": self.mode_slide,
            "comparison": self.comparison,
            "hierarchy": self.hierarchy,
            "steps": self.steps,
            "spawn": self.spawn,
            "access": self.access,
            "pillars": self.pillars,
            "intelligence-branch": self.intelligence_branch,
            "matrix": self.matrix,
            "dag": self.dag,
            "services": self.services,
            "workflow": self.workflow,
            "worked-stage": self.worked_stage,
            "verify-compile": self.verify_compile,
            "final": self.final_slide,
        }
        for index, scene in enumerate(slides):
            slide = self.new_slide(index)
            if scene["kind"] == "title":
                self.title_slide(slide, scene)
            else:
                self.base(slide, scene, index, len(slides))
                render = dispatch.get(scene["kind"])
                if render is None:
                    raise ValueError(f"No PowerPoint renderer for slide kind {scene['kind']!r}")
                render(slide, scene)
            self.add_notes(slide, scene)


def export_json(root: Path, source: Path, output: Path) -> None:
    helper = root / "tools" / "export-slide-data.mjs"
    subprocess.run(["node", str(helper), str(source), str(output)], check=True)


def create_deck(data: dict[str, Any], output: Path) -> tuple[int, int, int]:
    output.parent.mkdir(parents=True, exist_ok=True)
    with UnoOffice() as office:
        doc = office.desktop().loadComponentFromURL(
            "private:factory/simpress", "_blank", 0, (prop("Hidden", True),)
        )
        closed = False
        try:
            builder = DeckBuilder(doc, data)
            builder.build()
            pages = doc.getDrawPages().getCount()
            if pages != len(data["slides"]):
                raise RuntimeError(f"Expected {len(data['slides'])} slides, created {pages}")
            doc.storeAsURL(
                uno.systemPathToFileUrl(str(output.resolve())),
                (prop("FilterName", "Impress MS PowerPoint 2007 XML"), prop("Overwrite", True)),
            )
            doc.close(True)
            closed = True
            reopened_doc = office.desktop().loadComponentFromURL(
                uno.systemPathToFileUrl(str(output.resolve())),
                "_blank",
                0,
                (prop("Hidden", True),),
            )
            if reopened_doc is None:
                raise RuntimeError("LibreOffice could not reopen the generated PowerPoint")
            try:
                reopened = reopened_doc.getDrawPages().getCount()
                if reopened != pages:
                    raise RuntimeError(
                        f"Reopened PowerPoint has {reopened} slides; expected {pages}"
                    )
            finally:
                reopened_doc.close(True)
            return pages, builder.notes_added, reopened
        finally:
            if not closed:
                doc.close(True)


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=root / "showcase-data.js")
    parser.add_argument("--output", type=Path, default=root / "assets" / "loop-engine-showcase.pptx")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parent
    if not args.source.exists():
        raise FileNotFoundError(f"Showcase source does not exist: {args.source}")
    with tempfile.TemporaryDirectory(prefix="loop-engine-pptx-data-") as tmp:
        json_path = Path(tmp) / "showcase-data.json"
        export_json(root, args.source.resolve(), json_path)
        data = json.loads(json_path.read_text(encoding="utf-8"))
    if len(data.get("slides", [])) != 26:
        raise RuntimeError(f"Expected 26 showcase slides, found {len(data.get('slides', []))}")
    pages, notes, reopened = create_deck(data, args.output)
    print(json.dumps({
        "output": str(args.output.resolve()),
        "slides_created": pages,
        "slides_reopened": reopened,
        "notes_pages_written": notes,
        "bytes": args.output.stat().st_size,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
