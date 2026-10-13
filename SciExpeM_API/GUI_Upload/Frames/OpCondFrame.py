import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import tkinter as tk
from tkinter import ttk, messagebox

from SciExpeM_API.Utility import extract_data as ed
import os_conditions as osc


class OpCondFrame(ttk.LabelFrame):
    def __init__(self, parent, file_frame, measurement_frame):
        super().__init__(parent, text="Operating Conditions", padding=10)
        self.file_frame = file_frame
        self.measurement_frame = measurement_frame
        self._build()

    def _build(self):
        labels = ["Temperature", "Pressure", "phi"]
        display_labels = {
            "Temperature": "Temperature",
            "Pressure": "Pressure",
            "phi": "phi (100 = Pyro)"
        }

        self.entries = {}
        self.units = {}

        ttk.Label(self, text="").grid(row=0, column=0, padx=2)
        ttk.Label(self, text="INF").grid(row=0, column=1, padx=2)
        ttk.Label(self, text="SUP").grid(row=0, column=2, padx=2)
        ttk.Label(self, text="Unit").grid(row=0, column=3, padx=2)

        for i, label in enumerate(labels):
            row_idx = i + 1
            ttk.Label(self, text=display_labels[label]).grid(
                row=row_idx, column=0, sticky="e", padx=5, pady=2)

            entry_inf = ttk.Entry(self, width=15)
            entry_inf.grid(row=row_idx, column=1, sticky="w", padx=2, pady=2)

            entry_sup = ttk.Entry(self, width=15)
            entry_sup.grid(row=row_idx, column=2, sticky="w", padx=2, pady=2)

            if label == "Temperature":
                unit_cb = ttk.Combobox(self, values=["K"], state="readonly", width=5)
                unit_cb.current(0)
                unit_cb.grid(row=row_idx, column=3, sticky="w", padx=2, pady=2)
            elif label == "Pressure":
                unit_cb = ttk.Combobox(
                    self, values=["bar", "Pa", "kPa", "MPa", "atm"],
                    state="readonly", width=5)
                unit_cb.current(0)
                unit_cb.grid(row=row_idx, column=3, sticky="w", padx=2, pady=2)
            else:
                unit_cb = None

            self.entries[label] = (entry_inf, entry_sup)
            self.units[label] = unit_cb

        self.check_button = ttk.Button(self, text="Check file", command=self.check_file)
        self.check_button.grid(row=len(labels) + 1, column=0, columnspan=4, pady=5)
        ttk.Label(
            self, text="Check file fills these from the OS input + data; you can override.",
            foreground="#555"
        ).grid(row=len(labels) + 2, column=0, columnspan=4, sticky="w")

    # ---------------------------------------------------------------- #
    def _fill(self, label, inf, sup, unit=None):
        entry_inf, entry_sup = self.entries[label]
        entry_inf.delete(0, tk.END)
        entry_inf.insert(0, "{:.4g}".format(float(inf)))
        entry_sup.delete(0, tk.END)
        entry_sup.insert(0, "{:.4g}".format(float(sup)))
        if unit is not None and self.units.get(label) is not None:
            self.units[label].set(unit)

    def _read_df(self, files, profiles, x):
        """Read the experimental data file (+ align to profiles) or return None."""
        path = os.path.join(files.get("folder", ""), files.get("expdata_file", ""))
        if not os.path.isfile(path):
            return None
        df_data = ed.readdata(path, delzero=not profiles)
        if profiles and x and x[0] == "temperature":
            _, extrainfo = ed.process_osinput(
                files["folder"], files["OS_input_file"], profiles=True, flameinfo=True)
            csv_paths = (extrainfo.get("profileinfo") or {}).get("csv_paths") or []
            if csv_paths:
                df_data = ed.align_data_to_profile_nominal_values(
                    df_data, csv_paths, dg_id="dg1", fillna=0.0)
        return df_data

    def check_file(self):
        try:
            files = self.file_frame.get_data()
            measure = self.measurement_frame.get_data()
            profiles = bool(files.get("profiles_enabled"))
            x = [measure["x_axis"]["variable"], measure["x_axis"]["unit"]]

            _, extrainfo = ed.process_osinput(
                files["folder"], files["OS_input_file"],
                profiles=profiles, flameinfo=True)

            try:
                df_data = self._read_df(files, profiles, x)
            except Exception as exc:  # noqa: BLE001
                df_data = None
                print("check_file: could not read experimental data:", exc)

            try:
                t_inf, t_sup = osc.temperature_bounds(extrainfo, x=x, df_data=df_data)
                self._fill("Temperature", t_inf, t_sup, "K")
            except Exception as exc:  # noqa: BLE001
                messagebox.showwarning("Temperature", f"Temperature bounds not found:\n{exc}")

            try:
                p_inf, p_sup = osc.pressure_bounds(extrainfo, x=x, df_data=df_data)
                self._fill("Pressure", p_inf, p_sup, "bar")
            except Exception as exc:  # noqa: BLE001
                messagebox.showwarning("Pressure", f"Pressure bounds not found:\n{exc}")

            try:
                if measure["experiment_type"] == "laminar burning velocity measurement":
                    # phi is the swept axis; the OS @Moles belong to the outlet stream
                    values = [v for df in (df_data or {}).values() for v in df.index]
                    if not values:
                        raise ValueError("no phi values in the data file")
                    phi, phi_sup = min(values), max(values)
                else:
                    phi = phi_sup = ed.equivalence_ratio(extrainfo["molefractions"])
                self._fill("phi", phi, phi_sup)
            except Exception as exc:  # noqa: BLE001
                print("check_file: equivalence ratio not computed:", exc)

        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Error", f"Error reading OS file:\n{exc}")

    # ---------------------------------------------------------------- #
    def get_data(self):
        data = {}
        t_inf, t_sup = self.entries["Temperature"]
        data["T_INF"] = t_inf.get().strip()
        data["T_SUP"] = t_sup.get().strip()
        data["T_UNIT"] = self.units["Temperature"].get()

        p_inf, p_sup = self.entries["Pressure"]
        data["P_INF"] = p_inf.get().strip()
        data["P_SUP"] = p_sup.get().strip()
        data["P_UNIT"] = self.units["Pressure"].get()

        phi_inf, phi_sup = self.entries["phi"]
        data["PHI_INF"] = phi_inf.get().strip()
        data["PHI_SUP"] = phi_sup.get().strip()
        return data
