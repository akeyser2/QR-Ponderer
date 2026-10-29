import ctypes
import glob
import io
import math
import os
import platform
import shutil
import subprocess
import tempfile
import urllib.request
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, ttk
from PIL import Image, ImageColor, ImageDraw, ImageFilter, ImageFont, ImageOps, ImageTk
import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import (
    CircleModuleDrawer,
    GappedSquareModuleDrawer,
    HorizontalBarsDrawer,
    RoundedModuleDrawer,
    SquareModuleDrawer,
    VerticalBarsDrawer,
)

import sys

# Make sure correct run syst
if getattr(sys, "frozen", False):
    SCRIPT_DIR = sys._MEIPASS
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Media
WIZ_PATH = os.path.join(SCRIPT_DIR, "wiz.png")
ICON_PATH = os.path.join(SCRIPT_DIR, "orb.ico")
FONT_URL = (
    "https://raw.githubusercontent.com/google/fonts/main/"
    "ofl/jacquardabastarda9/JacquardaBastarda9-Regular.ttf"
)
FONT_PATH = os.path.join(SCRIPT_DIR, "JacquardaBastarda9-Regular.ttf")

APP_TITLE = "QR Orb Pondering"
WIN_SIZE = 1020
PANEL_BOUNDS = (54, 18, 966, 334)

# Where Orb (might need to adjust this if i change sizing)
ORB_CENTER_X = int(WIN_SIZE * 0.488)  # 498 px
ORB_CENTER_Y = int(WIN_SIZE * 0.812)  # 828 px (lowered from 0.775)
ORB_QR_SIZE = 290

# Color stuff
PALETTE_DARK = (3, 30, 46)
PALETTE_PANEL_RGBA = (3, 30, 46, 185)
PALETTE_TEAL_MID = (28, 114, 120)
PALETTE_SAGE = (123, 154, 139)
PALETTE_GLOW_CYAN = (145, 225, 205)
PALETTE_GOLD = (212, 214, 180)
HEX_DARK = "#031e2e"
HEX_TEAL = "#13525c"
HEX_GOLD = "#d4d6b4"

STYLE_MAP = {
    "Square (Default)": SquareModuleDrawer,
    "Rounded Corners": RoundedModuleDrawer,
    "Circle Dots": CircleModuleDrawer,
    "Gapped Squares": GappedSquareModuleDrawer,
    "Vertical Bars": VerticalBarsDrawer,
    "Horizontal Bars": HorizontalBarsDrawer,
}

# Honestly not sure how this works, but its for animation stuff
qr_color = "#031e2e"
bg_color = "#ffffff"
status_message = ""
status_color = PALETTE_GOLD

cached_ui_frame: Image.Image | None = None
cached_qr_scaled: Image.Image | None = None
pulse_step = 0




# Fun font from googlefonts, I think i can include the font when i build to exe
def ensure_pixel_font() -> str | None:
    existing = glob.glob(os.path.join(SCRIPT_DIR, "*Jacquarda*.ttf"))
    if existing:
        font_file = existing[0]
    else:
        font_file = FONT_PATH
        try:
            urllib.request.urlretrieve(FONT_URL, font_file)
        except Exception:
            return None

    system = platform.system()
    try:
        if system == "Windows":
            ctypes.windll.gdi32.AddFontResourceExW(font_file, 0x10, 0)
        elif system == "Linux":
            user_font_dir = os.path.expanduser("~/.local/share/fonts")
            os.makedirs(user_font_dir, exist_ok=True)
            dest = os.path.join(user_font_dir, os.path.basename(font_file))
            if not os.path.exists(dest):
                shutil.copy(font_file, dest)
                subprocess.run(["fc-cache", "-f"], check=False)
    except Exception:
        pass

    return font_file


LOADED_FONT_PATH = ensure_pixel_font()


def get_pil_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if LOADED_FONT_PATH and os.path.exists(LOADED_FONT_PATH):
        return ImageFont.truetype(LOADED_FONT_PATH, size)
    return ImageFont.load_default()


# Fun pixel border thing i found
def draw_old_english_pixel_panel(img: Image.Image, bounds: tuple[int, int, int, int]) -> Image.Image:
    """Draws a semi-transparent panel with stepped Gothic/Old English pixel borders."""
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    x1, y1, x2, y2 = bounds
    p = 3  # Change corner size here

    # Adjust transparency here if its too hard to see funny man
    draw.rectangle((x1 + p * 2, y1 + p * 2, x2 - p * 2, y2 - p * 2), fill=PALETTE_PANEL_RGBA)

    def pixel_rect(rx1, ry1, rx2, ry2, color, thickness=p):
        draw.rectangle((rx1, ry1, rx2, ry1 + thickness - 1), fill=color)
        draw.rectangle((rx1, ry2 - thickness + 1, rx2, ry2), fill=color)
        draw.rectangle((rx1, ry1, rx1 + thickness - 1, ry2), fill=color)
        draw.rectangle((rx2 - thickness + 1, ry1, rx2, ry2), fill=color)

    pixel_rect(x1 + p, y1 + p, x2 - p, y2 - p, PALETTE_DARK + (255,), p)
    pixel_rect(x1 + p * 2, y1 + p * 2, x2 - p * 2, y2 - p * 2, PALETTE_GOLD + (255,), p)
    pixel_rect(x1 + p * 3, y1 + p * 3, x2 - p * 3, y2 - p * 3, PALETTE_DARK + (255,), p)
    pixel_rect(x1 + p * 4, y1 + p * 4, x2 - p * 4, y2 - p * 4, PALETTE_TEAL_MID + (255,), p)

    # Adjust corner look here too depending how it looks but idc too much
    corners = [
        (x1 + p * 2, y1 + p * 2),
        (x2 - p * 2, y1 + p * 2),
        (x1 + p * 2, y2 - p * 2),
        (x2 - p * 2, y2 - p * 2),
    ]
    for cx, cy in corners:
        draw.rectangle((cx - p * 3, cy - p, cx + p * 3, cy + p), fill=PALETTE_DARK + (255,))
        draw.rectangle((cx - p, cy - p * 3, cx + p, cy + p * 3), fill=PALETTE_DARK + (255,))
        draw.rectangle((cx - p * 2, cy - p // 2, cx + p * 2, cy + p // 2), fill=PALETTE_GOLD + (255,))
        draw.rectangle((cx - p // 2, cy - p * 2, cx + p // 2, cy + p * 2), fill=PALETTE_GOLD + (255,))
        draw.rectangle((cx - p // 2, cy - p // 2, cx + p // 2, cy + p // 2), fill=PALETTE_SAGE + (255,))

    in_offset = p * 6
    for cx, cy, dx, dy in [
        (x1 + in_offset, y1 + in_offset, 1, 1),
        (x2 - in_offset, y1 + in_offset, -1, 1),
        (x1 + in_offset, y2 - in_offset, 1, -1),
        (x2 - in_offset, y2 - in_offset, -1, -1),
    ]:
        draw.rectangle(
            (min(cx, cx + dx * p * 4), cy, max(cx, cx + dx * p * 4), cy + p - 1),
            fill=PALETTE_GOLD + (255,),
        )
        draw.rectangle(
            (cx, min(cy, cy + dy * p * 3), cx + p - 1, max(cy, cy + dy * p * 3)),
            fill=PALETTE_GOLD + (255,),
        )

    mid_x = (x1 + x2) // 2
    for my in (y1 + p * 2, y2 - p * 2):
        draw.rectangle((mid_x - p * 4, my - p, mid_x + p * 4, my + p), fill=PALETTE_GOLD + (255,))
        draw.rectangle((mid_x - p, my - p * 2, mid_x + p, my + p * 2), fill=PALETTE_GOLD + (255,))
        draw.rectangle((mid_x - p // 2, my - p // 2, mid_x + p // 2, my + p // 2), fill=PALETTE_DARK + (255,))

    return Image.alpha_composite(img, overlay)


def make_pixel_button_image(text: str, width: int, height: int, bg_rgb: tuple[int, int, int]) -> ImageTk.PhotoImage:
    img = Image.new("RGBA", (width, height), bg_rgb + (255,))
    draw = ImageDraw.Draw(img)
    draw.fontmode = "1"
    p = 2

    draw.rectangle((0, 0, width - 1, p - 1), fill=PALETTE_GOLD + (255,))
    draw.rectangle((0, height - p, width - 1, height - 1), fill=PALETTE_GOLD + (255,))
    draw.rectangle((0, 0, p - 1, height - 1), fill=PALETTE_GOLD + (255,))
    draw.rectangle((width - p, 0, width - 1, height - 1), fill=PALETTE_GOLD + (255,))

    for cx, cy in [(p, p), (width - p * 2, p), (p, height - p * 2), (width - p * 2, height - p * 2)]:
        draw.rectangle((cx, cy, cx + p - 1, cy + p - 1), fill=PALETTE_GOLD + (255,))

    font = get_pil_font(20)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = (width - tw) // 2
    ty = (height - th) // 2 - bbox[1]

    draw.text((tx + 2, ty + 2), text, font=font, fill=PALETTE_DARK + (255,))
    draw.text((tx, ty), text, font=font, fill=PALETTE_GOLD + (255,))
    return ImageTk.PhotoImage(img)


# Pulsing effect for qr code when pondering
GLOW_PATCH_SIZE = ORB_QR_SIZE + 120  


def build_pulse_frames(num_frames: int = 24) -> list[Image.Image]:
    # prerender the frames to save compute although i doubt itll matter
    frames = []
    half = GLOW_PATCH_SIZE // 2
    qr_half = ORB_QR_SIZE // 2
    pixel_step = 5  

    for i in range(num_frames):
        t = (math.sin(2 * math.pi * i / num_frames) + 1.0) / 2.0

        glow = Image.new("RGBA", (GLOW_PATCH_SIZE, GLOW_PATCH_SIZE), (0, 0, 0, 0))
        draw = ImageDraw.Draw(glow)

        spread = int(14 + 22 * t)
        outer_alpha = int(75 + 95 * t)
        r = int(PALETTE_GLOW_CYAN[0] * (1 - t * 0.4) + PALETTE_GOLD[0] * (t * 0.4))
        g = int(PALETTE_GLOW_CYAN[1] * (1 - t * 0.4) + PALETTE_GOLD[1] * (t * 0.4))
        b = int(PALETTE_GLOW_CYAN[2] * (1 - t * 0.4) + PALETTE_GOLD[2] * (t * 0.4))

        draw.rounded_rectangle(
            (
                half - qr_half - spread,
                half - qr_half - spread,
                half + qr_half + spread,
                half + qr_half + spread,
            ),
            radius=28,
            fill=(r, g, b, outer_alpha),
        )

        rim_spread = int(5 + 8 * t)
        rim_alpha = int(130 + 90 * t)
        draw.rounded_rectangle(
            (
                half - qr_half - rim_spread,
                half - qr_half - rim_spread,
                half + qr_half + rim_spread,
                half + qr_half + rim_spread,
            ),
            radius=14,
            outline=PALETTE_GOLD + (rim_alpha,),
            width=6,
        )

        # blur effect
        glow = glow.filter(ImageFilter.GaussianBlur(radius=10 + 6 * t))
        small = glow.resize(
            (GLOW_PATCH_SIZE // pixel_step, GLOW_PATCH_SIZE // pixel_step),
            Image.Resampling.BILINEAR,
        )
        pixelated_glow = small.resize((GLOW_PATCH_SIZE, GLOW_PATCH_SIZE), Image.Resampling.NEAREST)
        frames.append(pixelated_glow)

    return frames


PULSE_FRAMES = build_pulse_frames()


# -------------------
# QR STUFF
# -------------------
# TODO: Fix so the big squares also adjust to the theme
def generate_qr_image(url: str, show_warning: bool = True) -> Image.Image | None:
    if not url:
        if show_warning:
            messagebox.showwarning("Missing URL", "Please enter a URL first.")
        return None

    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    selected_style = style_var.get()
    drawer_cls = STYLE_MAP.get(selected_style, SquareModuleDrawer)
    # Tried using any style for the eyes, but qr codes dont like that
    if selected_style in ("Square (Default)", "Gapped Squares"):
        eye_drawer_cls = SquareModuleDrawer
    else:
        eye_drawer_cls = RoundedModuleDrawer
    styled_img = qr.make_image(
        image_factory=StyledPilImage,
        module_drawer=drawer_cls(),
        eye_drawer=eye_drawer_cls(),
    )

    base_pil = styled_img.get_image().convert("L")
    mask = ImageOps.invert(base_pil)
    fg_rgb = ImageColor.getrgb(qr_color)

    if use_bg_var.get():
        bg_rgb = ImageColor.getrgb(bg_color)
        bg_layer = Image.new("RGBA", base_pil.size, bg_rgb + (255,))
        fg_layer = Image.new("RGBA", base_pil.size, fg_rgb + (255,))
        final_img = Image.composite(fg_layer, bg_layer, mask)
    else:
        final_img = Image.new("RGBA", base_pil.size, fg_rgb + (0,))
        final_img.putalpha(mask)

    return final_img


# pulse loop
def load_base_wizard() -> Image.Image:
    if os.path.exists(WIZ_PATH):
        img = Image.open(WIZ_PATH).convert("RGBA")
        alpha_mask = img.getchannel("A").point(lambda p:255 if p > 10 else 0)
        bbox = alpha_mask.getbbox()
        if bbox:
            img = img.crop(bbox)
        return img.resize((WIN_SIZE, WIN_SIZE), Image.Resampling.NEAREST)
    return Image.new("RGBA", (WIN_SIZE, WIN_SIZE), PALETTE_DARK + (255,))


BASE_WIZ_IMG = load_base_wizard()
PANEL_BASE_IMG = draw_old_english_pixel_panel(BASE_WIZ_IMG, PANEL_BOUNDS)


def rebuild_caches(*_args):
    global cached_ui_frame, cached_qr_scaled

    frame = PANEL_BASE_IMG.copy()
    draw = ImageDraw.Draw(frame)
    draw.fontmode = "1"

    font_lg = get_pil_font(24)
    font_md = get_pil_font(21)
    font_sm = get_pil_font(18)

    def draw_pixel_text(x: int, y: int, text: str, font, color=PALETTE_GOLD):
        draw.text((x + 2, y + 2), text, font=font, fill=PALETTE_DARK + (255,))
        draw.text((x, y), text, font=font, fill=color + (255,))

    # ADD MORE SETTINGS HERE IF NEEDED (i think this is fine for now tho)
    draw_pixel_text(86, 34, "Enter Desired URL:", font_lg)
    draw_pixel_text(86, 114, "QR Style:", font_md)
    draw_pixel_text(86, 158, "QR Color:", font_md)

    # checkbox
    cb_x, cb_y, cb_size = 86, 206, 20
    draw.rectangle(
        (cb_x, cb_y, cb_x + cb_size, cb_y + cb_size),
        fill=PALETTE_DARK + (255,),
        outline=PALETTE_GOLD + (255,),
        width=2,
    )
    if use_bg_var.get():
        draw.rectangle(
            (cb_x + 5, cb_y + 5, cb_x + cb_size - 5, cb_y + cb_size - 5),
            fill=PALETTE_GOLD + (255,),
        )
    draw_pixel_text(cb_x + 30, 202, "Enable BG Color", font_md)

    # color swatches, id like for them to be selectable, but this works for now
    fg_rgb = ImageColor.getrgb(qr_color)
    bg_rgb = ImageColor.getrgb(bg_color)
    draw.rectangle((708, 160, 736, 184), fill=fg_rgb + (255,), outline=PALETTE_GOLD + (255,), width=2)
    draw.rectangle((708, 204, 736, 228), fill=bg_rgb + (255,), outline=PALETTE_GOLD + (255,), width=2)

    if status_message:
        bbox = draw.textbbox((0, 0), status_message, font=font_sm)
        sw = bbox[2] - bbox[0]
        draw_pixel_text((WIN_SIZE - sw) // 2, 298, status_message, font_sm, status_color)

    cached_ui_frame = frame

    # update qr code
    url = url_entry.get().strip()
    if url:
        qr_img = generate_qr_image(url, show_warning=False)
        if qr_img:
            resample = (
                Image.Resampling.NEAREST
                if style_var.get() == "Square (Default)"
                else Image.Resampling.LANCZOS
            )
            cached_qr_scaled = qr_img.resize((ORB_QR_SIZE, ORB_QR_SIZE), resample)
        else:
            cached_qr_scaled = None
    else:
        cached_qr_scaled = None

    draw_current_frame()


def draw_current_frame():
    if cached_ui_frame is None:
        return

    frame = cached_ui_frame.copy()

    if cached_qr_scaled is not None:
        # 1. Composite the pulsing arcane aura around the QR code
        glow_img = PULSE_FRAMES[pulse_step % len(PULSE_FRAMES)]
        glow_x = ORB_CENTER_X - (GLOW_PATCH_SIZE // 2)
        glow_y = ORB_CENTER_Y - (GLOW_PATCH_SIZE // 2)
        frame.alpha_composite(glow_img, dest=(glow_x, glow_y))

        # 2. Composite the QR code on top of the glow
        paste_x = ORB_CENTER_X - (ORB_QR_SIZE // 2)
        paste_y = ORB_CENTER_Y - (ORB_QR_SIZE // 2)
        frame.alpha_composite(cached_qr_scaled, dest=(paste_x, paste_y))

    tk_frame = ImageTk.PhotoImage(frame)
    canvas.itemconfig(bg_image_id, image=tk_frame)
    canvas.image = tk_frame


def animate_pulse():
    """Advances the pulsing light animation around the QR code."""
    global pulse_step
    if cached_qr_scaled is not None:
        pulse_step = (pulse_step + 1) % len(PULSE_FRAMES)
        draw_current_frame()
    root.after(45, animate_pulse)


def set_status(msg: str, color: tuple[int, int, int] = PALETTE_GOLD):
    global status_message, status_color
    status_message = msg
    status_color = color
    rebuild_caches()


def choose_qr_color():
    global qr_color
    chosen = colorchooser.askcolor(title="Choose QR Code Color", initialcolor=qr_color)[1]
    if chosen:
        qr_color = chosen
        rebuild_caches()


def choose_bg_color():
    global bg_color
    if not use_bg_var.get():
        return
    chosen = colorchooser.askcolor(title="Choose Background Color", initialcolor=bg_color)[1]
    if chosen:
        bg_color = chosen
        rebuild_caches()


def on_canvas_click(event):
    if 86 <= event.x <= 310 and 202 <= event.y <= 230:
        use_bg_var.set(not use_bg_var.get())
        bg_color_btn.config(state="normal" if use_bg_var.get() else "disabled")
        rebuild_caches()


def save_qr():
    url = url_entry.get().strip()
    pil_img = generate_qr_image(url)
    if not pil_img:
        return

    rebuild_caches()
    file_path = filedialog.asksaveasfilename(
        title="Save QR Code",
        defaultextension=".png",
        filetypes=[("PNG Image", "*.png"), ("All Files", "*.*")],
        initialfile="qrcode.png",
    )

    if file_path:
        pil_img.save(file_path, format="PNG")
        set_status(f"Saved to: {os.path.basename(file_path)}", PALETTE_SAGE)

# Genuinely why is copying to clipboard so complicated, genuinely not even sure how this works
# multiple os support in case i put this on github or somn, but windows is probably all ill use it for
def copy_qr_to_clipboard():
    url = url_entry.get().strip()
    pil_img = generate_qr_image(url)
    if not pil_img:
        return

    rebuild_caches()
    system = platform.system()

    try:
        if system == "Windows":
            try:
                import win32clipboard

                png_buffer = io.BytesIO()
                pil_img.save(png_buffer, format="PNG")

                bg = Image.new("RGB", pil_img.size, (255, 255, 255))
                bg.paste(pil_img, mask=pil_img.split()[3])
                bmp_buffer = io.BytesIO()
                bg.save(bmp_buffer, format="BMP")
                dib_data = bmp_buffer.getvalue()[14:]

                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                png_format = win32clipboard.RegisterClipboardFormat("PNG")
                win32clipboard.SetClipboardData(png_format, png_buffer.getvalue())
                win32clipboard.SetClipboardData(win32clipboard.CF_DIB, dib_data)
                win32clipboard.CloseClipboard()
            except ImportError:
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    tmp_path = tmp.name
                bg = Image.new("RGB", pil_img.size, (255, 255, 255))
                bg.paste(pil_img, mask=pil_img.split()[3])
                bg.save(tmp_path, format="PNG")

                ps_cmd = (
                    "Add-Type -AssemblyName System.Windows.Forms, System.Drawing; "
                    f"$img = [System.Drawing.Image]::FromFile('{tmp_path}'); "
                    "[System.Windows.Forms.Clipboard]::SetImage($img); "
                    "$img.Dispose()"
                )
                subprocess.run(
                    ["powershell", "-NoProfile", "-Command", ps_cmd],
                    check=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                os.remove(tmp_path)

        elif system == "Darwin":
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp_path = tmp.name
                pil_img.save(tmp_path, format="PNG")
            subprocess.run(
                [
                    "osascript",
                    "-e",
                    f'set the clipboard to (read (POSIX file "{tmp_path}") as «class PNGf»)',
                ],
                check=True,
            )
            os.remove(tmp_path)

        elif system == "Linux":
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp_path = tmp.name
                pil_img.save(tmp_path, format="PNG")
            if shutil.which("wl-copy"):
                with open(tmp_path, "rb") as f:
                    subprocess.run(["wl-copy", "--type", "image/png"], stdin=f, check=True)
            else:
                subprocess.run(
                    ["xclip", "-selection", "clipboard", "-t", "image/png", "-i", tmp_path],
                    check=True,
                )
            os.remove(tmp_path)

        set_status("Copied QR code to clipboard!", PALETTE_GOLD)

    except Exception as e:
        messagebox.showerror("Clipboard Error", f"Could not copy to clipboard:\n{e}")


# COMPLICATED REMOVE WINDOWS BORDER STUFF 
def setup_borderless_with_taskbar():
    system = platform.system()

    if system == "Windows":
        root.overrideredirect(True)
        root.update_idletasks()

        hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
        if not hwnd:
            hwnd = root.winfo_id()

        GWL_EXSTYLE = -20
        WS_EX_APPWINDOW = 0x00040000
        WS_EX_TOOLWINDOW = 0x00000080

        get_long = getattr(ctypes.windll.user32, "GetWindowLongPtrW", ctypes.windll.user32.GetWindowLongW)
        set_long = getattr(ctypes.windll.user32, "SetWindowLongPtrW", ctypes.windll.user32.SetWindowLongW)

        style = get_long(hwnd, GWL_EXSTYLE)
        style = (style & ~WS_EX_TOOLWINDOW) | WS_EX_APPWINDOW
        set_long(hwnd, GWL_EXSTYLE, style)

        root.withdraw()
        root.after(10, root.deiconify)

    # For linux and mac
    elif system == "Linux":
        try:
            root.wm_attributes("-type", "splash")
        except tk.TclError:
            root.overrideredirect(True)

    else:  # macOS
        root.overrideredirect(True)



def minimize_window():
    system = platform.system()
    if system == "Windows":
        hwnd = ctypes.windll.user32.GetParent(root.winfo_id()) or root.winfo_id()
        SW_MINIMIZE = 6
        ctypes.windll.user32.ShowWindow(hwnd, SW_MINIMIZE)
    else:
        root.overrideredirect(False)
        root.iconify()


def on_window_restore(_event):
    if platform.system() != "Windows":
        if root.state() == "normal" and not root.overrideredirect():
            setup_borderless_with_taskbar()

# Actual app border stuff, i should probably remove the [] max screen button
APP_TITLE = "Orb QR Pondering"
TITLE_BAR_HEIGHT = 40

PURPLE_FRAME_BG = "#2e164d"
PURPLE_TITLE_BG = "#3d1e66"
PURPLE_TITLE_RIGHT = "#220e3b"
PURPLE_HILIGHT = "#7a52aa"
PURPLE_LIGHT = "#53307e"
PURPLE_SHADOW = "#180929"
PURPLE_DARK_EDGE = "#0c0417"


drag_offset_x = 0
drag_offset_y = 0


# ---------------
# GUI STUFF
# ---------------
# root = tk.Tk()
# root.title("Orb QR Pondering")
# root.geometry(f"{WIN_SIZE}x{WIN_SIZE}")
# root.resizable(False, False)

root = tk.Tk()
root.title(APP_TITLE)
root.configure(bg=PURPLE_DARK_EDGE)
root.bind("<Map>", on_window_restore)

if os.path.exists(ICON_PATH):
    try:
        if platform.system() == "Windows":
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("orb.qr.pondering.1")
            root.iconbitmap(ICON_PATH)
        pil_ico = Image.open(ICON_PATH)
        tk_app_icon = ImageTk.PhotoImage(pil_ico)
        root.iconphoto(True, tk_app_icon)
    except Exception:
        pass

# Enable borderless mode while keeping the taskbar icon active
setup_borderless_with_taskbar()



ttk_style = ttk.Style()
ttk_style.theme_use("clam")
ttk_style.configure(
    "Orb.TCombobox",
    fieldbackground=HEX_DARK,
    background=HEX_TEAL,
    foreground=HEX_GOLD,
    arrowcolor=HEX_GOLD,
    bordercolor=HEX_GOLD,
    lightcolor=HEX_GOLD,
    darkcolor=HEX_DARK,
)
ttk_style.map(
    "Orb.TCombobox",
    fieldbackground=[("readonly", HEX_DARK)],
    selectbackground=[("readonly", HEX_TEAL)],
    selectforeground=[("readonly", HEX_GOLD)],
    foreground=[("readonly", HEX_GOLD)],
)
root.option_add("*TCombobox*Listbox.background", HEX_DARK)
root.option_add("*TCombobox*Listbox.foreground", HEX_GOLD)
root.option_add("*TCombobox*Listbox.selectBackground", HEX_TEAL)
root.option_add("*TCombobox*Listbox.selectForeground", HEX_GOLD)
root.option_add("*TCombobox*Listbox.font", ("Jacquarda Bastarda 9", 14))

canvas = tk.Canvas(root, width=WIN_SIZE, height=WIN_SIZE, highlightthickness=0, bd=0)
canvas.pack(fill="both", expand=True)
bg_image_id = canvas.create_image(0, 0, anchor="nw")
canvas.bind("<Button-1>", on_canvas_click)

url_entry = tk.Entry(
    root,
    bg=HEX_DARK,
    fg=HEX_GOLD,
    insertbackground=HEX_GOLD,
    relief="flat",
    highlightthickness=2,
    highlightbackground=HEX_GOLD,
    highlightcolor=HEX_GOLD,
    font=("Jacquarda Bastarda 9", 15),
)
url_entry.bind("<KeyRelease>", rebuild_caches)
canvas.create_window(86, 68, window=url_entry, anchor="nw", width=848, height=32)
url_entry.focus()

# makes dropdowns look fun and not stand out so much
style_var = tk.StringVar(value="Square (Default)")
style_dropdown = ttk.Combobox(
    root,
    textvariable=style_var,
    values=list(STYLE_MAP.keys()),
    state="readonly",
    style="Orb.TCombobox",
    font=("Jacquarda Bastarda 9", 14),
)
style_dropdown.bind("<<ComboboxSelected>>", rebuild_caches)
canvas.create_window(604, 114, window=style_dropdown, anchor="nw", width=330, height=28)

# Color picker, would love for it to match theme too but im lazy
use_bg_var = tk.BooleanVar(value=False)

pick_qr_img = make_pixel_button_image("Pick Color", 186, 28, PALETTE_TEAL_MID)
qr_color_btn = tk.Button(
    root,
    image=pick_qr_img,
    command=choose_qr_color,
    bd=0,
    highlightthickness=0,
    activebackground=HEX_DARK,
    cursor="hand2",
)
canvas.create_window(748, 158, window=qr_color_btn, anchor="nw")

pick_bg_img = make_pixel_button_image("Pick BG", 186, 28, PALETTE_TEAL_MID)
bg_color_btn = tk.Button(
    root,
    image=pick_bg_img,
    command=choose_bg_color,
    bd=0,
    highlightthickness=0,
    activebackground=HEX_DARK,
    state="disabled",
    cursor="hand2",
)
canvas.create_window(748, 202, window=bg_color_btn, anchor="nw")

# What to do with qr, save or copy
save_btn_img = make_pixel_button_image("Save to File...", 410, 36, PALETTE_TEAL_MID)
save_btn = tk.Button(
    root,
    image=save_btn_img,
    command=save_qr,
    bd=0,
    highlightthickness=0,
    activebackground=HEX_DARK,
    cursor="hand2",
)
canvas.create_window(86, 252, window=save_btn, anchor="nw")

copy_btn_img = make_pixel_button_image("Copy to Clipboard", 410, 36, PALETTE_DARK)
copy_btn = tk.Button(
    root,
    image=copy_btn_img,
    command=copy_qr_to_clipboard,
    bd=0,
    highlightthickness=0,
    activebackground=HEX_TEAL,
    cursor="hand2",
)
canvas.create_window(524, 252, window=copy_btn, anchor="nw")






def make_win95_control_button(kind: str, size: int = 28) -> ImageTk.PhotoImage:
    img = Image.new("RGBA", (size, size), ImageColor.getrgb(PURPLE_FRAME_BG) + (255,))
    draw = ImageDraw.Draw(img)

    hi = ImageColor.getrgb(PURPLE_HILIGHT) + (255,)
    lt = ImageColor.getrgb(PURPLE_LIGHT) + (255,)
    sh = ImageColor.getrgb(PURPLE_SHADOW) + (255,)
    dk = ImageColor.getrgb(PURPLE_DARK_EDGE) + (255,)
    fg = PALETTE_GOLD + (255,)

    draw.rectangle((0, 0, size - 1, 1), fill=hi)
    draw.rectangle((0, 0, 1, size - 1), fill=hi)
    draw.rectangle((2, 2, size - 3, 3), fill=lt)
    draw.rectangle((2, 2, 3, size - 3), fill=lt)
    draw.rectangle((0, size - 2, size - 1, size - 1), fill=dk)
    draw.rectangle((size - 2, 0, size - 1, size - 1), fill=dk)
    draw.rectangle((2, size - 4, size - 3, size - 3), fill=sh)
    draw.rectangle((size - 4, 2, size - 3, size - 3), fill=sh)

    if kind == "min":
        draw.rectangle((7, size - 9, size - 8, size - 7), fill=fg)
    elif kind == "size":
        draw.rectangle((6, 6, size - 7, size - 7), outline=fg, width=2)
        draw.rectangle((6, 6, size - 7, 9), fill=fg)
    elif kind == "close":
        for i in range(7, size - 7):
            draw.rectangle((i, i, i + 1, i + 1), fill=fg)
            draw.rectangle((size - 1 - i, i, size - i, i + 1), fill=fg)

    return ImageTk.PhotoImage(img)


def make_titlebar_banner(width: int, height: int) -> ImageTk.PhotoImage:
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.fontmode = "1"

    c_left = ImageColor.getrgb(PURPLE_TITLE_BG)
    c_right = ImageColor.getrgb(PURPLE_TITLE_RIGHT)

    step = 6
    for x in range(0, width, step):
        t = x / max(1, width)
        r = int(c_left[0] * (1 - t) + c_right[0] * t)
        g = int(c_left[1] * (1 - t) + c_right[1] * t)
        b = int(c_left[2] * (1 - t) + c_right[2] * t)
        draw.rectangle((x, 0, min(x + step, width), height), fill=(r, g, b, 255))

    sh = ImageColor.getrgb(PURPLE_SHADOW) + (255,)
    hi = ImageColor.getrgb(PURPLE_HILIGHT) + (255,)
    draw.rectangle((0, 0, width - 1, 1), fill=sh)
    draw.rectangle((0, 0, 1, height - 1), fill=sh)
    draw.rectangle((0, height - 2, width - 1, height - 1), fill=hi)
    draw.rectangle((width - 2, 0, width - 1, height - 1), fill=hi)

    ox, oy = 12, height // 2
    draw.ellipse((ox - 9, oy - 9, ox + 9, oy + 9), fill=PALETTE_TEAL_MID + (255,), outline=PALETTE_GOLD + (255,), width=2)
    draw.rectangle((ox - 3, oy - 4, ox, oy - 1), fill=PALETTE_GLOW_CYAN + (255,))

    font = get_pil_font(22)
    bbox = draw.textbbox((0, 0), APP_TITLE, font=font)
    th = bbox[3] - bbox[1]
    tx, ty = 32, (height - th) // 2 - bbox[1]

    draw.text((tx + 2, ty + 2), APP_TITLE, font=font, fill=ImageColor.getrgb(PURPLE_DARK_EDGE) + (255,))
    draw.text((tx, ty), APP_TITLE, font=font, fill=PALETTE_GOLD + (255,))
    return ImageTk.PhotoImage(img)


def start_window_drag(event):
    global drag_offset_x, drag_offset_y
    drag_offset_x = event.x_root - root.winfo_x()
    drag_offset_y = event.y_root - root.winfo_y()


def do_window_drag(event):
    root.geometry(f"+{event.x_root - drag_offset_x}+{event.y_root - drag_offset_y}")





root.geometry(f"{WIN_SIZE + 20}x{WIN_SIZE + TITLE_BAR_HEIGHT + 24}")
root.configure(
    bg=PURPLE_FRAME_BG,
    bd=4,
    relief="raised",
    highlightthickness=2,
    highlightbackground=PURPLE_HILIGHT,
    highlightcolor=PURPLE_HILIGHT,
)
root.bind("<Map>", on_window_restore)

title_bar = tk.Frame(root, bg=PURPLE_FRAME_BG, height=TITLE_BAR_HEIGHT)
title_bar.pack(side="top", fill="x", padx=2, pady=(2, 2), before=canvas)
title_bar.pack_propagate(False)

banner_img = make_titlebar_banner(WIN_SIZE + 8, TITLE_BAR_HEIGHT - 4)
title_banner_label = tk.Label(title_bar, image=banner_img, bg=PURPLE_TITLE_BG, bd=0, highlightthickness=0)
title_banner_label.pack(fill="both", expand=True)
title_banner_label.bind("<ButtonPress-1>", start_window_drag)
title_banner_label.bind("<B1-Motion>", do_window_drag)

controls_frame = tk.Frame(title_banner_label, bg=PURPLE_TITLE_RIGHT)
controls_frame.place(relx=1.0, rely=0.5, x=-6, anchor="e")

min_icon = make_win95_control_button("min")
# size_icon = make_win95_control_button("size")
close_icon = make_win95_control_button("close")

tk.Button(
    controls_frame, image=min_icon, command=minimize_window,
    bd=0, highlightthickness=0, bg=PURPLE_FRAME_BG, activebackground=PURPLE_LIGHT, cursor="hand2"
).pack(side="left", padx=2)

# THIS IS FOR MAX SCREEN
# I dont plan on adding this anymore, kinda like it being a small little app
# tk.Button(
#     controls_frame, image=size_icon,
#     bd=0, highlightthickness=0, bg=PURPLE_FRAME_BG, activebackground=PURPLE_LIGHT, cursor="hand2"
# ).pack(side="left", padx=2)

tk.Button(
    controls_frame, image=close_icon, command=root.destroy,
    bd=0, highlightthickness=0, bg=PURPLE_FRAME_BG, activebackground="#8b1e3f", cursor="hand2"
).pack(side="left", padx=(2, 0))

# retro windows 3d effect
canvas.config(
    bd=3,
    relief="sunken",
    highlightthickness=1,
    highlightbackground=PURPLE_DARK_EDGE,
    highlightcolor=PURPLE_DARK_EDGE,
)
canvas.pack_configure(padx=2, pady=(0, 2))

# ico stuff
if os.path.exists(ICON_PATH):
    try:
        if platform.system() == "Windows":
            root.iconbitmap(ICON_PATH)
        pil_ico = Image.open(ICON_PATH)
        tk_app_icon = ImageTk.PhotoImage(pil_ico)
        root.iconphoto(True, tk_app_icon)
    except Exception:
        pass



# yipee
rebuild_caches()
animate_pulse()
root.mainloop()