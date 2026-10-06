import os
import shutil
import sys
import tkinter as tk
from datetime import datetime, timezone
from pathlib import Path
from tkinter import ttk, messagebox, filedialog

from adif_export import write_adif
from adif_import import read_adif, record_to_qso
from pota_utils import normalize_park_reference
from storage import ARCHIVES_DIR, LOGS_DIR, EXPORTS_DIR, RECOVERY_FILE, AUTO_LOG_FILE, UI_PREFS_FILE, read_json, write_json
from tooltips import add_tooltip

BANDS = ("2190m", "630m", "160m", "80m", "60m", "40m", "30m", "20m", "17m", "15m", "12m", "10m", "6m", "2m", "1.25m", "70cm", "33cm", "23cm")
MODES = ("SSB", "CW", "FM", "AM", "FT8", "FT4", "RTTY", "PSK31", "JS8", "JT65", "JT9", "Q65", "MFSK", "DATA")
VOICE_MODES = {"SSB", "FM", "AM"}
THREE_DIGIT_RST_MODES = {"CW", "RTTY"}
SIGNAL_LEVEL_MODES = {"FT8", "FT4", "JS8", "JT65", "JT9", "Q65", "PSK31", "MFSK", "DATA"}


class LoggerFrame(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=12)
        self.app = app
        self.date_utc = tk.StringVar()
        self.time_utc = tk.StringVar()
        self.live_utc = tk.StringVar()
        self.call = tk.StringVar()
        self.band = tk.StringVar(value="40m")
        self.mode = tk.StringVar(value="SSB")
        self.frequency_mhz = tk.StringVar()
        self.rst_sent = tk.StringVar(value="59")
        self.rst_rcvd = tk.StringVar(value="59")
        self.rst_sent_label = tk.StringVar(value="Report Sent")
        self.rst_rcvd_label = tk.StringVar(value="Report Rcvd")
        self.their_park = tk.StringVar()
        self.grid = tk.StringVar()
        self.operator = tk.StringVar()
        self.notes = tk.StringVar()
        self.session_label = tk.StringVar()
        self.status = tk.StringVar()
        self.editing_index = None
        self.editing_pota_active = None
        self.editing_my_park = ""
        self.timestamp_manual = False
        self.qso_entry_started = False
        self.sort_column = "number"
        self.sort_reverse = False
        self._build()
        self._bind_timestamp_tracking()
        self._clear_timestamp_fields()
        self._update_live_clock()

    def _build(self):
        style = ttk.Style(self)
        style.configure("EntryHeader.TLabel", font=("Segoe UI", 9, "bold"))
        style.configure("Clock.TLabel", font=("Segoe UI", 9, "bold"), padding=(4, 1))
        style.configure("QSO.TLabelframe.Label", font=("Segoe UI", 10, "bold"))
        # Windows' native ttk theme may ignore Treeview heading background
        # colors. Clone the heading cell from the "clam" theme for this one
        # widget so the requested light-gray header is actually drawn, while
        # leaving the rest of the application on the normal Windows theme.
        heading_bg = "#d9d9d9"
        try:
            style.element_create("GeneralHeading.cell", "from", "clam", "Treeheading.cell")
        except tk.TclError:
            pass

        def replace_heading_cell(layout):
            result = []
            for name, opts in layout:
                name = "GeneralHeading.cell" if name == "Treeheading.cell" else name
                opts = dict(opts)
                if "children" in opts:
                    opts["children"] = replace_heading_cell(opts["children"])
                result.append((name, opts))
            return result

        try:
            style.layout(
                "General.Treeview.Heading",
                replace_heading_cell(style.layout("Treeview.Heading")),
            )
        except tk.TclError:
            pass
        style.configure(
            "General.Treeview.Heading",
            background=heading_bg,
            foreground="black",
            relief="raised",
        )
        style.map("General.Treeview.Heading", background=[("active", "#ececec")])
        style.configure("Primary.TButton", font=("Segoe UI", 9, "bold"))

        top = ttk.Frame(self)
        top.pack(fill="x", pady=(0, 8))
        self.setup_button = ttk.Button(top, text="← Station Setup", command=self.back_to_setup)
        self.setup_button.pack(side="left")
        ttk.Label(top, textvariable=self.session_label, font=("Segoe UI", 11, "bold")).pack(side="left", padx=(14, 0))

        actions = ttk.Frame(top)
        actions.pack(side="right")
        ttk.Button(actions, text="Help", command=lambda: self.app.show_context_help("logging")).pack(side="left")
        ttk.Button(actions, text="Guides", command=self.app.show_guides).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="Save Log…", command=self.save_log).pack(side="left")
        ttk.Button(actions, text="Load Log…", command=self.load_log).pack(side="left", padx=(8, 0))
        self.import_adif_button = ttk.Button(actions, text="Import ADIF…", command=self.import_adif)
        self.import_adif_button.pack(side="left", padx=(8, 0))
        add_tooltip(self.import_adif_button, "Adds QSOs from an ADIF file to the current K4B log without replacing the QSOs already loaded.")
        self.adif_button = ttk.Button(actions, text="Export ADIF…", command=self.export_adif)
        self.adif_button.pack(side="left", padx=(8, 0))
        add_tooltip(
            self.adif_button,
            "Creates an ADIF log file for importing QSOs into compatible logging programs and online logbooks. ADIF is also accepted for some contest submissions.",
        )
        self.open_exports_button = ttk.Button(actions, text="Open Exports Folder", command=self.open_exports_folder)
        self.open_exports_button.pack(side="left", padx=(8, 0))
        add_tooltip(
            self.open_exports_button,
            "Opens the folder containing exported ADIF files.",
        )

        entry = ttk.LabelFrame(self, text="Log QSO", padding=10, style="QSO.TLabelframe")
        entry.pack(fill="x", pady=8)

        def field(label, variable, column, width, widget="entry", values=None, label_var=None):
            label_kwargs = {"textvariable": label_var} if label_var is not None else {"text": label}
            ttk.Label(entry, style="EntryHeader.TLabel", anchor="center", **label_kwargs).grid(
                row=0, column=column, sticky="ew", padx=(0, 6)
            )
            if widget == "combo":
                control = ttk.Combobox(entry, textvariable=variable, values=values or (), width=width, state="normal")
            else:
                control = ttk.Entry(entry, textvariable=variable, width=width)
            control.grid(row=1, column=column, sticky="ew", padx=(0, 6), pady=(2, 0))
            return control

        # Keep the entire fast-entry line together. Every heading and control
        # uses the same two grid rows so nothing drops lower than its neighbor.
        self.date_entry = field("Date UTC", self.date_utc, 0, 10)
        self.time_entry = field("UTC", self.time_utc, 1, 6)

        ttk.Label(entry, textvariable=self.live_utc, style="EntryHeader.TLabel", anchor="center").grid(
            row=0, column=2, sticky="ew", padx=(0, 6)
        )
        self.now_button = ttk.Button(entry, text="Set Current UTC", command=self.set_now, width=16)
        self.now_button.grid(row=1, column=2, sticky="ew", padx=(0, 6), pady=(2, 0))
        add_tooltip(
            self.now_button,
            "Sets this QSO timestamp to the current UTC time. The live clock above continues to run independently.",
        )

        self.call_entry = field("Call Sign", self.call, 3, 11)
        self.band_combo = field("Band", self.band, 4, 6, widget="combo", values=BANDS)
        self.mode_combo = field("Mode", self.mode, 5, 6, widget="combo", values=MODES)
        self.freq_entry = field("Freq MHz", self.frequency_mhz, 6, 12)
        self.rst_sent_entry = field("Report Sent", self.rst_sent, 7, 13, label_var=self.rst_sent_label)
        self.rst_rcvd_entry = field("Report Rcvd", self.rst_rcvd, 8, 13, label_var=self.rst_rcvd_label)
        self.their_park_entry = field("Park 2 Park", self.their_park, 9, 13)
        self.grid_entry = field("Grid", self.grid, 10, 9)
        self.operator_entry = field("Operator", self.operator, 11, 11)
        add_tooltip(self.their_park_entry, "For a POTA park-to-park contact, enter the other activator’s Park Reference. You may type 2155, US2155, US-2155, CA0008, etc.; the logger inserts the dash. Leave blank for an ordinary contact.")
        self.their_park_entry.bind("<FocusOut>", self._normalize_p2p_focus_out, add="+")

        # Blank header cell keeps Log QSO aligned with the entry controls.
        ttk.Label(entry, text="", style="EntryHeader.TLabel").grid(row=0, column=12)
        self.log_button = ttk.Button(entry, text="Log QSO", command=self.log_or_update, width=10)
        self.log_button.grid(row=1, column=12, sticky="w", pady=(2, 0), padx=(0, 6))
        self.cancel_edit_button = ttk.Button(entry, text="Cancel Edit", command=self.cancel_edit, width=10)
        self.clear_entry_button = ttk.Button(entry, text="Clear Entry", command=self.clear_entry, width=10)
        self.clear_entry_button.grid(row=1, column=13, sticky="w", pady=(2, 0))
        add_tooltip(self.clear_entry_button, "Clears the current unfinished QSO entry without changing the log.")

        ttk.Label(entry, text="Notes:", style="EntryHeader.TLabel").grid(
            row=2, column=0, columnspan=14, sticky="w", pady=(10, 0)
        )
        self.notes_entry = ttk.Entry(entry, textvariable=self.notes)
        self.notes_entry.grid(row=3, column=0, columnspan=14, sticky="ew", pady=(2, 0))

        ttk.Label(
            entry,
            text="The station clock stays live. The QSO timestamp is captured when you begin typing the call sign.",
        ).grid(row=4, column=0, columnspan=14, sticky="w", pady=(8, 0))
        ttk.Label(entry, textvariable=self.status).grid(
            row=5, column=0, columnspan=14, sticky="w", pady=(4, 0)
        )
        entry.columnconfigure(12, weight=0)

        self.call_entry.bind("<KeyPress>", self._begin_qso_entry, add="+")
        self.call_entry.bind("<FocusOut>", self._call_focus_out, add="+")
        self.mode_combo.bind("<<ComboboxSelected>>", self._mode_changed, add="+")
        for widget in (
            self.date_entry,
            self.time_entry,
            self.call_entry,
            self.band_combo,
            self.mode_combo,
            self.freq_entry,
            self.rst_sent_entry,
            self.rst_rcvd_entry,
            self.their_park_entry,
            self.grid_entry,
            self.operator_entry,
            self.notes_entry,
        ):
            widget.bind("<Return>", self._enter_logs, add="+")

        table_wrap = ttk.Frame(self, padding=(8, 4, 8, 8))
        table_wrap.pack(fill="both", expand=True, pady=8)
        header = ttk.Frame(table_wrap)
        header.pack(fill="x", pady=(0, 6))
        ttk.Label(header, text="QSO Log", font=("Segoe UI", 10, "bold")).pack(side="left")
        ttk.Button(header, text="Delete Selected", command=self.delete_selected).pack(side="right")
        ttk.Button(header, text="Edit Selected", command=self.edit_selected).pack(side="right", padx=(0, 8))

        tf = ttk.Frame(table_wrap)
        tf.pack(fill="both", expand=True)
        cols = ("number", "date", "time", "call", "band", "mode", "freq", "sent", "rcvd", "pota", "park", "grid", "operator", "notes")
        self.tree = ttk.Treeview(
            tf, columns=cols, show="headings", selectmode="extended", style="General.Treeview"
        )
        self.tree_cols = cols
        self.headings = {
            "number": "#",
            "date": "Date UTC",
            "time": "UTC",
            "call": "Call",
            "band": "Band",
            "mode": "Mode",
            "freq": "Freq MHz",
            "sent": "Report Sent",
            "rcvd": "Report Rcvd",
            "pota": "POTA Park",
            "park": "Park 2 Park",
            "grid": "Grid",
            "operator": "Operator",
            "notes": "Notes",
        }
        widths = {
            "number": 38,
            "date": 80,
            "time": 48,
            "call": 82,
            "band": 54,
            "mode": 60,
            "freq": 70,
            "sent": 62,
            "rcvd": 62,
            "pota": 90,
            "park": 92,
            "grid": 62,
            "operator": 75,
            "notes": 150,
        }
        saved_widths = self._load_saved_column_widths()
        for c in cols:
            self.tree.heading(c, text=self.headings[c], anchor="w", command=lambda col=c: self.sort_by_column(col))
            width = saved_widths.get(c, widths[c])
            self.tree.column(c, width=width, minwidth=32, anchor="w", stretch=False)

        sb = ttk.Scrollbar(tf, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tf, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=sb.set, xscrollcommand=hsb.set)
        tf.rowconfigure(0, weight=1)
        tf.columnconfigure(0, weight=1)
        self.tree.grid(row=0, column=0, sticky="nsew")
        sb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        self.tree.bind("<Double-1>", lambda _e: self.edit_selected())

        bottom = ttk.Frame(self)
        bottom.pack(fill="x", pady=(0, 4))
        self.new_session_button = ttk.Button(
            bottom,
            text="New Session…",
            command=self.start_new_session,
            style="Primary.TButton",
        )
        self.new_session_button.pack(side="right", padx=(0, 8))
        add_tooltip(
            self.new_session_button,
            "Archives the current session, then starts a new empty log while keeping your station setup.",
        )

    def _load_saved_column_widths(self):
        try:
            if not UI_PREFS_FILE.exists():
                return {}
            prefs = read_json(UI_PREFS_FILE)
            widths = prefs.get("qso_table_column_widths", {}) if isinstance(prefs, dict) else {}
            clean = {}
            for key, value in widths.items():
                try:
                    width = int(value)
                except (TypeError, ValueError):
                    continue
                if 32 <= width <= 1000:
                    clean[key] = width
            return clean
        except Exception:
            return {}

    def save_ui_preferences(self):
        try:
            prefs = {}
            if UI_PREFS_FILE.exists():
                loaded = read_json(UI_PREFS_FILE)
                if isinstance(loaded, dict):
                    prefs.update(loaded)
            prefs["qso_table_column_widths"] = {
                c: int(self.tree.column(c, "width")) for c in self.tree_cols
            }
            write_json(UI_PREFS_FILE, prefs)
        except Exception:
            pass

    def _bind_timestamp_tracking(self):
        self.date_utc.trace_add("write", self._timestamp_edited)
        self.time_utc.trace_add("write", self._timestamp_edited)

    def _timestamp_edited(self, *_):
        if not getattr(self, "_setting_timestamp", False):
            self.timestamp_manual = True

    def _update_live_clock(self):
        self.live_utc.set(datetime.now(timezone.utc).strftime("UTC %H:%M:%S"))
        self.after(1000, self._update_live_clock)

    def _clear_timestamp_fields(self):
        self._setting_timestamp = True
        self.date_utc.set(datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        self.time_utc.set("")
        self._setting_timestamp = False
        self.timestamp_manual = False

    def set_now(self):
        now = datetime.now(timezone.utc)
        self._setting_timestamp = True
        self.date_utc.set(now.strftime("%Y-%m-%d"))
        self.time_utc.set(now.strftime("%H%M"))
        self._setting_timestamp = False
        self.timestamp_manual = False

    def _report_defaults_for_mode(self):
        mode = self.mode.get().strip().upper()
        if mode in VOICE_MODES:
            return "Report Sent", "Report Rcvd", "59", "59"
        if mode in THREE_DIGIT_RST_MODES:
            return "Report Sent", "Report Rcvd", "599", "599"
        if mode in SIGNAL_LEVEL_MODES:
            return "Report Sent", "Report Rcvd", "", ""
        return "Report Sent", "Report Rcvd", "", ""

    def _apply_mode_report_defaults(self, force=False):
        sent_label, rcvd_label, sent_default, rcvd_default = self._report_defaults_for_mode()
        self.rst_sent_label.set(sent_label)
        self.rst_rcvd_label.set(rcvd_label)
        if force and self.editing_index is None:
            self.rst_sent.set(sent_default)
            self.rst_rcvd.set(rcvd_default)

    def _mode_changed(self, _event=None):
        # A deliberate mode change starts with the conventional report form:
        # 59 for voice, 599 for CW/RTTY, and blank signed-report fields for
        # weak-signal/digital modes such as FT8.
        self._apply_mode_report_defaults(force=True)

    def _begin_qso_entry(self, event=None):
        if self.editing_index is not None or self.qso_entry_started:
            return
        if event is not None and not getattr(event, "char", ""):
            return
        if not self.timestamp_manual:
            self.set_now()
        self.qso_entry_started = True

    def _enter_logs(self, _event=None):
        self.log_or_update()
        return "break"

    def refresh_from_setup(self):
        s = self.app.setup_data or {}
        label = "K4B — Blind Equality Achievement Month"
        pota = f" — POTA {s.get('my_park', '')}" if s.get("pota_enabled") else ""
        self.session_label.set(f"{label}{pota}")
        self.their_park_entry.configure(state="normal" if s.get("pota_enabled") else "disabled")
        if not self.operator.get():
            self.operator.set(s.get("operator_call", ""))
        self.refresh_table()
        self.call_entry.focus_set()

    def back_to_setup(self):
        self.app.show_setup()

    @staticmethod
    def _valid_date(value):
        try:
            datetime.strptime(value, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    @staticmethod
    def _valid_time(value):
        return len(value) == 4 and value.isdigit() and 0 <= int(value[:2]) <= 23 and 0 <= int(value[2:]) <= 59

    def _normalize_p2p_focus_out(self, _event=None):
        raw = self.their_park.get().strip()
        if not raw:
            return
        try:
            self.their_park.set(normalize_park_reference(raw, default_prefix="US"))
        except ValueError:
            # Commit-time validation gives the actual warning.
            pass

    def _warn(self, msg, widget=None):
        self.status.set(f"⚠ {msg}")
        if widget:
            widget.focus_set()
            try:
                widget.selection_range(0, "end")
            except (tk.TclError, AttributeError):
                pass
        return False


    @staticmethod
    def _band_from_mhz(mhz):
        ranges = (
            (1.8, 2.0, "160m"), (3.5, 4.0, "80m"), (5.0, 5.5, "60m"),
            (7.0, 7.3, "40m"), (10.1, 10.15, "30m"), (14.0, 14.35, "20m"),
            (18.068, 18.168, "17m"), (21.0, 21.45, "15m"), (24.89, 24.99, "12m"),
            (28.0, 29.7, "10m"), (50.0, 54.0, "6m"), (144.0, 148.0, "2m"),
            (222.0, 225.0, "1.25m"), (420.0, 450.0, "70cm"), (902.0, 928.0, "33cm"),
            (1240.0, 1300.0, "23cm"),
        )
        for low, high, band in ranges:
            if low <= mhz <= high:
                return band
        return None

    def _validate(self):
        if not self._valid_date(self.date_utc.get().strip()):
            return self._warn("Enter the UTC date as YYYY-MM-DD.", self.date_entry)
        if not self._valid_time(self.time_utc.get().strip()):
            return self._warn("Enter UTC time as four digits, HHMM.", self.time_entry)
        call = self.call.get().strip().upper()
        if not call:
            return self._warn("Enter the station call sign.", self.call_entry)
        letters = sum(ch.isalpha() for ch in call)
        digits = sum(ch.isdigit() for ch in call)
        if len(call) < 3 or letters < 2 or digits < 1 or any(not (ch.isalnum() or ch == "/") for ch in call):
            messagebox.showwarning("Call Sign", "Please verify the call sign. It must be at least three characters, contain at least two letters and one number, and may use / for a portable or special suffix.")
            self.call_entry.focus_set()
            return False
        if not self.band.get().strip():
            return self._warn("Enter or select a band.", self.band_combo)
        if not self.mode.get().strip():
            return self._warn("Enter or select a mode.", self.mode_combo)
        freq = self.frequency_mhz.get().strip()
        if freq:
            try:
                value = float(freq)
                if value >= 1000:
                    value /= 1000.0
                if value <= 0:
                    raise ValueError
                self.frequency_mhz.set((f"{value:.6f}").rstrip("0").rstrip("."))
                derived_band = self._band_from_mhz(value)
                if derived_band:
                    self.band.set(derived_band)
            except ValueError:
                return self._warn("Frequency must be entered in MHz or kHz, for example 7.225 or 7225.", self.freq_entry)
        if (self.app.setup_data or {}).get("pota_enabled"):
            park = self.their_park.get().strip()
            if park:
                try:
                    park = normalize_park_reference(park, default_prefix="US")
                except ValueError as exc:
                    return self._warn(str(exc), self.their_park_entry)
                self.their_park.set(park)
        return True

    @staticmethod
    def _canonical_grid(value):
        """Return a Maidenhead locator with conventional letter case."""
        value = value.strip()
        if len(value) >= 2:
            value = value[:2].upper() + value[2:]
        if len(value) >= 6:
            value = value[:4] + value[4:6].lower() + value[6:]
        return value

    def _call_focus_out(self, _event=None):
        """Normalize the call, then show informational history if it was worked before."""
        call = self.call.get().strip().upper()
        self.call.set(call)
        self._show_previous_contacts()

    def _show_previous_contacts(self, _event=None):
        """Show informational history for this call in the currently loaded log."""
        if self.editing_index is not None:
            return
        call = self.call.get().strip().upper()
        if not call:
            return

        matches = [
            q for q in self.app.qsos
            if q.get("call", "").strip().upper() == call
        ]
        if not matches:
            return

        lines = []
        for q in matches:
            when = f"{q.get('date_utc', '')} {q.get('time_utc', '')} UTC".strip()
            details = [q.get("band", ""), q.get("mode", "")]
            freq = q.get("frequency_mhz", "").strip()
            if freq:
                details.append(f"{freq} MHz")
            details = [item for item in details if item]
            lines.append(f"{when} — " + ", ".join(details))

        messagebox.showinfo(
            f"Previous contacts — {call}",
            f"Previous contacts with {call} in the current log:\n\n"
            + "\n".join(lines)
            + "\n\nInformational only — press OK to continue entering this QSO.",
        )

    def _entry(self):
        setup = self.app.setup_data or {}
        if self.editing_index is not None and self.editing_pota_active is not None:
            pota_active = bool(self.editing_pota_active)
            my_park = self.editing_my_park.strip().upper() if pota_active else ""
        else:
            pota_active = bool(setup.get("pota_enabled"))
            my_park = setup.get("my_park", "").strip().upper() if pota_active else ""

        return {
            "date_utc": self.date_utc.get().strip(),
            "time_utc": self.time_utc.get().strip(),
            "call": self.call.get().strip().upper(),
            "band": self.band.get().strip(),
            "mode": self.mode.get().strip().upper(),
            "frequency_mhz": self.frequency_mhz.get().strip(),
            "rst_sent": self.rst_sent.get().strip(),
            "rst_rcvd": self.rst_rcvd.get().strip(),
            "pota_active": pota_active,
            "my_park": my_park,
            "their_park": self.their_park.get().strip().upper() if pota_active else "",
            "station_callsign": setup.get("station_call", "K4B").strip().upper(),
            "grid": self._canonical_grid(self.grid.get()),
            "operator": self.operator.get().strip().upper(),
            "notes": self.notes.get().strip(),
        }

    def log_or_update(self):
        if not self._validate():
            return
        qso = self._entry()
        if self.editing_index is None:
            self.app.qsos.append(qso)
        else:
            self.app.qsos[self.editing_index] = qso
        self.editing_index = None
        self.editing_pota_active = None
        self.editing_my_park = ""
        self.status.set("")
        self.log_button.config(text="Log QSO")
        self.cancel_edit_button.grid_remove()
        self.clear_entry_button.grid_configure(column=13)
        self._clear_next()
        self.refresh_table()
        self.autosave()

    def cancel_edit(self):
        self.editing_index = None
        self.editing_pota_active = None
        self.editing_my_park = ""
        self.status.set("")
        self.log_button.config(text="Log QSO")
        self.cancel_edit_button.grid_remove()
        self.clear_entry_button.grid_configure(column=13)
        self._clear_next()

    def clear_entry(self):
        """Clear the current entry form without changing any logged QSO."""
        self.editing_index = None
        self.editing_pota_active = None
        self.editing_my_park = ""
        self.status.set("")
        self.log_button.config(text="Log QSO")
        self.cancel_edit_button.grid_remove()
        self.clear_entry_button.grid_configure(column=13)
        self._clear_next()

    def _clear_next(self):
        self.call.set("")
        # Keep the last frequency in place for the next QSO. This saves retyping
        # when several contacts are made without changing frequency.
        self.their_park.set("")
        self.grid.set("")
        self.notes.set("")
        self._apply_mode_report_defaults(force=True)
        self._clear_timestamp_fields()
        self.qso_entry_started = False
        self.call_entry.focus_set()

    def _row(self, index, q):
        return (
            index + 1,
            q.get("date_utc", ""),
            q.get("time_utc", ""),
            q.get("call", ""),
            q.get("band", ""),
            q.get("mode", ""),
            q.get("frequency_mhz", ""),
            q.get("rst_sent", ""),
            q.get("rst_rcvd", ""),
            q.get("my_park", "") if q.get("pota_active", bool(q.get("my_park"))) else "",
            q.get("their_park", ""),
            q.get("grid", ""),
            q.get("operator", ""),
            q.get("notes", ""),
        )

    def refresh_table(self):
        selected_indexes = set()
        for iid in self.tree.selection():
            try:
                selected_indexes.add(int(iid))
            except ValueError:
                pass
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        rows = [(i, q) for i, q in enumerate(self.app.qsos)]
        keymap = {
            "number": lambda x: x[0],
            "date": lambda x: x[1].get("date_utc", ""),
            "time": lambda x: x[1].get("time_utc", ""),
            "call": lambda x: x[1].get("call", ""),
            "band": lambda x: x[1].get("band", ""),
            "mode": lambda x: x[1].get("mode", ""),
            "freq": lambda x: x[1].get("frequency_mhz", ""),
            "sent": lambda x: x[1].get("rst_sent", ""),
            "rcvd": lambda x: x[1].get("rst_rcvd", ""),
            "pota": lambda x: x[1].get("my_park", "") if x[1].get("pota_active", bool(x[1].get("my_park"))) else "",
            "park": lambda x: x[1].get("their_park", ""),
            "grid": lambda x: x[1].get("grid", ""),
            "operator": lambda x: x[1].get("operator", ""),
            "notes": lambda x: x[1].get("notes", ""),
        }
        rows.sort(key=keymap[self.sort_column], reverse=self.sort_reverse)
        for i, q in rows:
            self.tree.insert("", "end", iid=str(i), values=self._row(i, q))
        for iid in selected_indexes:
            if self.tree.exists(str(iid)):
                self.tree.selection_add(str(iid))
        for c in self.tree_cols:
            arrow = ""
            if c == self.sort_column:
                arrow = " ▼" if self.sort_reverse else " ▲"
            self.tree.heading(c, text=self.headings[c] + arrow, anchor="w", command=lambda col=c: self.sort_by_column(col))

    def sort_by_column(self, column):
        if self.sort_column == column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = column
            self.sort_reverse = False
        self.refresh_table()

    def edit_selected(self):
        sel = self.tree.selection()
        if len(sel) != 1:
            messagebox.showwarning("Edit QSO", "Select exactly one QSO to edit.")
            return
        i = int(sel[0])
        q = self.app.qsos[i]
        self.editing_index = i
        self._setting_timestamp = True
        self.date_utc.set(q.get("date_utc", ""))
        self.time_utc.set(q.get("time_utc", ""))
        self._setting_timestamp = False
        self.timestamp_manual = True
        self.qso_entry_started = True
        self.call.set(q.get("call", ""))
        self.band.set(q.get("band", ""))
        self.mode.set(q.get("mode", ""))
        self._apply_mode_report_defaults(force=False)
        self.frequency_mhz.set(q.get("frequency_mhz", ""))
        self.rst_sent.set(q.get("rst_sent", ""))
        self.rst_rcvd.set(q.get("rst_rcvd", ""))
        self.editing_pota_active = q.get("pota_active", bool(q.get("my_park")))
        self.editing_my_park = q.get("my_park", "")
        self.their_park.set(q.get("their_park", ""))
        self.grid.set(self._canonical_grid(q.get("grid", "")))
        self.operator.set(q.get("operator", ""))
        self.notes.set(q.get("notes", ""))
        self.log_button.config(text="Update QSO")
        self.cancel_edit_button.grid(row=1, column=13, sticky="w", pady=(2, 0), padx=(0, 6))
        self.clear_entry_button.grid_configure(column=14)
        self.status.set(f"Editing QSO #{i + 1}. Press Enter or Update QSO to save.")
        self.call_entry.focus_set()

    def delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Delete QSO", "Select one or more QSOs to delete.")
            return
        count = len(sel)
        if not messagebox.askyesno("Delete QSO", f"Delete the {count} selected QSO{'s' if count != 1 else ''}?"):
            return
        for i in sorted((int(x) for x in sel), reverse=True):
            del self.app.qsos[i]
        self.editing_index = None
        self.status.set("")
        self.log_button.config(text="Log QSO")
        self.refresh_table()
        self.autosave()

    def _payload(self):
        return {
            "version": 3,
            "setup": self.app.setup_data,
            "qsos": self.app.qsos,
            "log_path": str(self.app.log_path) if self.app.log_path else "",
        }

    def autosave(self):
        payload = self._payload()
        try:
            write_json(RECOVERY_FILE, payload)
        except OSError:
            pass
        try:
            write_json(AUTO_LOG_FILE, payload)
        except OSError:
            pass
        if self.app.log_path:
            try:
                write_json(self.app.log_path, payload)
            except OSError as exc:
                messagebox.showerror("Autosave", f"The QSO is in memory, but the selected log file could not be saved:\n{exc}")

    def save_log(self):
        initial = "K4B_log.json"
        path = filedialog.asksaveasfilename(
            initialdir=LOGS_DIR,
            initialfile=initial,
            defaultextension=".json",
            filetypes=[("K4B Logger files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        write_json(path, self._payload())
        self.app.log_path = Path(path)
        self.autosave()
        self.app.update_title()

    def load_log(self):
        path = filedialog.askopenfilename(
            initialdir=LOGS_DIR,
            filetypes=[("K4B Logger files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            data = read_json(path)
        except Exception as exc:
            messagebox.showerror("Load Log", f"Could not load that log:\n{exc}")
            return
        self.app.setup_data = data.get("setup", {})
        self.app.qsos = list(data.get("qsos", []))
        self.app.log_path = Path(path)
        self.app.setup_frame.load_from_dict(self.app.setup_data)
        self.app.remember_setup(self.app.setup_data)
        self.refresh_from_setup()
        self.autosave()
        self.app.update_title()

    def _archive_current_session(self):
        """Archive the whole current session before clearing it."""
        setup = dict(self.app.setup_data or {})
        qsos = list(self.app.qsos)
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%SZ")
        final_dir = ARCHIVES_DIR / stamp
        counter = 2
        while final_dir.exists():
            final_dir = ARCHIVES_DIR / f"{stamp}_{counter}"
            counter += 1

        temp_dir = ARCHIVES_DIR / f".{final_dir.name}.creating"
        try:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            temp_dir.mkdir(parents=True, exist_ok=False)
            write_json(temp_dir / "K4B_session.json", self._payload())
            write_adif(temp_dir / "K4B_log.adi", setup, qsos)
            info = (
                "K4B Special Event Logger archived log\n"
                f"Archived UTC: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}\n"
                "Logger version: 2.0.4\n"
                f"Station call: {setup.get('station_call', '')}\n"
                f"Default operator: {setup.get('operator_call', '')}\n"
                f"POTA enabled: {setup.get('pota_enabled', False)}\n"
                f"My park: {setup.get('my_park', '')}\n"
                f"QSO count: {len(qsos)}\n"
                "\nThe files in this folder were generated together immediately before "
                "the logger started a new session.\n"
            )
            (temp_dir / "archive_info.txt").write_text(info, encoding="utf-8")
            temp_dir.rename(final_dir)
            return final_dir
        except Exception as exc:
            try:
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)
            except OSError:
                pass
            messagebox.showerror(
                "New Session",
                "The current session could not be archived, so a new session was NOT started.\n\n"
                f"{exc}",
            )
            return None

    def start_new_session(self):
        if not self.app.qsos:
            if not messagebox.askyesno(
                "Start New Session",
                "There are no QSOs in the current session. Start a fresh session and keep the current station setup?",
            ):
                return False
            archive_dir = None
        else:
            if not messagebox.askyesno(
                "Start New Session",
                "Start a new logging session?\n\n"
                "The current session will first be archived as JSON, ADIF, and archive information files. "
                "Your station setup will be kept.",
            ):
                return False
            archive_dir = self._archive_current_session()
            if archive_dir is None:
                return False

        self.app.qsos = []
        self.app.log_path = None
        self.editing_index = None
        self.editing_pota_active = None
        self.editing_my_park = ""
        self.status.set("")
        self.log_button.config(text="Log QSO")
        self.call.set("")
        self.frequency_mhz.set("")
        self.their_park.set("")
        self.grid.set("")
        self.notes.set("")
        self.operator.set((self.app.setup_data or {}).get("operator_call", ""))
        self._apply_mode_report_defaults(force=True)
        self._clear_timestamp_fields()
        self.qso_entry_started = False
        self.refresh_table()
        self.autosave()
        self.app.update_title()
        self.call_entry.focus_set()

        if archive_dir is not None:
            messagebox.showinfo(
                "New Session",
                "The previous session was archived successfully.\n\n"
                f"Archive:\n{archive_dir}\n\nA new empty log is ready, and your station setup was kept.",
            )
        return True

    def import_adif(self):
        path = filedialog.askopenfilename(
            title="Import ADIF into K4B Log",
            initialdir=LOGS_DIR,
            filetypes=[("ADIF files", "*.adi *.adif"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            records = read_adif(path)
        except OSError as exc:
            messagebox.showerror("Import ADIF", f"Could not read the ADIF file:\n{exc}")
            return

        imported = []
        skipped = 0
        station_calls = set()
        parks = set()
        for record in records:
            qso = record_to_qso(record)
            if qso is None:
                skipped += 1
                continue
            if qso.get("station_callsign"):
                station_calls.add(qso["station_callsign"])
            if qso.get("my_park"):
                parks.add(qso["my_park"])
            imported.append(qso)

        if not imported:
            messagebox.showwarning("Import ADIF", "No usable QSO records were found in that ADIF file.")
            return

        current_station = (self.app.setup_data or {}).get("station_call", "K4B").strip().upper()
        other_calls = sorted(call for call in station_calls if call and call != current_station)
        if other_calls:
            shown = ", ".join(other_calls[:6])
            if len(other_calls) > 6:
                shown += ", …"
            if not messagebox.askyesno(
                "Import ADIF",
                f"This ADIF contains STATION_CALLSIGN value(s) different from {current_station}:\n\n{shown}\n\nImport these QSOs anyway?",
            ):
                return

        self.app.qsos.extend(imported)
        self.refresh_table()
        self.autosave()
        details = [f"Imported {len(imported)} QSO{'s' if len(imported) != 1 else ''} into the current log."]
        if skipped:
            details.append(f"Skipped {skipped} incomplete record{'s' if skipped != 1 else ''}.")
        if parks:
            details.append("POTA Park Reference(s) preserved per QSO: " + ", ".join(sorted(parks)))
        details.append("Existing QSOs were kept; the import was appended to the current log.")
        messagebox.showinfo("Import ADIF", "\n\n".join(details))

    def open_exports_folder(self):
        try:
            EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
            if sys.platform == "win32":
                os.startfile(EXPORTS_DIR)
            elif sys.platform == "darwin":
                os.system(f'open "{EXPORTS_DIR}"')
            else:
                os.system(f'xdg-open "{EXPORTS_DIR}"')
        except Exception as exc:
            messagebox.showerror("Open Exports Folder", f"Could not open the exports folder:\n{exc}")

    def export_adif(self):
        if not self.app.qsos:
            messagebox.showwarning("Export ADIF", "There are no QSOs to export.")
            return
        base = "K4B"
        path = filedialog.asksaveasfilename(
            initialdir=EXPORTS_DIR,
            initialfile=base + ".adi",
            defaultextension=".adi",
            filetypes=[("ADIF files", "*.adi"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            write_adif(path, self.app.setup_data or {}, self.app.qsos)
        except OSError as exc:
            messagebox.showerror("Export ADIF", f"Could not write the ADIF file:\n{exc}")
            return
        messagebox.showinfo("Export ADIF", f"ADIF exported successfully:\n{path}")

