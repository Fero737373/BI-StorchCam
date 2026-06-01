from __future__ import annotations

import tkinter as tk
from datetime import datetime
from typing import Dict, List

from .providers.transit_vrr import Departure, get_departures
from .providers.weather_openmeteo import format_weather, get_weather


class OverlayApp:
    def __init__(self, config: Dict):
        self.config = config
        self.last_weather = "Bielefeld | Wetter lädt ..."
        self.root = tk.Tk()
        self.root.withdraw()

        self._build_windows()

    def _ui(self, key: str, default):
        return self.config.get("ui", {}).get(key, default)

    def _build_window(self, y: int, height: int, width: int, x: int, alpha: float) -> tk.Toplevel:
        win = tk.Toplevel()
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        try:
            win.attributes("-alpha", alpha)
        except Exception:
            pass
        win.configure(bg="#101010")
        win.geometry(f"{width}x{height}+{x}+{y}")
        return win

    def _build_windows(self) -> None:
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()

        # Obere Uhrzeit-Leiste
        top_w = min(760, screen_w - 50)
        top_h = 68
        top_x = int((screen_w - top_w) / 2)
        top_y = 14

        # Wetter unten
        weather_w = min(1120, screen_w - 50)
        weather_h = 58
        weather_x = int((screen_w - weather_w) / 2)
        weather_y = screen_h - weather_h - 18

        # Abfahrten rechts über Wetter, kompakt
        bus_w = min(360, screen_w - 32)
        bus_h = 172
        bus_x = screen_w - bus_w - 14
        bus_y = max(86, weather_y - bus_h - 12)

        self.top_win = self._build_window(
            top_y,
            top_h,
            top_w,
            top_x,
            float(self._ui("opacity_top", 0.82)),
        )
        self.weather_win = self._build_window(
            weather_y,
            weather_h,
            weather_w,
            weather_x,
            float(self._ui("opacity_weather", 0.78)),
        )
        self.bus_win = self._build_window(
            bus_y,
            bus_h,
            bus_w,
            bus_x,
            float(self._ui("opacity_bus", 0.88)),
        )

        self.time_label = tk.Label(
            self.top_win,
            text="--:--:--",
            bg="#101010",
            fg="white",
            font=("Arial", int(self._ui("top_clock_font_size", 34)), "bold"),
            padx=18,
            pady=8,
        )
        self.time_label.pack(fill="both", expand=True)

        self.weather_label = tk.Label(
            self.weather_win,
            text="Bielefeld | Wetter lädt ...",
            bg="#101010",
            fg="white",
            font=("Arial", int(self._ui("weather_font_size", 15)), "bold"),
            padx=18,
            pady=10,
        )
        self.weather_label.pack(fill="both", expand=True)

        self.bus_header = tk.Label(
            self.bus_win,
            text="SCHNEIDERSTRASSE",
            bg="#101010",
            fg="#ffd84d",
            font=("DejaVu Sans Mono", int(self._ui("bus_header_font_size", 14)), "bold"),
            anchor="w",
            padx=14,
            pady=5,
        )
        self.bus_header.pack(fill="x")

        self.bus_cols = tk.Label(
            self.bus_win,
            text="Linie Ziel           Zeit",
            bg="#101010",
            fg="#ffd84d",
            font=("DejaVu Sans Mono", 10, "bold"),
            anchor="w",
            padx=14,
        )
        self.bus_cols.pack(fill="x")

        self.bus_text = tk.Label(
            self.bus_win,
            text="lädt ...",
            bg="#101010",
            fg="#ffd84d",
            font=("DejaVu Sans Mono", int(self._ui("bus_font_size", 12)), "bold"),
            anchor="nw",
            justify="left",
            padx=14,
            pady=5,
        )
        self.bus_text.pack(fill="both", expand=True)

    def _lift_all(self) -> None:
        for win in [self.top_win, self.bus_win, self.weather_win]:
            win.lift()
            try:
                win.attributes("-topmost", True)
            except Exception:
                pass

    def refresh_weather_loop(self) -> None:
        loc = self.config.get("location", {})
        try:
            weather = get_weather(
                float(loc.get("latitude", 52.0302)),
                float(loc.get("longitude", 8.5325)),
            )
            self.last_weather = format_weather(str(loc.get("label", "Bielefeld")), weather)
        except Exception:
            self.last_weather = "Bielefeld | Wetterdaten nicht erreichbar"

        self.weather_label.config(text=self.last_weather)
        self._lift_all()
        refresh = int(self.config.get("weather", {}).get("refresh_seconds", 300)) * 1000
        self.root.after(max(30000, refresh), self.refresh_weather_loop)

    def refresh_bus_loop(self) -> None:
        transit = self.config.get("transit", {})
        try:
            rows = get_departures(
                str(transit.get("station_id", "23005489")),
                str(transit.get("station_name", "Gellershagen Schneiderstraße")),
                int(transit.get("max_rows", 5)),
            )
        except Exception:
            rows = []

        station_name = str(transit.get("station_name", "Schneiderstraße"))
        header = station_name.upper().replace("BIELEFELD", "").replace("BI-", "").strip(" ,")
        if len(header) > 22:
            header = header[:22]
        self.bus_header.config(text=header or "ABFAHRTEN")

        if not rows:
            self.bus_text.config(text="Keine Daten")
        else:
            lines = []
            for row in rows:
                lines.append(f"{row.line:<3}  {row.destination:<16} {row.minutes:>6}")
            self.bus_text.config(text="\n".join(lines))

        self._lift_all()
        refresh = int(transit.get("refresh_seconds", 15)) * 1000
        self.root.after(max(5000, refresh), self.refresh_bus_loop)

    def refresh_time_loop(self) -> None:
        self.time_label.config(text=datetime.now().strftime("%H:%M:%S"))
        self._lift_all()
        self.root.after(1000, self.refresh_time_loop)

    def run(self) -> None:
        self.refresh_weather_loop()
        self.refresh_bus_loop()
        self.refresh_time_loop()
        self.root.mainloop()
