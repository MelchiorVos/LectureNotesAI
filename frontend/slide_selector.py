"""
Slide selector GUI – lets the user mark slides for exclusion before processing.
"""

from typing import List, Set, Optional

import customtkinter as ctk
from PIL import Image, ImageTk

from frontend.theme import (
    ACCENT,
    ACCENT_HOVER,
    BG,
    FG,
    MUTED,
    BORDER,
    RED,
    RED_BG,
    GREEN_BG,
    force_focus,
)


def select_slides_to_exclude(image_paths: List[str]) -> Optional[Set[int]]:
    """
    Show a CustomTkinter GUI to select which slides to exclude.

    Controls:
    - Left/Right arrows: Navigate slides
    - Enter/Space: Toggle exclude for current slide
    - Escape: Abort (returns None)
    - Q: Confirm and continue

    Returns:
        Set of 1-based page numbers to exclude, or None if aborted.
    """
    if not image_paths:
        return set()

    excluded: Set[int] = set()
    current_index = [0]
    aborted = [False]

    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title("Slide Selector")
    root.configure(fg_color=BG)
    root.resizable(True, True)

    # Container
    container = ctk.CTkFrame(root, fg_color=BG)
    container.pack(fill="both", expand=True, padx=24, pady=16)

    # Top row: title + status
    top_frame = ctk.CTkFrame(container, fg_color=BG)
    top_frame.pack(fill="x", pady=(0, 8))

    ctk.CTkLabel(
        top_frame,
        text="Slide Selector",
        font=ctk.CTkFont(size=22, weight="bold"),
        text_color=FG,
    ).pack(side="left")

    status_label = ctk.CTkLabel(
        top_frame,
        text="",
        font=ctk.CTkFont(size=13),
        text_color=MUTED,
    )
    status_label.pack(side="right")

    # Slide counter
    counter_label = ctk.CTkLabel(
        container,
        text="",
        font=ctk.CTkFont(size=14, weight="bold"),
        text_color=FG,
    )
    counter_label.pack(pady=(0, 8))

    # Image frame with border
    image_frame = ctk.CTkFrame(
        container,
        fg_color="#F8FAFC",
        border_color=BORDER,
        border_width=2,
        corner_radius=12,
    )
    image_frame.pack(fill="both", expand=True, pady=(0, 12))

    image_label = ctk.CTkLabel(image_frame, text="")
    image_label.pack(expand=True, padx=8, pady=8)

    # Exclude badge
    badge_label = ctk.CTkLabel(
        container,
        text="",
        font=ctk.CTkFont(size=13, weight="bold"),
        height=28,
        corner_radius=6,
    )
    badge_label.pack(pady=(0, 8))

    # Navigation + toggle row
    nav_frame = ctk.CTkFrame(container, fg_color=BG)
    nav_frame.pack(fill="x", pady=(0, 8))

    prev_btn = ctk.CTkButton(
        nav_frame,
        text="←  Previous",
        width=120,
        height=38,
        font=ctk.CTkFont(size=13),
        fg_color="#F1F5F9",
        hover_color="#E2E8F0",
        text_color=FG,
        corner_radius=8,
    )
    prev_btn.pack(side="left")

    next_btn = ctk.CTkButton(
        nav_frame,
        text="Next  →",
        width=120,
        height=38,
        font=ctk.CTkFont(size=13),
        fg_color="#F1F5F9",
        hover_color="#E2E8F0",
        text_color=FG,
        corner_radius=8,
    )
    next_btn.pack(side="right")

    toggle_btn = ctk.CTkButton(
        nav_frame,
        text="",
        width=200,
        height=38,
        font=ctk.CTkFont(size=13, weight="bold"),
        corner_radius=8,
    )
    toggle_btn.pack(expand=True, padx=16)

    # Bottom row: instructions + action buttons
    bottom_frame = ctk.CTkFrame(container, fg_color=BG)
    bottom_frame.pack(fill="x")

    ctk.CTkLabel(
        bottom_frame,
        text="← → Navigate   |   Enter/Space: Toggle   |   Q: Confirm   |   Esc: Abort",
        font=ctk.CTkFont(size=11),
        text_color=MUTED,
    ).pack(side="left")

    abort_btn = ctk.CTkButton(
        bottom_frame,
        text="Abort",
        width=80,
        height=34,
        font=ctk.CTkFont(size=13),
        fg_color="#FEF2F2",
        hover_color="#FEE2E2",
        text_color=RED,
        border_color=RED,
        border_width=1,
        corner_radius=8,
    )
    abort_btn.pack(side="right", padx=(8, 0))

    confirm_btn = ctk.CTkButton(
        bottom_frame,
        text="Confirm",
        width=100,
        height=34,
        font=ctk.CTkFont(size=13, weight="bold"),
        fg_color=ACCENT,
        hover_color=ACCENT_HOVER,
        text_color="#FFFFFF",
        corner_radius=8,
    )
    confirm_btn.pack(side="right")

    # ---- Display logic ----

    target_w = [700]
    target_h = [750]

    def update_display():
        idx = current_index[0]
        page_num = idx + 1
        total = len(image_paths)
        is_excluded = page_num in excluded

        win_w = root.winfo_width()
        win_h = root.winfo_height()
        if win_w < 100:
            win_w = target_w[0]
            win_h = target_h[0]

        img = Image.open(image_paths[idx])
        max_h = max(win_h - 260, 300)
        max_w = max(win_w - 80, 400)
        ratio = min(max_w / img.width, max_h / img.height, 1.0)
        new_size = (int(img.width * ratio), int(img.height * ratio))
        img = img.resize(new_size, Image.Resampling.LANCZOS)

        photo = ImageTk.PhotoImage(img)
        image_label.configure(image=photo)
        image_label.image = photo

        counter_label.configure(text=f"Slide {page_num} of {total}")
        status_label.configure(text=f"{len(excluded)} slide{'s' if len(excluded) != 1 else ''} excluded")

        if is_excluded:
            badge_label.configure(text="  EXCLUDED  ", fg_color=RED_BG, text_color=RED)
            image_frame.configure(border_color=RED)
        else:
            badge_label.configure(text="  INCLUDED  ", fg_color=GREEN_BG, text_color="#16A34A")
            image_frame.configure(border_color=BORDER)

        if is_excluded:
            toggle_btn.configure(text="Include this slide", fg_color="#16A34A", hover_color="#15803D", text_color="#FFFFFF")
        else:
            toggle_btn.configure(text="Exclude this slide", fg_color=RED, hover_color="#DC2626", text_color="#FFFFFF")

        prev_btn.configure(state="normal" if idx > 0 else "disabled")
        next_btn.configure(state="normal" if idx < total - 1 else "disabled")

    def go_prev():
        if current_index[0] > 0:
            current_index[0] -= 1
            update_display()

    def go_next():
        if current_index[0] < len(image_paths) - 1:
            current_index[0] += 1
            update_display()

    def toggle():
        page_num = current_index[0] + 1
        if page_num in excluded:
            excluded.remove(page_num)
        else:
            excluded.add(page_num)
        update_display()

    def on_confirm():
        root.destroy()

    def on_abort():
        aborted[0] = True
        root.destroy()

    prev_btn.configure(command=go_prev)
    next_btn.configure(command=go_next)
    toggle_btn.configure(command=toggle)
    confirm_btn.configure(command=on_confirm)
    abort_btn.configure(command=on_abort)

    def on_key(event):
        if event.keysym in ("Right", "Down"):
            go_next()
        elif event.keysym in ("Left", "Up"):
            go_prev()
        elif event.keysym in ("Return", "space"):
            toggle()
        elif event.keysym in ("q", "Q"):
            on_confirm()
        elif event.keysym == "Escape":
            on_abort()

    root.bind("<Key>", on_key)
    root.protocol("WM_DELETE_WINDOW", on_abort)

    _resize_job = [None]

    def _on_resize(event):
        if _resize_job[0] is not None:
            root.after_cancel(_resize_job[0])
        _resize_job[0] = root.after(150, update_display)

    root.bind("<Configure>", _on_resize)

    # Initial display
    update_display()

    # Size and center
    root.update_idletasks()
    w = max(root.winfo_width(), 700)
    h = max(root.winfo_height(), 750)
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - w) // 2
    y = (sh - h) // 2
    root.geometry(f"{w}x{h}+{x}+{y}")

    # Focus
    root.lift()
    root.attributes("-topmost", True)
    root.update()
    force_focus(root)
    root.after(200, lambda: root.attributes("-topmost", False))
    root.focus_force()

    root.mainloop()

    if aborted[0]:
        return None
    return excluded
