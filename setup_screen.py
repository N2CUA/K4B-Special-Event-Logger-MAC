import json
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from storage import DATA_DIR, SETUPS_DIR, read_json, write_json
from pota_utils import normalize_us_park_reference
from tooltips import add_tooltip


class SetupFrame(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=14)
        self.app = app
        self.station_call = tk.StringVar(value="K4B")
        self.operator_call = tk.StringVar()
        self.grid_square = tk.StringVar()
        self.pota_enabled = tk.BooleanVar(value=False)
        self.my_park = tk.StringVar()
        self.setup_error_text = tk.StringVar()
        self._build()

    def _build(self):
        ttk.Label(self, text="K4B Special Event Logger", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        ttk.Label(self, text="Blind Equality Achievement Month — simple special-event logging with optional Parks on the Air support.", wraplength=720).pack(anchor="w", pady=(2, 14))

        box = ttk.LabelFrame(self, text="Station / Event Setup", padding=12)
        box.pack(fill="x")
        fields = [
            ("Special-event call sign", self.station_call, 0, 18),
            ("Operator call sign", self.operator_call, 1, 18),
            ("Grid square (optional)", self.grid_square, 2, 14),
        ]
        for label, var, row, width in fields:
            ttk.Label(box, text=label + ":", font=("Segoe UI", 9, "bold")).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=5)
            entry = ttk.Entry(box, textvariable=var, width=width)
            entry.grid(row=row, column=1, sticky="w", pady=5)
            if var is self.station_call:
                self.station_call_entry = entry

        style = ttk.Style(self)
        style.configure("Bold.TCheckbutton", font=("Segoe UI", 9, "bold"))
        self.pota_check = ttk.Checkbutton(box, text="POTA Activation", variable=self.pota_enabled, command=self._update_pota_state, style="Bold.TCheckbutton")
        self.pota_check.grid(row=3, column=0, sticky="w", pady=(8, 5))
        add_tooltip(self.pota_check, "Check this when K4B is being operated from a Parks on the Air activation. Leave it off for home or other non-POTA operation.")
        ttk.Label(box, text="POTA Park Reference:", font=("Segoe UI", 9, "bold")).grid(
            row=3, column=1, sticky="w", padx=(18, 8), pady=(8, 5)
        )
        self.my_park_entry = ttk.Entry(box, textvariable=self.my_park, width=16)
        self.my_park_entry.grid(row=3, column=2, sticky="w", padx=(8, 0), pady=(8, 5))
        add_tooltip(self.my_park_entry, "Enter the U.S. POTA Park Reference. You may type 2155, US2155, or US-2155; the logger stores it as US-2155 and exports it in MY_SIG_INFO.")
        self.my_park_entry.bind("<FocusOut>", self._normalize_park_focus_out, add="+")

        ttk.Label(box, text="When POTA is enabled, the logging screen also provides an optional Park 2 Park field for P2P contacts.", wraplength=680).grid(row=4, column=0, columnspan=3, sticky="w", pady=(4, 0))

        style.configure("Primary.TButton", font=("Segoe UI", 9, "bold"))
        buttons = ttk.Frame(self)
        buttons.pack(fill="x", pady=(14, 0))
        ttk.Button(buttons, text="Save Setup…", command=self.save_setup).pack(side="left")
        ttk.Button(buttons, text="Load Setup…", command=self.load_setup).pack(side="left", padx=(8, 0))
        ttk.Button(buttons, text="Open Data Folder", command=self.open_data_folder).pack(side="left", padx=(8, 0))
        ttk.Button(buttons, text="Help", command=lambda: self.app.show_context_help("setup")).pack(side="left", padx=(8, 0))
        ttk.Button(buttons, text="Guides", command=self.app.show_guides).pack(side="left", padx=(8, 0))
        ttk.Button(buttons, text="About…", command=self.app.show_about).pack(side="left", padx=(8, 0))
        ttk.Button(buttons, text="Logging", command=self.continue_to_logger, style="Primary.TButton").pack(side="right")
        ttk.Label(self, textvariable=self.setup_error_text).pack(fill="x", pady=(4, 0))
        self._update_pota_state()

    def _update_pota_state(self):
        self.my_park_entry.configure(state="normal" if self.pota_enabled.get() else "disabled")


    def _normalize_park_focus_out(self, _event=None):
        if not self.pota_enabled.get():
            return
        raw = self.my_park.get().strip()
        if not raw:
            return
        try:
            self.my_park.set(normalize_us_park_reference(raw))
        except ValueError:
            # Commit-time validation gives the operator the actual warning.
            pass

    @staticmethod
    def _canonical_grid(value):
        value = value.strip()
        if len(value) >= 2:
            value = value[:2].upper() + value[2:]
        if len(value) >= 6:
            value = value[:4] + value[4:6].lower() + value[6:]
        return value

    def collect_setup(self):
        return {
            "station_call": self.station_call.get().strip().upper(),
            "operator_call": self.operator_call.get().strip().upper(),
            "grid_square": self._canonical_grid(self.grid_square.get()),
            "activity_name": "K4B — Blind Equality Achievement Month",
            "contest_id": "",
            "pota_enabled": bool(self.pota_enabled.get()),
            "my_park": self.my_park.get().strip().upper(),
        }

    def suggested_setup_filename(self):
        op = self.operator_call.get().strip().upper()
        safe = "".join(ch for ch in op if ch.isalnum() or ch in "-_")
        return f"K4B_{safe}_Setup.json" if safe else "K4B_Setup.json"

    def save_setup(self):
        data = self.collect_setup()
        if data["pota_enabled"]:
            try:
                data["my_park"] = normalize_us_park_reference(data["my_park"])
            except ValueError as exc:
                messagebox.showwarning("POTA Park Reference", str(exc))
                self.my_park_entry.focus_set()
                return
            self.my_park.set(data["my_park"])
        path = filedialog.asksaveasfilename(
            title="Save K4B Setup",
            initialdir=SETUPS_DIR,
            initialfile=self.suggested_setup_filename(),
            defaultextension=".json",
            filetypes=[("K4B setup", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            write_json(path, data)
        except OSError as exc:
            messagebox.showerror("Save Setup", f"Could not save setup:\n{exc}")
            return
        self.app.setup_data = data
        self.app.remember_setup(self.app.setup_data)
        messagebox.showinfo("Save Setup", f"Station setup saved to:\n{path}")

    def load_setup(self):
        path = filedialog.askopenfilename(title="Load K4B Setup", initialdir=SETUPS_DIR, filetypes=[("K4B setup", "*.json"), ("All files", "*.*")])
        if not path:
            return
        try:
            data = read_json(path)
        except (OSError, json.JSONDecodeError) as exc:
            messagebox.showerror("Load Setup", f"Could not load setup:\n{exc}")
            return
        if not isinstance(data, dict):
            messagebox.showerror("Load Setup", "That file is not a valid K4B Logger setup.")
            return
        self.load_from_dict(data)
        self.app.setup_data = self.collect_setup()
        self.app.remember_setup(self.app.setup_data)

    def open_data_folder(self):
        try:
            if sys.platform == "win32":
                os.startfile(DATA_DIR)
            elif sys.platform == "darwin":
                os.system(f'open "{DATA_DIR}"')
            else:
                os.system(f'xdg-open "{DATA_DIR}"')
        except Exception as exc:
            messagebox.showerror("Open Data Folder", f"Could not open the data folder:\n{exc}")

    def continue_to_logger(self):
        self.setup_error_text.set("")
        data = self.collect_setup()
        if not data["station_call"]:
            self.setup_error_text.set("⚠ Please enter the K4B station call before continuing.")
            self.station_call_entry.focus_set(); return
        if data["pota_enabled"]:
            try:
                data["my_park"] = normalize_us_park_reference(data["my_park"])
            except ValueError as exc:
                self.setup_error_text.set(f"⚠ {exc}")
                self.my_park_entry.focus_set()
                try:
                    self.my_park_entry.selection_range(0, "end")
                except tk.TclError:
                    pass
                return
            self.my_park.set(data["my_park"])
        self.app.setup_data = data
        self.app.remember_setup(data)
        self.app.show_logger()

    def load_from_dict(self, data):
        self.station_call.set(data.get("station_call", "K4B") or "K4B")
        self.operator_call.set(data.get("operator_call", ""))
        self.grid_square.set(data.get("grid_square", ""))
        self.pota_enabled.set(bool(data.get("pota_enabled", False)))
        self.my_park.set(data.get("my_park", ""))
        self._update_pota_state()
