"""Airport Chaos: optional graphical interface (Tkinter, no extra installs).

Run from the project root:   python gui/app.py

The GUI contains no algorithm logic: every action calls the same Engine and
algorithm functions as the command-line interface.
"""
import os
import sys
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, messagebox, filedialog
from datetime import datetime

ROOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT_DIR)

from airport.engine import Engine
from airport.flight import Flight
from airport.sorting import counting_sort_priority, radix_sort_ids
from airport.analysis import build_load, analyze
from airport.matrix import build_route_matrix, classical_multiply, strassen_multiply
from airport.perfect_hash import PerfectHash, RULE_IDS

OFFICIAL_CSV = os.path.join(ROOT_DIR, "data", "airport_flights.csv")
TIME_FMT = "%Y-%m-%d %H:%M"

# ---------------------------------------------------------------- palette (light pastel)
BG = "#f5f6fb"
PANEL = "#ffffff"
PANEL_2 = "#f1f3fa"
LINE = "#e4e8f1"
TEXT = "#2b3145"
MUTED = "#8c94a8"
HEAD = "#5b6bd6"
PRIMARY = "#c9d4ff"
PRIMARY_HOVER = "#b5c3ff"
SECONDARY = "#eef0f7"
SECONDARY_HOVER = "#e2e6f2"
ACCENT = "#9edcc8"
DELAYED = "#ffcf99"
CANCELLED = "#f5a9bb"
EMERGENCY = "#c3b3f5"
HIGHLIGHT_FILL = "#fff7dc"
HIGHLIGHT_LINE = "#e9c96b"
HEAT_HIGH = "#8fb8f2"

STATUS_COLOUR = {"SCHEDULED": ACCENT, "DELAYED": DELAYED, "CANCELLED": CANCELLED}
STATUS_TEXT = {"SCHEDULED": "#2f8f74", "DELAYED": "#c07a1f", "CANCELLED": "#c2506b"}
EMERGENCY_TEXT = "#7a5fd1"
FAMILY = "Helvetica Neue"
FONT = (FAMILY, 13)
FONT_SMALL = (FAMILY, 11)
FONT_BOLD = (FAMILY, 13, "bold")
FONT_HEAD = (FAMILY, 15, "bold")
FONT_TITLE = (FAMILY, 22, "bold")
MONO = ("Menlo", 12)

PX_PER_MIN = 3
ROW_H = 46
LEFT = 60


def hhmm(dt):
    return dt.strftime("%H:%M") if dt else "-----"


def _round_rect(c, x0, y0, x1, y1, r, **kw):
    """Rounded rectangle on a Canvas (smoothed polygon)."""
    r = max(0, min(r, (x1 - x0) / 2, (y1 - y0) / 2))
    pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
           x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
    return c.create_polygon(pts, smooth=True, **kw)


def _mix(c1, c2, t):
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    t = max(0.0, min(1.0, t)) ** 0.6
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))


# ================================================================ rounded widgets
class RoundButton(tk.Canvas):
    """Pill-shaped button drawn on a canvas (ttk buttons cannot be rounded)."""

    def __init__(self, parent, text, command=None, kind="secondary", bg=PANEL,
                 radius=14, padx=16, pady=8, font=FONT, fill_width=False, width=None):
        self.colours = {"primary": (PRIMARY, PRIMARY_HOVER),
                        "secondary": (SECONDARY, SECONDARY_HOVER),
                        "tab": (bg, SECONDARY_HOVER),
                        "tab_on": (PANEL, PANEL)}
        self.kind, self.command, self.radius, self.text = kind, command, radius, text
        self.font = font
        f = tkfont.Font(font=font)
        w = width or (f.measure(text) + 2 * padx)
        h = f.metrics("linespace") + 2 * pady
        super().__init__(parent, width=w, height=h, bg=bg, highlightthickness=0, bd=0)
        self.fill_width = fill_width
        self._draw(False)
        self.bind("<Enter>", lambda _e: self._draw(True))
        self.bind("<Leave>", lambda _e: self._draw(False))
        self.bind("<Button-1>", lambda _e: self.command and self.command())
        self.bind("<Configure>", lambda _e: self._draw(False))

    def set_kind(self, kind):
        self.kind = kind
        self._draw(False)

    def _draw(self, hover):
        self.delete("all")
        w, h = int(self.winfo_width() or self["width"]), int(self.winfo_height() or self["height"])
        if w <= 1:
            w, h = int(self["width"]), int(self["height"])
        base, over = self.colours[self.kind]
        fill = over if hover else base
        outline = LINE if self.kind == "tab_on" else ""
        _round_rect(self, 1, 1, w - 1, h - 1, self.radius, fill=fill, outline=outline)
        colour = HEAD if self.kind == "tab_on" else (MUTED if self.kind == "tab" else TEXT)
        weight = "bold" if self.kind in ("primary", "tab_on") else "normal"
        self.create_text(w / 2, h / 2, text=self.text, fill=colour,
                         font=(self.font[0], self.font[1], weight))


class RoundEntry(tk.Canvas):
    """Rounded input box: a borderless Entry inside a rounded rectangle."""

    def __init__(self, parent, textvariable, width=180, bg=PANEL, fill=PANEL_2):
        h = 34
        super().__init__(parent, width=width, height=h, bg=bg, highlightthickness=0, bd=0)
        self.fill = fill
        self.entry = tk.Entry(self, textvariable=textvariable, relief="flat", bd=0,
                              bg=fill, fg=TEXT, insertbackground=TEXT, font=FONT,
                              highlightthickness=0)
        self.window = self.create_window(12, h / 2, window=self.entry, anchor="w")
        self.bind("<Configure>", self._draw)
        self._draw()

    def _draw(self, _event=None):
        w = int(self.winfo_width() or self["width"])
        if w <= 1:
            w = int(self["width"])
        h = int(self["height"])
        self.delete("frame")
        _round_rect(self, 1, 1, w - 1, h - 1, 12, fill=self.fill, outline=LINE, tags="frame")
        self.tag_lower("frame")
        self.itemconfigure(self.window, width=max(20, w - 24))

    def bind_return(self, fn):
        self.entry.bind("<Return>", lambda _e: fn())


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Airport Chaos · Ground Stop Scheduler")
        self.geometry("1340x840")
        self.minsize(1120, 720)
        self.configure(bg=BG)
        self.engine = Engine()
        self.day = None
        self.emergency_ids = set()
        self.block_info = {}
        self.selected = None
        self._style()
        self._layout()
        self.load_csv(OFFICIAL_CSV)

    # ------------------------------------------------------------ styling (tables only)
    def _style(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("Treeview", background=PANEL, fieldbackground=PANEL, foreground=TEXT,
                    rowheight=28, borderwidth=0, font=MONO)
        s.configure("Treeview.Heading", background=PANEL, foreground=MUTED, font=FONT_SMALL,
                    borderwidth=0, relief="flat", padding=(6, 6))
        s.map("Treeview", background=[("selected", "#e8ecff")], foreground=[("selected", TEXT)])
        s.map("Treeview.Heading", background=[("active", PANEL_2)])
        for orient in ("Vertical", "Horizontal"):
            s.configure(f"{orient}.TScrollbar", background=SECONDARY, troughcolor=PANEL,
                        borderwidth=0, arrowsize=0, relief="flat")

    def _label(self, parent, text, bg=PANEL, fg=TEXT, font=FONT, **kw):
        return tk.Label(parent, text=text, bg=bg, fg=fg, font=font, **kw)

    def _card(self, parent, bg=PANEL, pad=18):
        """White rounded card: a canvas border with a frame inside."""
        outer = tk.Frame(parent, bg=parent["bg"])
        canvas = tk.Canvas(outer, bg=parent["bg"], highlightthickness=0, bd=0)
        canvas.place(relwidth=1, relheight=1)
        inner = tk.Frame(outer, bg=bg)
        inner.pack(fill="both", expand=True, padx=pad, pady=pad)

        def redraw(_e=None):
            canvas.delete("all")
            w, h = outer.winfo_width(), outer.winfo_height()
            _round_rect(canvas, 1, 1, w - 1, h - 1, 18, fill=bg, outline=LINE)
        outer.bind("<Configure>", redraw)
        return outer, inner

    # ------------------------------------------------------------ layout
    def _layout(self):
        side = tk.Frame(self, bg=PANEL, padx=22, pady=22)
        side.pack(side="left", fill="y")
        tk.Frame(self, bg=LINE, width=1).pack(side="left", fill="y")

        self._label(side, "Airport Chaos", font=FONT_TITLE).pack(anchor="w")
        self._label(side, "Ground stop scheduler · CP3", fg=MUTED, font=FONT_SMALL).pack(anchor="w", pady=(0, 18))

        RoundButton(side, "Load official CSV", lambda: self.load_csv(OFFICIAL_CSV),
                    kind="primary", width=230).pack(anchor="w", pady=3)
        RoundButton(side, "Load other CSV…", self.pick_csv, width=230).pack(anchor="w", pady=3)

        self._section(side, "Find flight")
        row = tk.Frame(side, bg=PANEL); row.pack(anchor="w")
        self.find_var = tk.StringVar(value="B610505")
        e = RoundEntry(row, self.find_var, width=150); e.pack(side="left")
        e.bind_return(self.find)
        RoundButton(row, "Find", self.find, kind="primary").pack(side="left", padx=(8, 0))

        self._section(side, "Selected flight")
        card_outer, card = self._card(side, bg=PANEL_2, pad=14)
        card_outer.pack(fill="x")
        self.detail = self._label(card, "Click a flight on\nthe timeline", bg=PANEL_2, fg=MUTED,
                                  font=MONO, justify="left", anchor="w")
        self.detail.pack(fill="x")
        btns = tk.Frame(side, bg=PANEL); btns.pack(anchor="w", pady=(8, 0))
        RoundButton(btns, "Cancel", self.cancel_selected, width=105).pack(side="left")
        RoundButton(btns, "Reschedule…", self.reschedule_selected, width=117).pack(side="left", padx=(8, 0))

        self._section(side, "Legend")
        for label, colour, outline in (("Scheduled", ACCENT, False), ("Delayed", DELAYED, False),
                                       ("Cancelled (original slot)", CANCELLED, True),
                                       ("Emergency", EMERGENCY, False)):
            r = tk.Frame(side, bg=PANEL); r.pack(anchor="w", pady=2)
            sw = tk.Canvas(r, width=16, height=16, bg=PANEL, highlightthickness=0)
            sw.pack(side="left")
            if outline:
                _round_rect(sw, 2, 2, 14, 14, 5, fill=PANEL, outline=colour, width=2)
            else:
                _round_rect(sw, 1, 1, 15, 15, 5, fill=colour, outline="")
            self._label(r, "  " + label, font=FONT_SMALL).pack(side="left")

        self.status = tk.StringVar(value="")
        tk.Label(side, textvariable=self.status, bg=PANEL, fg=MUTED, font=FONT_SMALL,
                 wraplength=230, justify="left").pack(side="bottom", anchor="w")

        # ---- main area: rounded tab bar + pages
        main = tk.Frame(self, bg=BG, padx=20, pady=16)
        main.pack(side="left", fill="both", expand=True)
        self.tabbar = tk.Frame(main, bg=BG)
        self.tabbar.pack(fill="x", pady=(0, 12))
        page_outer, self.pages = self._card(main, bg=PANEL, pad=16)
        page_outer.pack(fill="both", expand=True)
        self.tab_buttons, self.page_frames = [], []
        for name, builder in (("Runways", self._tab_runways), ("Scenarios", self._tab_scenarios),
                              ("Flights", self._tab_flights), ("Analysis", self._tab_analysis),
                              ("Routes", self._tab_routes), ("Stats", self._tab_stats)):
            frame = tk.Frame(self.pages, bg=PANEL)
            builder(frame)
            index = len(self.page_frames)
            btn = RoundButton(self.tabbar, name, lambda i=index: self.select_tab(i),
                              kind="tab", bg=BG, radius=12, padx=20, pady=9)
            btn.pack(side="left", padx=(0, 6))
            self.tab_buttons.append(btn)
            self.page_frames.append(frame)
        self.select_tab(0)

    def select_tab(self, index):
        for i, (btn, frame) in enumerate(zip(self.tab_buttons, self.page_frames)):
            if i == index:
                btn.set_kind("tab_on")
                frame.pack(fill="both", expand=True)
            else:
                btn.set_kind("tab")
                frame.pack_forget()

    def _section(self, parent, text):
        self._label(parent, text.upper(), fg=MUTED, font=(FAMILY, 10, "bold")).pack(anchor="w", pady=(20, 6))

    def _heading(self, parent, text, sub=""):
        row = tk.Frame(parent, bg=PANEL); row.pack(fill="x", pady=(0, 10))
        self._label(row, text, fg=HEAD, font=FONT_HEAD).pack(side="left")
        if sub:
            self._label(row, "   " + sub, fg=MUTED, font=FONT_SMALL).pack(side="left", pady=(3, 0))
        return row

    # ------------------------------------------------------------ tab: runways
    def _tab_runways(self, f):
        top = self._heading(f, "Runway timeline", "24 h · scroll sideways · click a block for details")
        RoundButton(top, "Jump to 14:00", lambda: self.scroll_to(14 * 60)).pack(side="right")
        RoundButton(top, "Jump to 09:00", lambda: self.scroll_to(9 * 60)).pack(side="right", padx=8)
        self.timeline = tk.Canvas(f, bg=PANEL, highlightthickness=0)
        hbar = ttk.Scrollbar(f, orient="horizontal", command=self.timeline.xview)
        self.timeline.configure(xscrollcommand=hbar.set)
        self.timeline.pack(fill="both", expand=True)
        hbar.pack(fill="x")
        self.timeline.bind("<Button-1>", self.on_timeline_click)

    def draw_timeline(self):
        c = self.timeline
        c.delete("all")
        self.block_info = {}
        if self.day is None:
            return
        midnight = datetime(self.day.year, self.day.month, self.day.day)
        runways = sorted(self.engine.runways)
        width = LEFT + 1440 * PX_PER_MIN + 20
        height = 40 + ROW_H * len(runways) + 10
        c.configure(scrollregion=(0, 0, width, height))
        for h in range(25):
            x = LEFT + h * 60 * PX_PER_MIN
            c.create_line(x, 24, x, height, fill=LINE)
            c.create_text(x + 4, 12, text=f"{h:02d}:00", fill=MUTED, anchor="w", font=FONT_SMALL)
        cancelled = [f for f in self.engine.registry.all_flights() if f.status == "CANCELLED"]
        for row, name in enumerate(runways):
            y = 32 + row * ROW_H
            _round_rect(c, 6, y + 2, LEFT - 10, y + ROW_H - 10, 10, fill=PANEL_2, outline="")
            c.create_text(LEFT // 2 - 2, y + (ROW_H - 8) // 2, text=name, fill=HEAD, font=FONT_BOLD)
            for f in cancelled:
                if f.runway == name:
                    self._block(c, f, f.orig_start, f.orig_end, y, midnight, CANCELLED, outline_only=True)
            for f in self.engine.runways[name].inorder():
                colour = EMERGENCY if f.flight_id in self.emergency_ids else STATUS_COLOUR.get(f.status, ACCENT)
                self._block(c, f, f.start, f.end, y, midnight, colour)

    def _block(self, c, f, start, end, y, midnight, colour, outline_only=False):
        x0 = LEFT + (start - midnight).total_seconds() / 60 * PX_PER_MIN
        x1 = LEFT + (end - midnight).total_seconds() / 60 * PX_PER_MIN
        if outline_only:
            item = _round_rect(c, x0, y + 4, x1, y + ROW_H - 12, 5, fill=PANEL, outline=colour, width=2)
        else:
            item = _round_rect(c, x0, y + 4, x1, y + ROW_H - 12, 5, fill=colour, outline="")
        self.block_info[item] = f

    def on_timeline_click(self, event):
        x, y = self.timeline.canvasx(event.x), self.timeline.canvasy(event.y)
        for item in self.timeline.find_overlapping(x - 2, y - 2, x + 2, y + 2):
            if item in self.block_info:
                self.show_flight(self.block_info[item])
                return

    def scroll_to(self, minute):
        total = LEFT + 1440 * PX_PER_MIN + 20
        self.timeline.xview_moveto(max(0, (LEFT + minute * PX_PER_MIN - 40) / total))

    # ------------------------------------------------------------ tab: scenarios
    def _tab_scenarios(self, f):
        self._heading(f, "Crisis scenarios", "official values pre-filled · run each from a fresh load")
        cards = tk.Frame(f, bg=PANEL); cards.pack(fill="x")
        date = "2026-11-27"

        a = self._scenario_card(cards, "A · Runway closure")
        self.a_runway = self._field(a, "Runway", "R1")
        self.a_start = self._field(a, "Closed from", f"{date} 09:00")
        self.a_end = self._field(a, "Closed until", f"{date} 11:00")
        RoundButton(a, "Run closure", self.run_a, kind="primary", bg=PANEL_2, width=200).pack(anchor="w", pady=(10, 0))

        b = self._scenario_card(cards, "B · Emergency insert")
        self.b_id = self._field(b, "Flight ID", "EM90001")
        self.b_runway = self._field(b, "Runway", "R1")
        self.b_start = self._field(b, "Requested start", f"{date} 09:00")
        self.b_end = self._field(b, "Requested end", f"{date} 09:05")
        r = tk.Frame(b, bg=PANEL_2); r.pack(anchor="w", pady=(10, 0))
        RoundButton(r, "Check & offer", lambda: self.run_b(False), bg=PANEL_2).pack(side="left")
        RoundButton(r, "Accept slot", lambda: self.run_b(True), kind="primary", bg=PANEL_2).pack(side="left", padx=(8, 0))

        cc = self._scenario_card(cards, "C · Mass cancel", last=True)
        self.c_start = self._field(cc, "Window start", f"{date} 14:00")
        self.c_end = self._field(cc, "Window end", f"{date} 15:00")
        RoundButton(cc, "Cancel window", self.run_c, kind="primary", bg=PANEL_2, width=200).pack(anchor="w", pady=(10, 0))

        self.scen_summary = self._label(f, "", font=FONT_BOLD, anchor="w")
        self.scen_summary.pack(fill="x", pady=(16, 6))
        self.scen_table = self._table(f, ("Flight", "Old start", "New start", "Status"), (120, 120, 120, 140))

    def _scenario_card(self, parent, title, last=False):
        outer, inner = self._card(parent, bg=PANEL_2, pad=16)
        outer.pack(side="left", fill="both", expand=True, padx=(0, 0 if last else 12))
        self._label(inner, title, bg=PANEL_2, fg=HEAD, font=FONT_BOLD).pack(anchor="w", pady=(0, 8))
        return inner

    def _field(self, parent, label, default):
        self._label(parent, label, bg=PANEL_2, fg=MUTED, font=FONT_SMALL).pack(anchor="w")
        var = tk.StringVar(value=default)
        RoundEntry(parent, var, width=200, bg=PANEL_2, fill=PANEL).pack(anchor="w", pady=(2, 6))
        return var

    def _table(self, parent, columns, widths):
        wrap = tk.Frame(parent, bg=PANEL); wrap.pack(fill="both", expand=True)
        t = ttk.Treeview(wrap, columns=columns, show="headings")
        for col, w in zip(columns, widths):
            t.heading(col, text=col)
            t.column(col, width=w, anchor="w")
        sb = ttk.Scrollbar(wrap, orient="vertical", command=t.yview)
        t.configure(yscrollcommand=sb.set)
        t.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")
        for status, colour in STATUS_TEXT.items():
            t.tag_configure(status, foreground=colour)
        t.tag_configure("EMERGENCY", foreground=EMERGENCY_TEXT)
        return t

    def _fill(self, table, rows):
        table.delete(*table.get_children())
        for values, tag in rows:
            table.insert("", "end", values=values, tags=(tag,))

    def _time(self, var):
        return datetime.strptime(var.get().strip(), TIME_FMT)

    def run_a(self):
        try:
            rows, n, d, c, mins = self.engine.runway_closure(
                self.a_runway.get().strip(), self._time(self.a_start), self._time(self.a_end))
        except KeyError:
            return messagebox.showerror("Runway closure", "No such runway.")
        except ValueError as e:
            return messagebox.showerror("Runway closure", f"Bad time: {e}")
        self._fill(self.scen_table, [((fid, hhmm(old), hhmm(new), st), st) for fid, old, new, st in rows])
        self.scen_summary.configure(
            text=f"Affected {n}  ·  delayed {d}  ·  cancelled {c}  ·  total delay {mins} min")
        self.refresh()

    def run_b(self, accept):
        try:
            f = Flight(self.b_id.get().strip(), "EM", "JFK", "BOS", self.b_runway.get().strip(),
                       self._time(self.b_start), self._time(self.b_end), 1)
        except ValueError as e:
            return messagebox.showerror("Emergency insert", f"Bad time: {e}")
        ok, msg, clashes, slot = self.engine.emergency_insert(f, accept)
        rows = [((c.flight_id, hhmm(c.start), "", "conflict"), "CANCELLED") for c in clashes]
        if slot is not None:
            rows.append(((f.flight_id, hhmm(self._time(self.b_start)), hhmm(slot),
                          "INSERTED" if ok else "OFFERED"), "EMERGENCY"))
        self._fill(self.scen_table, rows)
        extra = f"  ·  slot {hhmm(slot)}" if slot else ""
        self.scen_summary.configure(text=f"{f.flight_id}: {msg.strip()}{extra}")
        if ok:
            self.emergency_ids.add(f.flight_id)
        self.refresh()

    def run_c(self):
        try:
            ids = self.engine.mass_cancel(self._time(self.c_start), self._time(self.c_end))
        except ValueError as e:
            return messagebox.showerror("Mass cancel", f"Bad time: {e}")
        rows = []
        for fid in ids:
            fl = self.engine.find(fid)[0]
            rows.append(((fid, hhmm(fl.orig_start), "", "CANCELLED"), "CANCELLED"))
        self._fill(self.scen_table, rows)
        self.scen_summary.configure(text=f"Cancelled {len(ids)} flights on all runways")
        self.refresh()

    # ------------------------------------------------------------ tab: flights
    def _tab_flights(self, f):
        top = self._heading(f, "All flights")
        RoundButton(top, "Stability demo", lambda: self.fill_flights("demo")).pack(side="right")
        RoundButton(top, "Sort by ID · radix", lambda: self.fill_flights("id")).pack(side="right", padx=8)
        RoundButton(top, "Sort by priority · counting",
                    lambda: self.fill_flights("priority")).pack(side="right")
        self.flight_note = self._label(f, "", fg=MUTED, font=FONT_SMALL, anchor="w")
        self.flight_note.pack(fill="x", pady=(0, 6))
        self.flight_table = self._table(
            f, ("ID", "Airline", "From", "To", "Runway", "Start", "End", "Priority", "Status"),
            (100, 70, 60, 60, 70, 70, 70, 70, 110))

    def fill_flights(self, mode):
        flights = self.engine.registry.all_flights()
        if mode == "priority":
            flights = counting_sort_priority(flights)
            note = "Counting sort on priority (stable, k = 3)."
        elif mode == "id":
            flights = radix_sort_ids(flights)
            note = "LSD radix sort on flight ID (one stable counting pass per character)."
        else:
            flights = counting_sort_priority(radix_sort_ids(flights))
            ok = all(flights[i].flight_id < flights[i + 1].flight_id
                     for i in range(len(flights) - 1) if flights[i].priority == flights[i + 1].priority)
            note = f"Sorted by ID, then by priority: IDs stay in order inside each priority → stable: {ok}"
        self.flight_note.configure(text=note)
        self._fill(self.flight_table, [((f.flight_id, f.airline, f.origin, f.destination, f.runway,
                                         hhmm(f.start), hhmm(f.end), f.priority, f.status), f.status)
                                       for f in flights])

    # ------------------------------------------------------------ tab: analysis
    def _tab_analysis(self, f):
        self._heading(f, "Disruption analysis", "delayed + cancelled per 5-minute bucket, by original start")
        self.analysis_note = self._label(f, "", anchor="w", justify="left")
        self.analysis_note.pack(fill="x", pady=(0, 8))
        self.chart = tk.Canvas(f, bg=PANEL, highlightthickness=0, height=360)
        self.chart.pack(fill="both", expand=True)
        self.chart.bind("<Configure>", lambda _e: self.draw_analysis())

    def draw_analysis(self):
        c = self.chart
        c.delete("all")
        flights = self.engine.registry.all_flights()
        load, day = build_load(flights)
        if not load:
            return
        r = analyze(flights)
        w, h = max(c.winfo_width(), 600), max(c.winfo_height(), 300)
        pad_l, pad_b, pad_t = 40, 30, 16
        bw = (w - pad_l - 10) / len(load)
        peak = max(max(load), 1)
        if r and r["result"]:
            s, e, total = r["result"]
            _round_rect(c, pad_l + s * bw - 3, pad_t, pad_l + (e + 1) * bw + 3, h - pad_b, 10,
                        fill=HIGHLIGHT_FILL, outline=HIGHLIGHT_LINE, width=2)
            self.analysis_note.configure(
                text=f"Maximum subarray (divide & conquer): buckets {s}–{e} "
                     f"({hhmm(r['from'])}–{hhmm(r['to'])}), {total} disrupted flights.   "
                     f"O(n²) reference agrees: {r['matches']}")
        else:
            self.analysis_note.configure(text="No disrupted flights yet. Run a scenario to see the analysis.")
        for i, v in enumerate(load):
            if v:
                x0 = pad_l + i * bw
                y0 = h - pad_b - (h - pad_b - pad_t) * v / peak
                _round_rect(c, x0 + 0.5, y0, x0 + bw - 0.5, h - pad_b, 2, fill="#ffb877", outline="")
        c.create_line(pad_l, h - pad_b, w - 10, h - pad_b, fill=LINE)
        for hour in range(0, 25, 3):
            x = pad_l + hour * 12 * bw
            c.create_text(x, h - pad_b + 12, text=f"{hour:02d}:00", fill=MUTED, font=FONT_SMALL)
        c.create_text(pad_l - 8, pad_t, text=str(peak), fill=MUTED, font=FONT_SMALL, anchor="e")

    # ------------------------------------------------------------ tab: routes
    def _tab_routes(self, f):
        top = self._heading(f, "Route matrix")
        self.square = tk.BooleanVar(value=True)
        self.btn_a2 = RoundButton(top, "A × A  (two-leg)", lambda: self._set_square(True))
        self.btn_a1 = RoundButton(top, "A  (direct)", lambda: self._set_square(False))
        self.btn_a2.pack(side="right")
        self.btn_a1.pack(side="right", padx=8)
        self.routes_note = self._label(f, "", anchor="w")
        self.routes_note.pack(fill="x", pady=(0, 8))
        self.heat = tk.Canvas(f, bg=PANEL, highlightthickness=0)
        self.heat.pack(fill="both", expand=True)
        self.heat.bind("<Configure>", lambda _e: self.draw_routes())
        self._set_square(True, redraw=False)

    def _set_square(self, value, redraw=True):
        self.square.set(value)
        self.btn_a2.set_kind("primary" if value else "secondary")
        self.btn_a1.set_kind("secondary" if value else "primary")
        if redraw:
            self.draw_routes()

    def draw_routes(self):
        c = self.heat
        c.delete("all")
        codes, A = build_route_matrix(self.engine.registry.all_flights())
        n = len(codes)
        if n == 0:
            return
        M = A
        if self.square.get():
            M = strassen_multiply(A, A, cutoff=1)
            same = M == classical_multiply(A, A)
            best = max((M[i][j], codes[i], codes[j]) for i in range(n) for j in range(n))
            self.routes_note.configure(
                text=f"A² via Strassen matches classical: {same}   ·   busiest two-leg pair: "
                     f"{best[1]} → ? → {best[2]} ({best[0]} combinations)")
        else:
            self.routes_note.configure(text=f"{n} airports · A[i][j] = flights from row airport to column airport")
        w, h = max(c.winfo_width(), 500), max(c.winfo_height(), 400)
        cell = min((w - 70) / n, (h - 40) / n)
        peak = max(max(row) for row in M) or 1
        for j, code in enumerate(codes):
            c.create_text(60 + j * cell + cell / 2, 12, text=code, fill=MUTED, font=FONT_SMALL)
        for i, code in enumerate(codes):
            c.create_text(30, 28 + i * cell + cell / 2, text=code, fill=MUTED, font=FONT_SMALL)
            for j in range(n):
                v = M[i][j] / peak
                x0, y0 = 60 + j * cell, 28 + i * cell
                _round_rect(c, x0 + 2, y0 + 2, x0 + cell - 2, y0 + cell - 2, 8,
                            fill=_mix(PANEL_2, HEAT_HIGH, v), outline="")
                if cell > 34:
                    c.create_text(x0 + cell / 2, y0 + cell / 2, text=str(M[i][j]), fill=TEXT, font=FONT_SMALL)

    # ------------------------------------------------------------ tab: stats
    def _tab_stats(self, f):
        self._heading(f, "Statistics")
        cols = tk.Frame(f, bg=PANEL); cols.pack(fill="both", expand=True)
        lo, left = self._card(cols, bg=PANEL_2, pad=20)
        lo.pack(side="left", fill="both", expand=True, padx=(0, 12))
        ro, right = self._card(cols, bg=PANEL_2, pad=20)
        ro.pack(side="left", fill="both", expand=True)
        self._label(left, "Hash registry & runway trees", bg=PANEL_2, fg=HEAD, font=FONT_BOLD).pack(anchor="w")
        self.stats_text = self._label(left, "", bg=PANEL_2, font=MONO, justify="left", anchor="nw")
        self.stats_text.pack(fill="both", expand=True, pady=(10, 0))
        self._label(right, "Crisis rule IDs · FKS perfect hashing", bg=PANEL_2, fg=HEAD,
                    font=FONT_BOLD).pack(anchor="w")
        self.ph = PerfectHash(RULE_IDS)
        self._label(right, (f"{len(RULE_IDS)} keys · storage {self.ph.storage()} slots\n"
                            f"retries: level 1 = {self.ph.level1_retries}, level 2 = {self.ph.level2_retries}\n"
                            f"bucket sizes: {self.ph.bucket_sizes()}"),
                    bg=PANEL_2, font=MONO, justify="left", wraplength=420).pack(anchor="w", pady=(10, 12))
        row = tk.Frame(right, bg=PANEL_2); row.pack(anchor="w")
        self.rule_var = tk.StringVar(value="173")
        e = RoundEntry(row, self.rule_var, width=110, bg=PANEL_2, fill=PANEL); e.pack(side="left")
        e.bind_return(self.lookup_rule)
        RoundButton(row, "Look up rule", self.lookup_rule, kind="primary", bg=PANEL_2).pack(side="left", padx=8)
        self.rule_result = self._label(right, "", bg=PANEL_2, font=FONT_BOLD)
        self.rule_result.pack(anchor="w", pady=10)

    def lookup_rule(self):
        try:
            k = int(self.rule_var.get())
        except ValueError:
            return self.rule_result.configure(text="Enter a whole number", fg=STATUS_TEXT["CANCELLED"])
        found = self.ph.contains(k)
        self.rule_result.configure(text=f"Rule {k}: {'present' if found else 'absent'}  (2 hashes, O(1) worst case)",
                                   fg=STATUS_TEXT["SCHEDULED"] if found else STATUS_TEXT["CANCELLED"])

    def draw_stats(self):
        st = self.engine.registry.stats()
        lines = [f"{'size':<14}{st['size']}", f"{'capacity m':<14}{st['capacity']}",
                 f"{'load factor':<14}{st['load_factor']:.3f}", f"{'tombstones':<14}{st['tombstones']}",
                 f"{'collisions':<14}{st['collisions']}", f"{'avg probes':<14}{st['avg_probes']:.2f}", ""]
        for name in sorted(self.engine.runways):
            t = self.engine.runways[name]
            lines.append(f"{name:<6}{t.size:>4} active   height {t.height()}")
        problems = self.engine.check_consistency()
        lines += ["", "consistency: " + ("OK" if not problems else f"{len(problems)} problem(s)")]
        self.stats_text.configure(text="\n".join(lines))

    # ------------------------------------------------------------ actions
    def load_csv(self, path):
        n, errors = self.engine.load(path)
        self.emergency_ids = set()
        self.day = build_load(self.engine.registry.all_flights())[1]
        self.selected = None
        self.detail.configure(text="Click a flight on\nthe timeline", fg=MUTED)
        self.scen_summary.configure(text="")
        self._fill(self.scen_table, [])
        self.status.set(f"Loaded {n} flights from {os.path.basename(path)}" +
                        (f", {len(errors)} rejected" if errors else ""))
        self.refresh()
        self.scroll_to(8 * 60)

    def pick_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if path:
            self.load_csv(path)

    def refresh(self):
        self.draw_timeline()
        self.fill_flights("priority")
        self.draw_analysis()
        self.draw_routes()
        self.draw_stats()

    def find(self):
        fid = self.find_var.get().strip()
        f, probes = self.engine.find(fid)
        if f is None:
            self.detail.configure(text=f"{fid}\nnot found ({probes} probes)", fg=STATUS_TEXT["CANCELLED"])
            self.selected = None
            return
        self.show_flight(f, probes)
        self.select_tab(0)
        if f.status != "CANCELLED":
            midnight = datetime(self.day.year, self.day.month, self.day.day)
            self.scroll_to((f.start - midnight).total_seconds() / 60 - 30)

    def show_flight(self, f, probes=None):
        self.selected = f
        text = (f"{f.flight_id}  ·  {f.airline}\n{f.origin} → {f.destination}\n"
                f"runway {f.runway}  ·  P{f.priority}\n{hhmm(f.start)}–{hhmm(f.end)}\n"
                f"original {hhmm(f.orig_start)}\n{f.status}")
        if probes is not None:
            text += f"\nfound in {probes} probe{'s' if probes != 1 else ''}"
        colour = EMERGENCY_TEXT if f.flight_id in self.emergency_ids else STATUS_TEXT.get(f.status, TEXT)
        self.detail.configure(text=text, fg=colour)

    def cancel_selected(self):
        if not self.selected:
            return
        ok, msg = self.engine.cancel(self.selected.flight_id)
        self.status.set(f"{self.selected.flight_id}: {msg}")
        self.show_flight(self.selected)
        self.refresh()

    def reschedule_selected(self):
        if not self.selected:
            return
        win = tk.Toplevel(self, bg=PANEL, padx=20, pady=18)
        win.title("Reschedule")
        self._label(win, f"New start for {self.selected.flight_id}", font=FONT_BOLD).pack(anchor="w")
        var = tk.StringVar(value=self.selected.start.strftime(TIME_FMT))
        RoundEntry(win, var, width=220).pack(pady=10)

        def go():
            try:
                new = datetime.strptime(var.get().strip(), TIME_FMT)
            except ValueError:
                return messagebox.showerror("Reschedule", "Use YYYY-MM-DD HH:MM", parent=win)
            ok, msg, clashes = self.engine.reschedule(self.selected.flight_id, new)
            extra = (" — conflicts with " + ", ".join(c.flight_id for c in clashes)) if clashes else ""
            self.status.set(f"{self.selected.flight_id}: {msg}{extra}")
            if not ok:
                messagebox.showwarning("Reschedule", msg + extra, parent=win)
                return
            win.destroy()
            self.show_flight(self.selected)
            self.refresh()

        RoundButton(win, "Reschedule", go, kind="primary", width=220).pack()


if __name__ == "__main__":
    App().mainloop()
