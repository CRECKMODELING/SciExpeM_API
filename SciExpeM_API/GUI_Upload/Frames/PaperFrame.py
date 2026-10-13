import tkinter as tk
from tkinter import ttk

class PaperFrame(ttk.LabelFrame):
    def __init__(self, parent):
        super().__init__(parent, text="Paper informations", padding=10)
        self._build()

    def _build(self):
        ttk.Label(self, text="DOI").grid(row=0, column=0, sticky="e", padx=5, pady=2)
        self.doi = ttk.Entry(self, width=40)
        self.doi.grid(row=0, column=1, sticky="w", pady=2)

        ttk.Label(self, text="Authors").grid(row=1, column=0, sticky="e", padx=5, pady=2)
        self.authors = ttk.Entry(self, width=40)
        self.authors.grid(row=1, column=1, sticky="w", pady=2)

        ttk.Label(self, text="Title").grid(row=2, column=0, sticky="e", padx=5, pady=2)
        self.title = ttk.Entry(self, width=40)
        self.title.grid(row=2, column=1, sticky="w", pady=2)

        ttk.Label(self, text="Year").grid(row=3, column=0, sticky="e", padx=5, pady=2)
        self.year = ttk.Entry(self, width=10)
        self.year.grid(row=3, column=1, sticky="w", pady=2)

        ttk.Label(self, text="Description").grid(row=4, column=0, sticky="ne", padx=5, pady=2)
        self.description = tk.Text(self, width=47, height=4)
        self.description.grid(row=4, column=1, sticky="w", pady=2)
        
        ttk.Label(self, text="Comments").grid(row=5, column=0, sticky="ne", padx=5, pady=2)
        self.comments = tk.Text(self, width=47, height=4)
        self.comments.grid(row=5, column=1, sticky="w", pady=2)

    def get_data(self):
        try:
            year_val = int(self.year.get().strip())
        except ValueError:
            year_val = None

        return {
            "doi": self.doi.get().strip(),
            "author": self.authors.get().strip(),
            "title": self.title.get().strip(),
            "year": year_val,
            "description": self.description.get("1.0", "end").strip(),
            "comments": self.comments.get("1.0", "end").strip()
        }
