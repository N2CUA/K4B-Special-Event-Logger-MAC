import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox

from logger_screen import LoggerFrame
from setup_screen import SetupFrame
from storage import (
    CLEAN_SHUTDOWN_FILE, CURRENT_SETUP_FILE, LEGACY_CURRENT_SETUP_FILE, RECOVERY_FILE, AUTO_LOG_FILE, SETUPS_DIR,
    read_json, write_json,
)


APP_TITLE = "K4B Special Event Logger 2.0.4"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("820x410")
        self.minsize(760, 390)
        self.setup_data = {}
        self.qsos = []
        self.log_path = None
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True)
        self.setup_frame = SetupFrame(container, self)
        self.logger_frame = LoggerFrame(container, self)
        # A clean-shutdown marker distinguishes a real interrupted session from
        # an intentionally retained recovery snapshot. Remove it immediately so
        # a crash during this run will be detected next time.
        self.previous_shutdown_was_clean = CLEAN_SHUTDOWN_FILE.exists()
        try:
            if CLEAN_SHUTDOWN_FILE.exists():
                CLEAN_SHUTDOWN_FILE.unlink()
        except OSError:
            pass
        self.load_current_setup()
        if self.previous_shutdown_was_clean:
            self.load_working_log()
        self.show_setup()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.after(100, self.offer_recovery)


    def load_current_setup(self):
        """Restore the last-used setup, with a named-setup fallback."""
        candidates = []
        if CURRENT_SETUP_FILE.exists():
            candidates.append(CURRENT_SETUP_FILE)
        # v2.0.0 used a hidden quick-start file in the main data folder.
        # Read it once as a migration fallback, then recreate the visible
        # automatic setup file in Setups on the next successful remember.
        if LEGACY_CURRENT_SETUP_FILE.exists():
            candidates.append(LEGACY_CURRENT_SETUP_FILE)
        try:
            for path in sorted(SETUPS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
                if path not in candidates:
                    candidates.append(path)
        except OSError:
            pass

        for path in candidates:
            try:
                data = read_json(path)
            except Exception:
                continue
            if not isinstance(data, dict) or not data.get("station_call", "").strip():
                continue
            self.setup_data = data
            self.setup_frame.load_from_dict(data)
            # Repair/recreate the quick-start copy if the fallback was used.
            if path != CURRENT_SETUP_FILE:
                self.remember_setup(data)
            return

    def load_working_log(self):
        """Silently restore the last automatic working log after a normal close.

        v2.0.1 kept a recovery snapshot but did not restore it after a clean close.
        Use that file once as a migration fallback when the new automatic log
        file does not exist yet.
        """
        source = AUTO_LOG_FILE if AUTO_LOG_FILE.exists() else RECOVERY_FILE
        if not source.exists():
            return
        try:
            data = read_json(source)
        except Exception:
            return
        if not isinstance(data, dict):
            return

        setup = data.get("setup", {})
        qsos = data.get("qsos", [])
        if isinstance(setup, dict) and setup.get("station_call", "").strip():
            self.setup_data = setup
            self.setup_frame.load_from_dict(setup)
            self.remember_setup(setup)
        if isinstance(qsos, list):
            self.qsos = qsos

        saved_path = str(data.get("log_path", "") or "").strip()
        if saved_path:
            candidate = Path(saved_path)
            if candidate.exists():
                self.log_path = candidate

        if source != AUTO_LOG_FILE:
            try:
                write_json(AUTO_LOG_FILE, data)
            except OSError:
                pass

    def remember_setup(self, data=None):
        """Remember the active setup so normal startup does not require Load Setup."""
        data = dict(data if data is not None else (self.setup_data or {}))
        if not data.get("station_call", "").strip():
            return
        try:
            write_json(CURRENT_SETUP_FILE, data)
            # Once the new visible auto-setup copy is safely written, the old
            # hidden v2.0.0 quick-start file is no longer needed.
            if LEGACY_CURRENT_SETUP_FILE.exists():
                try:
                    LEGACY_CURRENT_SETUP_FILE.unlink()
                except OSError:
                    pass
        except OSError:
            pass

    def on_close(self):
        # Preserve the visible setup even when the user closes from the setup screen.
        try:
            visible_setup = self.setup_frame.collect_setup()
            if visible_setup.get("station_call", "").strip():
                self.setup_data = visible_setup
                self.remember_setup(visible_setup)
        except Exception:
            pass
        # Persist the working log even if the operator never clicked Save Log.
        try:
            self.logger_frame.autosave()
        except Exception:
            pass
        # Preserve user-adjusted QSO table column widths between runs.
        try:
            self.logger_frame.save_ui_preferences()
        except Exception:
            pass
        # Keep recovery.json as a last-known-good safety snapshot, but record
        # that this session ended normally so it will not trigger recovery.
        try:
            CLEAN_SHUTDOWN_FILE.write_text("clean\n", encoding="utf-8")
        except OSError:
            pass
        self.destroy()

    def show_setup(self):
        self.logger_frame.pack_forget()
        self.setup_frame.pack(fill="both", expand=True)
        self.update_idletasks()
        desired_w = max(760, self.setup_frame.winfo_reqwidth() + 24)
        desired_h = max(410, self.setup_frame.winfo_reqheight() + 24)
        self.minsize(760, 390)
        self.geometry(f"{desired_w}x{desired_h}")

    def show_logger(self):
        self.setup_frame.pack_forget()
        self.geometry("1240x720")
        self.minsize(1080, 600)
        self.logger_frame.pack(fill="both", expand=True)
        self.logger_frame.refresh_from_setup()
        self.update_title()

    def update_title(self):
        self.title(APP_TITLE)

    def show_text_dialog(self, title, text, parent=None, width=84, height=27):
        owner = parent if parent is not None else self
        dialog = tk.Toplevel(owner)
        dialog.title(title)
        dialog.transient(owner)
        dialog.resizable(True, True)
        body = ttk.Frame(dialog, padding=12)
        body.pack(fill="both", expand=True)
        viewer = tk.Text(body, wrap="word", width=width, height=height, padx=8, pady=8)
        scroll = ttk.Scrollbar(body, orient="vertical", command=viewer.yview)
        viewer.configure(yscrollcommand=scroll.set)
        viewer.insert("1.0", text)
        viewer.configure(state="disabled")
        viewer.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        ttk.Button(dialog, text="Close", command=dialog.destroy).pack(pady=(0, 10))
        return dialog

    def show_context_help(self, context):
        if context == "setup":
            text = (
                "K4B LOGGER — SETUP HELP\n\n"
                "Special-event call sign — Defaults to K4B.\n\n"
                "Operator call sign — The individual operator. This is especially important for a club/group POTA activation.\n\n"
                "Grid square — Optional station Maidenhead grid.\n\n"
                "POTA Activation — Check only when K4B is operating from a Parks on the Air activation.\n\n"
                "POTA Park Reference — The activation park. You may type 2155, US2155, or US-2155; the logger stores the official US-2155 form and exports it in MY_SIG / MY_SIG_INFO.\n\n"
                "Logging — Opens the K4B QSO screen using this setup."
            )
            self.show_text_dialog("K4B Setup Help", text, width=82, height=22)
        else:
            text = (
                "K4B LOGGER — LOGGING HELP\n\n"
                "Date UTC / UTC — Captured when callsign entry begins and remains editable.\n\n"
                "Call / Band / Mode / Frequency — Core contact information. Frequency accepts MHz or kHz, such as 7.225 or 7225.\n\n"
                "RST / Report — Signal reports. Voice defaults to 59 and CW/RTTY to 599; you may change the report.\n\n"
                "Park 2 Park — Enabled only when this K4B setup is a POTA activation. Enter the other activator's Park Reference for a P2P contact; otherwise leave it blank. The logger can insert the dash for forms such as US2155.\n\n"
                "Grid / Operator / Notes — Optional contact details.\n\n"
                "Import ADIF — Appends QSOs from another ADIF file to the current log, useful for combining K4B operator logs.\n\n"
                "ADIF Export — POTA status is stored per QSO, so one log may safely contain both POTA and non-POTA contacts. POTA QSOs include MY_SIG/MY_SIG_INFO and, for P2P QSOs, SIG/SIG_INFO."
            )
            self.show_text_dialog("K4B Logging Help", text, width=84, height=26)

    def show_guides(self):
        text = (
            "K4B SPECIAL EVENT QUICK GUIDE\n\n"
            "Log each contact as it actually happened: UTC date/time, worked call, band and mode, then signal reports and any useful optional information.\n\n"
            "POTA is optional. If K4B is operating from a park, enable POTA in Station Setup and enter the POTA Park Reference. For park-to-park contacts, enter the other activator's reference in Park 2 Park. Each QSO remembers whether it was a POTA contact and which park was active, so one working log may contain both POTA and non-POTA contacts.\n\n"
            "POTA does not require a formal on-air exchange. Signal reports and park references are useful operating information, but the logger does not pretend they are a mandatory contest exchange.\n\n"
            "For a club/group POTA activation, K4B is the station callsign and the individual operator belongs in the Operator field.\n\n"
            "Import ADIF can append another operator's K4B QSOs to the current log. Export ADIF for interchange and POTA submission. Always spot-check the exported file before uploading it."
        )
        self.show_text_dialog("K4B Quick Guide", text, width=84, height=24)

    def show_about(self):
        dialog = tk.Toplevel(self)
        dialog.title("About K4B Special Event Logger")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)
        body = ttk.Frame(dialog, padding=18)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text=APP_TITLE, font=("Segoe UI", 13, "bold")).pack(anchor="w")
        ttk.Label(
            body,
            text=(
                "Copyright © 2026 Randy Swart - N2CUA\n"
                "Developed by Randy Swart with assistance from OpenAI ChatGPT.\n\n"
                "This program is free software licensed under the GNU General Public License, version 3 (GPLv3). "
                "The complete license text is included as LICENSE.txt."
            ),
            justify="left",
            wraplength=510,
        ).pack(anchor="w", pady=(10, 14))
        buttons = ttk.Frame(body)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="View GPLv3 License", command=lambda: self.show_license(dialog)).pack(side="left")
        ttk.Button(buttons, text="Close", command=dialog.destroy).pack(side="right")

    def show_license(self, parent):
        try:
            text = Path(__file__).with_name("LICENSE.txt").read_text(encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("GPLv3 License", f"Could not open LICENSE.txt:\n{exc}")
            return
        window = tk.Toplevel(parent)
        window.title("GNU General Public License, Version 3")
        window.transient(parent)
        window.grab_set()
        window.geometry("760x620")
        frame = ttk.Frame(window, padding=10)
        frame.pack(fill="both", expand=True)
        scroll = ttk.Scrollbar(frame, orient="vertical")
        viewer = tk.Text(frame, wrap="word", yscrollcommand=scroll.set)
        scroll.configure(command=viewer.yview)
        viewer.insert("1.0", text)
        viewer.configure(state="disabled")
        viewer.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        def close():
            window.grab_release()
            window.destroy()
            if parent.winfo_exists():
                parent.grab_set()
                parent.focus_set()

        window.protocol("WM_DELETE_WINDOW", close)
        ttk.Button(frame, text="Close", command=close).pack(side="bottom", anchor="e", pady=(8, 0))
        window.focus_set()

    def offer_recovery(self):
        # A retained recovery snapshot is only offered after an unclean exit.
        if self.previous_shutdown_was_clean:
            return
        if not RECOVERY_FILE.exists():
            return
        try:
            data = read_json(RECOVERY_FILE)
        except Exception:
            return
        if not data.get("qsos"):
            return
        if messagebox.askyesno("Recovery Log", "A recovery log from a previous session was found. Load it?"):
            self.setup_data = data.get("setup", {})
            self.qsos = list(data.get("qsos", []))
            self.setup_frame.load_from_dict(self.setup_data)
            self.remember_setup(self.setup_data)
            # Recovery restores the data but intentionally leaves the operator
            # on Station Setup. The operator enters the logger normally.
            self.show_setup()


if __name__ == "__main__":
    App().mainloop()
