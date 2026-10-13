import tkinter as tk
from tkinter import ttk


class FileFrame(ttk.LabelFrame):
    def __init__(self, parent):
        super().__init__(parent, text="Input Files", padding=10)
        self._build()

    # --------------------------------------------------
    # BUILD
    # --------------------------------------------------
    def _build(self):

        # ---------- Folder ----------
        ttk.Label(self, text="Path to input file folder").grid(
            row=0, column=0, sticky="e", padx=5, pady=2
        )
        self.folder = ttk.Entry(self, width=40)
        self.folder.grid(row=0, column=1, columnspan=3, sticky="w")

        # ---------- OpenSMOKE input ----------
        ttk.Label(self, text="OpenSMOKE input file name").grid(
            row=1, column=0, sticky="e", padx=5, pady=2
        )
        self.osinputfile = ttk.Entry(self, width=40)
        self.osinputfile.grid(row=1, column=1, columnspan=3, sticky="w")
        self.osinputfile.insert(0, "input.dic")

        # ---------- Experimental data mode ----------
        ttk.Label(self, text="Experimental data input").grid(
            row=2, column=0, sticky="e", padx=5, pady=2
        )

        self.expdata_mode = tk.StringVar(value="file")

        ttk.Radiobutton(
            self, text="From file",
            variable=self.expdata_mode, value="file",
            command=self._toggle_expdata_mode
        ).grid(row=2, column=1, sticky="w")

        ttk.Radiobutton(
            self, text="Paste data",
            variable=self.expdata_mode, value="paste",
            command=self._toggle_expdata_mode
        ).grid(row=2, column=2, sticky="w")

        # ---------- FILE MODE ----------
        self.file_mode_frame = ttk.Frame(self)
        self.file_mode_frame.grid(row=3, column=0, columnspan=4, sticky="w")

        ttk.Label(
            self.file_mode_frame, text="Experimental data file name"
        ).grid(row=0, column=0, sticky="e", padx=5, pady=2)

        self.expdata = ttk.Entry(self.file_mode_frame, width=40)
        self.expdata.grid(row=0, column=1, sticky="w")
        self.expdata.insert(0, "expdata.txt")

        # ---------- PASTE MODE ----------
        self.paste_mode_frame = ttk.Frame(self)
        self.paste_mode_frame.grid(row=4, column=0, columnspan=4, sticky="w")
        self.paste_mode_frame.grid_remove()

        ttk.Label(
            self.paste_mode_frame,
            text="Paste experimental data (one value per row)"
        ).grid(row=0, column=0, columnspan=2, pady=(5, 2))

        ttk.Label(self.paste_mode_frame, text="x-data").grid(row=1, column=0)
        ttk.Label(self.paste_mode_frame, text="y-data").grid(row=1, column=1)

        self.xdata_text = tk.Text(self.paste_mode_frame, width=20, height=8)
        self.xdata_text.grid(row=2, column=0, padx=5)

        self.ydata_text = tk.Text(self.paste_mode_frame, width=20, height=8)
        self.ydata_text.grid(row=2, column=1, padx=5)

        # ---------- Source type ----------
        ttk.Label(self, text="Source type (exp data)").grid(
            row=5, column=0, sticky="e", padx=5, pady=2
        )

        self.srctype = ttk.Combobox(
            self,
            values=["reported", "digitized", "inferred", "calculated"],
            state="readonly",
            width=37
        )
        self.srctype.current(0)
        self.srctype.grid(row=5, column=1, columnspan=3, sticky="w")

        # ---------- Opt-in toggles: profiles and in-file uncertainty ----------
        # Both are OFF by default: nothing is read unless the box is ticked.
        self.profiles_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            self, text="Profiles", variable=self.profiles_var
        ).grid(row=6, column=0, sticky="e", padx=5, pady=2)
        ttk.Label(
            self, text="use @ListOfProfiles from the OS input file",
            foreground="#555"
        ).grid(row=6, column=1, columnspan=3, sticky="w")

        self.uncertainty_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            self, text="Uncertainty in file", variable=self.uncertainty_var
        ).grid(row=7, column=0, sticky="e", padx=5, pady=2)
        ttk.Label(
            self, text="read  _uncabs_<y>  / _uncrel_<y>  columns next to their y column",
            foreground="#555"
        ).grid(row=7, column=1, columnspan=3, sticky="w")

    # --------------------------------------------------
    # TOGGLE MODE
    # --------------------------------------------------
    def _toggle_expdata_mode(self):
        if self.expdata_mode.get() == "file":
            self.file_mode_frame.grid()
            self.paste_mode_frame.grid_remove()
        else:
            self.file_mode_frame.grid_remove()
            self.paste_mode_frame.grid()

    # --------------------------------------------------
    # GET DATA
    # --------------------------------------------------
    def get_data(self):

        data = {
            "folder": self.folder.get().strip(),
            "OS_input_file": self.osinputfile.get().strip(),
            "expdata_mode": self.expdata_mode.get(),   # "file" | "paste"
            "expdata_file": self.expdata.get().strip(),
            "x_data": None,
            "y_data": None,
            "srctype": self.srctype.get(),
            "profiles_enabled": self.profiles_var.get(),
            "uncertainty_in_file": self.uncertainty_var.get(),
        }

        # --- pasted data ---
        if data["expdata_mode"] == "paste":
            try:
                x_raw = self.xdata_text.get("1.0", "end").strip()
                y_raw = self.ydata_text.get("1.0", "end").strip()

                x = [float(v) for v in x_raw.replace(",", " ").split()]
                y = [float(v) for v in y_raw.replace(",", " ").split()]

                if len(x) != len(y):
                    raise ValueError("x-data and y-data must have same length")

                data["x_data"] = x
                data["y_data"] = y

            except Exception as e:
                raise ValueError(f"Invalid pasted experimental data: {e}")

        return data
