from tkinter import ttk

class MeasurementTypeFrame(ttk.LabelFrame):
    def __init__(self, parent):
        super().__init__(parent, text="Measurement Type", padding=10)
        self._build()

    def _build(self):
        # --- Experiment Type (Main) ---
        ttk.Label(self, text="Experiment Type").grid(row=0, column=0, sticky="e", padx=5, pady=2)
        self.exptype = ttk.Combobox(
            self, state="readonly", width=40,
            values=[
                "outlet concentration measurement",
                "jet stirred reactor measurement",
                "burner stabilized flame speciation measurement",
                "concentration time profile measurement",
                "laminar burning velocity measurement",
                "ignition delay measurement"
            ]
        )
        self.exptype.grid(row=0, column=1, sticky="w", pady=2)
        self.exptype.bind("<<ComboboxSelected>>", self.update_subtypes)

        # Subtypes (not all main types have same subtypes)
        self.subtypes_dict = {
            "ignition delay measurement": ["shock tube", "rapid compression machine"],
            "laminar burning velocity measurement": ["flame"],
            "outlet concentration measurement": ["shock tube","stirred reactor","flow reactor"],
            "concentration time profile measurement": ["shock tube","stirred reactor","flow reactor"],
            "jet stirred reactor measurement": ["shock tube","stirred reactor","flow reactor"],
            "burner stabilized flame speciation measurement":["flame"]
        }

        # Reactor type
        ttk.Label(self, text="Reactor type").grid(row=1, column=0, sticky="e", padx=5, pady=2)
        self.reactortype = ttk.Combobox(self, values=[], state="readonly", width=15)
        self.reactortype.grid(row=1, column=1, sticky="w", pady=2)
        self.reactortype.bind("<<ComboboxSelected>>", self.update_third_type)

        # Flame type
        self.flame_label = ttk.Label(self, text="Flame type")
        self.flame_label.grid(row=2, column=0, sticky="e", padx=5, pady=2)
        self.reactormode = ttk.Combobox(
            self,
            values=["counterflow", "premixed", "coflow", "burner stabilized stagnation"],
            state="readonly",
            width=15
        )
        self.reactormode.grid(row=2, column=1, sticky="w", pady=2)
        self.flame_label.grid_remove()
        self.reactormode.grid_remove()
        self.subtype_with_sign = {"flame"}
        
        
        # Ignition type (initially hidden)
        self.ignition_label = ttk.Label(self, text="Ignition type")
        self.ignition_type = ttk.Combobox( self, values=["p-d/dt max", "p", "OH", "CH"],
            state="readonly", width=25
        )
        self.ignition_type.current(0)
        
        self.ignition_label.grid(row=3, column=0, sticky="e", padx=5, pady=2)
        self.ignition_type.grid(row=3, column=1, sticky="w", pady=2)
        
        self.ignition_label.grid_remove()
        self.ignition_type.grid_remove()

        # --- X-axis e Y-axis ---
        # NB: the server stores name/units. Use 'equivalence ratio'
        # (unitless) as the LFS x-axis and 'distance' (cm) for flame position.
        variables = ["temperature", "pressure", "time", "distance", "phi",
                     "equivalence ratio", "ignition delay", "composition",
                     "laminar burning velocity", "volume", "length", "concentration"]
        units_dict = {
            "temperature": ["K"],
            "pressure": ["bar", "Pa", "kPa", "MPa", "atm"],
            "time": ["s", "ms", "us", "min"],
            "distance": ["cm", "mm", "m"],
            "phi": ["-"],
            "equivalence ratio": ["unitless"],
            "ignition delay":["s", "ms", "us", "min"],
            "composition":["mole fraction"],
            "concentration":["mol/cm3","mol/dm3","mol/m3"],
            "length":["m","cm","mm","um"],
            "laminar burning velocity":["cm/s", "m/s", "mm/s"]
        }

        # X-axis
        ttk.Label(self, text="Plot x-axis").grid(row=4, column=0, sticky="e", padx=5, pady=2)
        self.x_var_cb = ttk.Combobox(self, values=variables, state="readonly", width=15)
        self.x_var_cb.grid(row=4, column=1, sticky="w", pady=2)
        self.x_unit_cb = ttk.Combobox(self, values=[], state="readonly", width=10)
        self.x_unit_cb.grid(row=4, column=2, sticky="w", padx=2, pady=2)

        self.x_var_cb.bind("<<ComboboxSelected>>", self.update_x_units)

        # Y-axis
        ttk.Label(self, text="Plot y-axis").grid(row=5, column=0, sticky="e", padx=5, pady=2)
        self.y_var_cb = ttk.Combobox(self, values=variables, state="readonly", width=15)
        self.y_var_cb.grid(row=5, column=1, sticky="w", pady=2)
        self.y_unit_cb = ttk.Combobox(self, values=[], state="readonly", width=10)
        self.y_unit_cb.grid(row=5, column=2, sticky="w", padx=2, pady=2)

        self.y_var_cb.bind("<<ComboboxSelected>>", self.update_y_units)

        # Salvataggio delle unità disponibili
        self.units_dict = units_dict

    def update_subtypes(self, event=None):
        cat = self.exptype.get()
        # reactor subtypes
        self.reactortype['values'] = self.subtypes_dict.get(cat, [])
        if self.reactortype['values']:
            self.reactortype.current(0)
        else:
            self.reactortype.set('')
    
        # ignition type visibility
        if cat == "ignition delay measurement":
            self.ignition_label.grid()
            self.ignition_type.grid()
        else:
            self.ignition_label.grid_remove()
            self.ignition_type.grid_remove()

        if cat == "laminar burning velocity measurement":
            self._preset_axis(self.x_var_cb, self.x_unit_cb, "equivalence ratio")
            self._preset_axis(self.y_var_cb, self.y_unit_cb, "laminar burning velocity")

        self.update_third_type()

    def _preset_axis(self, var_cb, unit_cb, variable):
        var_cb.set(variable)
        unit_cb["values"] = self.units_dict.get(variable, [])
        if unit_cb["values"]:
            unit_cb.current(0)
    
    def update_third_type(self, event=None):
        subtype = self.reactortype.get()
        if subtype in self.subtype_with_sign:
            self.flame_label.grid()
            self.reactormode.grid()
            self.reactormode.current(0)
        else:
            self.flame_label.grid_remove()
            self.reactormode.grid_remove()

    def update_x_units(self, event=None):
        var = self.x_var_cb.get()
        self.x_unit_cb['values'] = self.units_dict.get(var, [])
        if self.x_unit_cb['values']:
            self.x_unit_cb.current(0)

    def update_y_units(self, event=None):
        var = self.y_var_cb.get()
        self.y_unit_cb['values'] = self.units_dict.get(var, [])
        if self.y_unit_cb['values']:
            self.y_unit_cb.current(0)

    def get_data(self):
        return {
            "experiment_type": self.exptype.get(),
            "reactor_type": self.reactortype.get(),
            "reactor_mode": self.reactormode.get() if self.reactormode.winfo_ismapped() else "premixed",
            "ignition_type": ( self.ignition_type.get() if self.exptype.get() == "ignition delay measurement" else None),
            "x_axis": {
                "variable": self.x_var_cb.get(),
                "unit": self.x_unit_cb.get()
            },
            "y_axis": {
                "variable": self.y_var_cb.get(),
                "unit": self.y_unit_cb.get()
            }
        }
