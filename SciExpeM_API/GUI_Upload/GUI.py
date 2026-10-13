"""SciExpeM experiment upload front-end.

User & Pw are required on first upload of the GUI session, memorized afterwards.
"""

import os
import sys

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import tkinter.font as tkfont

# Bump every stock Tk named font by this factor (the default ~9-10pt is too small).
FONT_SCALE = float(os.environ.get("SCIEXPEM_GUI_FONT_SCALE", "1.35"))



from SciExpeM_API.Utility import extract_data
from Frames.FileFrame import FileFrame
from Frames.PaperFrame import PaperFrame
from Frames.OpCondFrame import OpCondFrame
from Frames.MeasurementTypeFrame import MeasurementTypeFrame

OFFLINE_TESTMODE = os.environ.get("SCIEXPEM_GUI_OFFLINE", "") not in ("", "0", "false", "False")

SCIEXPEM_USER = os.environ.get("SCIEXPEM_USER", "")
SCIEXPEM_PASSWORD = os.environ.get("SCIEXPEM_PASSWORD", "")
SCIEXPEM_PORT = int(os.environ.get("SCIEXPEM_PORT", "8080"))
SCIEXPEM_SECURE = os.environ.get("SCIEXPEM_SECURE", "") not in ("", "0", "false", "False")

# populated lazily by App._get_client() on the first upload
my_sciexpem = None


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SciExpeM experiment upload")
        self.resizable(False, False)
        self._enlarge_fonts(FONT_SCALE)

        main_frame = ttk.Frame(self)
        main_frame.pack(padx=10, pady=10, fill="both", expand=True)
        for col in range(2):
            main_frame.columnconfigure(col, weight=1, uniform="col")
        for row in range(2):
            main_frame.rowconfigure(row, weight=1, uniform="row")

        # The four panels stay independent: each represents a different thing and
        # exposes a single get_data() -> dict.  Assembled "like a book":
        # upper-left, lower-left, upper-right, lower-right.
        self.paper_frame = PaperFrame(main_frame)
        self.paper_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        self.measurement_frame = MeasurementTypeFrame(main_frame)
        self.measurement_frame.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")

        self.file_frame = FileFrame(main_frame)
        self.file_frame.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")

        self.opcond_frame = OpCondFrame(main_frame, file_frame=self.file_frame,
                                        measurement_frame=self.measurement_frame)
        self.opcond_frame.grid(row=1, column=1, padx=5, pady=5, sticky="nsew")

        ttk.Button(main_frame, text="Print data on screen",
                   command=self.print_data).grid(row=2, column=0, columnspan=2,
                                                 pady=10, sticky="ew")
        upload_btn = ttk.Button(main_frame, text="Upload experiment",
                                command=self.upload_experiment)
        upload_btn.grid(row=3, column=0, columnspan=2, pady=10, sticky="ew")
        if OFFLINE_TESTMODE:
            upload_btn.state(["disabled"])

    # ------------------------------------------------------------------ #
    def _enlarge_fonts(self, scale):
        if scale == 1.0:
            return
        for name in ("TkDefaultFont", "TkTextFont", "TkFixedFont", "TkMenuFont",
                     "TkHeadingFont", "TkCaptionFont", "TkSmallCaptionFont",
                     "TkIconFont", "TkTooltipFont"):
            try:
                font = tkfont.nametofont(name)
            except tk.TclError:
                continue
            size = font.cget("size")
            if size:  # Tk sizes are pt (>0) or px (<0); scaling keeps the sign
                font.configure(size=int(round(size * scale)))
        try:
            ttk.Style(self).configure(".", font="TkDefaultFont")
        except tk.TclError:
            pass

    def _frame_data(self):
        return (self.paper_frame.get_data(),
                self.file_frame.get_data(),
                self.measurement_frame.get_data(),
                self.opcond_frame.get_data())

    def _get_client(self):
        """Connect to SciExpeM on first use; cache the singleton."""
        global my_sciexpem
        if my_sciexpem is not None:
            return my_sciexpem

        user = SCIEXPEM_USER or simpledialog.askstring(
            "SciExpeM login", "Username:", parent=self)
        if not user:
            return None
        password = SCIEXPEM_PASSWORD or simpledialog.askstring(
            "SciExpeM login", "Password for {}:".format(user), parent=self, show="*")
        if not password:
            return None

        try:
            from SciExpeM_API.SciExpeM import SciExpeM 
            # TODO when site is fixed, remove port/secure from here
            my_sciexpem = SciExpeM(username=user, password=password,
                                   port=SCIEXPEM_PORT, secure=SCIEXPEM_SECURE)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Login failed", str(exc))
            print("Login failed:", repr(exc))
            return None
        return my_sciexpem

    # 'Print data on screen' -- dump every panel, no network
    def print_data(self):
        try:
            paper, files, measure, opcond = self._frame_data()
        except Exception as exc:  # noqa: BLE001 - bad free-text field, tell the user
            messagebox.showerror("Invalid input", str(exc))
            return
        print("=== PAPER ==="); print(paper)
        print("=== FILE ==="); print(files)
        print("=== EXPERIMENT TYPE ==="); print(measure)
        print("=== OPERATIVE CONDITIONS ==="); print(opcond)
        if files.get("profiles_enabled"):
            try:
                ed = extract_data
                _, extrainfo = ed.process_osinput(files["folder"], files["OS_input_file"],
                                                  profiles=True, flameinfo=True)
                print("=== List of Profiles ===")
                print((extrainfo.get("profileinfo") or {}).get("csv_paths", []))
            except Exception as exc:  # noqa: BLE001
                print("could not read profile list:", exc)
        print("=== END OF DATA ===")

    # 'Upload experiment' -- build via experiment_assembler and insert
    def upload_experiment(self):
        if OFFLINE_TESTMODE:
            messagebox.showinfo("Offline", "OFFLINE_TESTMODE is on -- upload disabled.")
            return

        client = self._get_client()
        if client is None:
            return

        try:
            import experiment_assembler as assembler
            paper, files, measure, opcond = self._frame_data()
            experiment = assembler.build_experiment(
                paper, files, measure, opcond, client,
                comment=(paper.get("comments") or None),
            )
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Build failed", str(exc))
            print("Build failed:", repr(exc))
            return

        print("=== SERIALIZED EXPERIMENT ===")
        print(experiment.serialize())
        try:
            client.insertElement(experiment, verbose=True)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Upload failed", str(exc))
            print("Upload failed:", repr(exc))
            return
        messagebox.showinfo("Upload", "Upload done.")
        print("Upload done")


if __name__ == "__main__":
    App().mainloop()
