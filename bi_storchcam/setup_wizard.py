from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from typing import Dict, List, Optional

from .config import DEFAULT_STREAM_URL, load_config, save_config
from .geocoding import geocode_bielefeld
from .providers.transit_vrr import Station, search_stations


class SetupWizard:
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or load_config()
        self.stations: List[Station] = []
        self.selected_station: Optional[Station] = None
        self.geo_result = None

        self.root = tk.Tk()
        self.root.title("BI-StorchCam Setup")
        self.root.geometry("760x560")
        self.root.minsize(720, 520)
        self.root.configure(bg="#111111")

        self._build()

    def _label(self, text: str, size: int = 11, bold: bool = False) -> tk.Label:
        return tk.Label(
            self.root,
            text=text,
            bg="#111111",
            fg="white",
            anchor="w",
            font=("Arial", size, "bold" if bold else "normal"),
        )

    def _entry(self, value: str) -> tk.Entry:
        entry = tk.Entry(self.root, font=("Arial", 12), bg="#202020", fg="white", insertbackground="white")
        entry.insert(0, value)
        return entry

    def _button(self, text: str, command) -> tk.Button:
        return tk.Button(
            self.root,
            text=text,
            command=command,
            font=("Arial", 11, "bold"),
            bg="#303030",
            fg="white",
            activebackground="#444444",
            activeforeground="white",
            relief="flat",
            padx=14,
            pady=8,
        )

    def _build(self) -> None:
        pad_x = 18

        title = tk.Label(
            self.root,
            text="BI-StorchCam Setup",
            bg="#111111",
            fg="white",
            font=("Arial", 22, "bold"),
            anchor="w",
        )
        title.pack(fill="x", padx=pad_x, pady=(18, 8))

        desc = tk.Label(
            self.root,
            text="Adresse oder Ort in Bielefeld eingeben, Haltestelle bestätigen und Infoscreen starten.",
            bg="#111111",
            fg="#cccccc",
            font=("Arial", 11),
            anchor="w",
        )
        desc.pack(fill="x", padx=pad_x, pady=(0, 18))

        self._label("Livestream-Link", bold=True).pack(fill="x", padx=pad_x)
        self.stream_entry = self._entry(self.config.get("video", {}).get("url", DEFAULT_STREAM_URL))
        self.stream_entry.pack(fill="x", padx=pad_x, pady=(4, 14))

        self._label("Ort oder Adresse in Bielefeld", bold=True).pack(fill="x", padx=pad_x)
        self.location_entry = self._entry(self.config.get("location", {}).get("query", "Bielefeld"))
        self.location_entry.pack(fill="x", padx=pad_x, pady=(4, 14))

        self._label("Haltestelle manuell, optional", bold=True).pack(fill="x", padx=pad_x)
        self.station_entry = self._entry(self.config.get("transit", {}).get("station_name", ""))
        self.station_entry.pack(fill="x", padx=pad_x, pady=(4, 10))

        button_frame = tk.Frame(self.root, bg="#111111")
        button_frame.pack(fill="x", padx=pad_x, pady=(2, 12))
        self._button("Suchen", self.search).pack(side="left")
        self._button("Ausgewählte Haltestelle speichern und starten", self.save_and_close).pack(side="left", padx=(10, 0))

        self.status_label = tk.Label(
            self.root,
            text="Noch keine Suche gestartet.",
            bg="#111111",
            fg="#cccccc",
            anchor="w",
            font=("Arial", 10),
        )
        self.status_label.pack(fill="x", padx=pad_x, pady=(0, 8))

        self.listbox = tk.Listbox(
            self.root,
            font=("DejaVu Sans Mono", 11),
            bg="#181818",
            fg="#ffd84d",
            selectbackground="#444444",
            selectforeground="white",
            height=12,
        )
        self.listbox.pack(fill="both", expand=True, padx=pad_x, pady=(0, 18))
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        footer = tk.Label(
            self.root,
            text="Wenn die Haltestelle falsch ist: Namen manuell eingeben und erneut suchen.",
            bg="#111111",
            fg="#999999",
            anchor="w",
            font=("Arial", 10),
        )
        footer.pack(fill="x", padx=pad_x, pady=(0, 14))

    def _on_select(self, _event=None) -> None:
        selection = self.listbox.curselection()
        if not selection:
            return
        index = selection[0]
        if 0 <= index < len(self.stations):
            self.selected_station = self.stations[index]
            self.status_label.config(
                text=f"Ausgewählt: {self.selected_station.name} (ID {self.selected_station.station_id})"
            )

    def search(self) -> None:
        location_query = self.location_entry.get().strip() or "Bielefeld"
        manual_station = self.station_entry.get().strip()
        station_query = manual_station or location_query

        self.status_label.config(text="Suche läuft ...")
        self.root.update_idletasks()

        try:
            self.geo_result = geocode_bielefeld(location_query)
            self.stations = search_stations(station_query, limit=12)
        except Exception as exc:
            messagebox.showerror("Fehler", f"Suche fehlgeschlagen:\n{exc}")
            self.status_label.config(text="Suche fehlgeschlagen.")
            return

        self.listbox.delete(0, tk.END)
        for station in self.stations:
            self.listbox.insert(tk.END, f"{station.station_id:<10}  {station.name}")

        if self.stations:
            self.listbox.selection_set(0)
            self.selected_station = self.stations[0]
            self.status_label.config(
                text=(
                    f"Wetter-Ort: {self.geo_result.label}. "
                    f"Bitte Haltestelle prüfen und bestätigen."
                )
            )
        else:
            self.selected_station = None
            self.status_label.config(text="Keine Haltestelle gefunden. Bitte Haltestelle manuell eingeben.")

    def save_and_close(self) -> None:
        if self.geo_result is None:
            self.search()

        if self.selected_station is None:
            messagebox.showwarning("Haltestelle fehlt", "Bitte zuerst eine Haltestelle suchen und auswählen.")
            return

        video_url = self.stream_entry.get().strip() or DEFAULT_STREAM_URL
        location_query = self.location_entry.get().strip() or "Bielefeld"

        if self.geo_result is None:
            self.geo_result = geocode_bielefeld(location_query)

        self.config.setdefault("video", {})["url"] = video_url
        self.config.setdefault("video", {})["fullscreen"] = True

        self.config["location"] = {
            "query": location_query,
            "label": self.geo_result.label,
            "latitude": self.geo_result.latitude,
            "longitude": self.geo_result.longitude,
        }

        self.config["transit"] = {
            "provider": "vrr",
            "station_id": self.selected_station.station_id,
            "station_name": self.selected_station.name,
            "refresh_seconds": 15,
            "max_rows": 5,
        }

        save_config(self.config)
        messagebox.showinfo("Gespeichert", "Konfiguration gespeichert. Der Infoscreen startet jetzt.")
        self.root.destroy()

    def run(self) -> Dict:
        self.root.mainloop()
        return load_config()


def run_setup(config: Optional[Dict] = None) -> Dict:
    wizard = SetupWizard(config)
    return wizard.run()
