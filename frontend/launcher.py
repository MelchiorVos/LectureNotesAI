"""
Launcher GUI – collects PDF path, course name, and slide-review preference.
"""

import os
from dataclasses import dataclass
from typing import Optional, List

import customtkinter as ctk
from tkinterdnd2 import TkinterDnD, DND_FILES


from frontend.theme import (
    ACCENT,
    ACCENT_HOVER,
    BG,
    FG,
    MUTED,
    BORDER,
    force_focus,
)


AVAILABLE_MODELS = ["gpt-5.2", "gpt-5-mini"]


def discover_courses() -> list[str]:
    """Return sorted course names derived from NOTION_PAGE_* env vars."""
    import os
    courses = []
    for key in os.environ:
        if key.startswith("NOTION_PAGE_"):
            name = key.removeprefix("NOTION_PAGE_").replace("_", " ").title()
            courses.append(name)
    return sorted(courses)


@dataclass
class LauncherResult:
    pdf_path: str
    course_name: str
    model: str
    select_slides: bool


class _TkinterDnDCustomTk(ctk.CTk, TkinterDnD.DnDWrapper):
    """CustomTkinter root window with TkinterDnD2 drag-and-drop support."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.TkdndVersion = TkinterDnD._require(self)


class LauncherApp:
    def __init__(self) -> None:
        self.result: Optional[LauncherResult] = None
        self._pdf_path: Optional[str] = None

        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.root = _TkinterDnDCustomTk()
        self.root.title("Tutor")
        self.root.geometry("560x520")
        self.root.resizable(True, True)
        self.root.configure(fg_color=BG)

        self._build_ui()
        self._center_window()

        # Focus
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.update()
        force_focus(self.root)
        self.root.after(200, lambda: self.root.attributes("-topmost", False))
        self.root.focus_force()

        # Close = abort
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---- UI ----

    def _build_ui(self) -> None:
        container = ctk.CTkFrame(self.root, fg_color=BG)
        container.pack(fill="both", expand=True, padx=32, pady=24)

        # Title
        ctk.CTkLabel(
            container,
            text="Tutor",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=FG,
        ).pack(anchor="w")

        ctk.CTkLabel(
            container,
            text="Process lecture slides with AI explanations",
            font=ctk.CTkFont(size=13),
            text_color=MUTED,
        ).pack(anchor="w", pady=(0, 20))

        # Drop zone
        self._drop_frame = ctk.CTkFrame(
            container,
            fg_color="#F8FAFC",
            border_color=BORDER,
            border_width=2,
            corner_radius=12,
        )
        self._drop_frame.pack(fill="both", expand=True, pady=(0, 20))

        self._drop_icon = ctk.CTkLabel(
            self._drop_frame,
            text="📄",
            font=ctk.CTkFont(size=32),
            text_color=MUTED,
        )
        self._drop_icon.pack(pady=(20, 4))

        self._drop_label = ctk.CTkLabel(
            self._drop_frame,
            text="Drop a PDF here, or click to browse",
            font=ctk.CTkFont(size=13),
            text_color=MUTED,
        )
        self._drop_label.pack()

        self._drop_sublabel = ctk.CTkLabel(
            self._drop_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=ACCENT,
        )
        self._drop_sublabel.pack(pady=(2, 0))

        # Drag-and-drop bindings
        self._drop_frame.drop_target_register(DND_FILES)
        self._drop_frame.dnd_bind("<<DropEnter>>", self._on_drag_enter)
        self._drop_frame.dnd_bind("<<DropLeave>>", self._on_drag_leave)
        self._drop_frame.dnd_bind("<<Drop>>", self._on_drop)

        for widget in (self._drop_frame, self._drop_icon, self._drop_label, self._drop_sublabel):
            widget.bind("<Button-1>", self._on_browse)

        # Course dropdown
        ctk.CTkLabel(
            container,
            text="Course",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=FG,
        ).pack(anchor="w", pady=(0, 4))

        courses = discover_courses()
        self._course_var = ctk.StringVar(value=courses[0] if courses else "")
        self._course_dropdown = ctk.CTkOptionMenu(
            container,
            variable=self._course_var,
            values=courses if courses else ["No courses found"],
            width=300,
            height=36,
            font=ctk.CTkFont(size=13),
            fg_color="#F1F5F9",
            button_color="#E2E8F0",
            button_hover_color="#CBD5E1",
            text_color=FG,
            dropdown_fg_color=BG,
            dropdown_text_color=FG,
            dropdown_hover_color="#F1F5F9",
            corner_radius=8,
        )
        self._course_dropdown.pack(anchor="w", pady=(0, 16))

        # Model dropdown
        ctk.CTkLabel(
            container,
            text="Model",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=FG,
        ).pack(anchor="w", pady=(0, 4))

        self._model_var = ctk.StringVar(value=AVAILABLE_MODELS[0])
        self._model_dropdown = ctk.CTkOptionMenu(
            container,
            variable=self._model_var,
            values=AVAILABLE_MODELS,
            width=300,
            height=36,
            font=ctk.CTkFont(size=13),
            fg_color="#F1F5F9",
            button_color="#E2E8F0",
            button_hover_color="#CBD5E1",
            text_color=FG,
            dropdown_fg_color=BG,
            dropdown_text_color=FG,
            dropdown_hover_color="#F1F5F9",
            corner_radius=8,
        )
        self._model_dropdown.pack(anchor="w", pady=(0, 16))

        # Slide selector checkbox
        self._exclude_var = ctk.BooleanVar(value=True)
        self._exclude_check = ctk.CTkCheckBox(
            container,
            text="Review slides before processing  (choose which slides to skip)",
            variable=self._exclude_var,
            font=ctk.CTkFont(size=13),
            text_color=FG,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            border_color=BORDER,
            corner_radius=4,
        )
        self._exclude_check.pack(anchor="w", pady=(0, 24))

        # Process button
        self._process_btn = ctk.CTkButton(
            container,
            text="Process Lecture",
            font=ctk.CTkFont(size=15, weight="bold"),
            height=44,
            corner_radius=10,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            text_color="#FFFFFF",
            command=self._on_process,
            state="disabled",
        )
        self._process_btn.pack(fill="x")

    # ---- Drag-and-drop handlers ----

    def _on_drag_enter(self, event):
        self._drop_frame.configure(border_color=ACCENT)

    def _on_drag_leave(self, event):
        color = ACCENT if self._pdf_path else BORDER
        self._drop_frame.configure(border_color=color)

    def _on_drop(self, event):
        path = event.data.strip()
        if path.startswith("{") and path.endswith("}"):
            path = path[1:-1]
        self._set_pdf(path)

    def _on_browse(self, event=None):
        from tkinter import filedialog

        path = filedialog.askopenfilename(
            title="Select PDF",
            filetypes=[("PDF files", "*.pdf")],
            parent=self.root,
        )
        if path:
            self._set_pdf(path)

    def _set_pdf(self, path: str) -> None:
        if not path.lower().endswith(".pdf"):
            self._drop_label.configure(text="Only PDF files are accepted", text_color="#EF4444")
            self.root.after(
                2000,
                lambda: self._drop_label.configure(
                    text="Drop a PDF here, or click to browse", text_color=MUTED
                ),
            )
            self._drop_frame.configure(border_color=BORDER)
            return

        self._pdf_path = path
        filename = os.path.basename(path)

        self._drop_icon.configure(text="✅")
        self._drop_label.configure(text=filename, text_color=FG, font=ctk.CTkFont(size=14, weight="bold"))
        self._drop_sublabel.configure(text="Click or drop to replace")
        self._drop_frame.configure(border_color=ACCENT, fg_color="#F0F7FF")

        self._process_btn.configure(state="normal")

    # ---- Actions ----

    def _on_process(self) -> None:
        if not self._pdf_path:
            return
        self.result = LauncherResult(
            pdf_path=self._pdf_path,
            course_name=self._course_var.get(),
            model=self._model_var.get(),
            select_slides=self._exclude_var.get(),
        )
        self.root.destroy()

    def _on_close(self) -> None:
        self.result = None
        self.root.destroy()

    # ---- Helpers ----

    def _center_window(self) -> None:
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() - w) // 2
        y = (self.root.winfo_screenheight() - h) // 2
        self.root.geometry(f"+{x}+{y}")

    def run(self) -> Optional[LauncherResult]:
        self.root.mainloop()
        return self.result


def launch() -> Optional[LauncherResult]:
    """Open the launcher GUI. Returns LauncherResult or None if closed."""
    app = LauncherApp()
    return app.run()


if __name__ == "__main__":
    result = launch()
    if result:
        print(f"PDF:    {result.pdf_path}")
        print(f"Course: {result.course_name}")
        print(f"Review: {result.select_slides}")
    else:
        print("Aborted.")
