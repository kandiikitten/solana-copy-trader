import threading
from dataclasses import dataclass
from datetime import datetime
from tkinter import messagebox, ttk

import customtkinter as ctk

from app.config import AppConfig, WalletTarget
from app.executor import SwapExecutor
from app.monitor import MultiTradeMonitor
from app.parser import DetectedTrade


class Theme:
    """Soft dark + pastel cute palette."""

    BG = "#0c0a12"
    BG_GRADIENT = "#14101f"
    CARD = "#1a1528"
    CARD_HOVER = "#221c34"
    CARD_BORDER = "#2e2548"
    ROW = "#151020"

    PINK = "#ff8ec8"
    PINK_SOFT = "#f0a6ca"
    LAVENDER = "#b8a9f0"
    MINT = "#7ee8c7"
    PEACH = "#ffc9a8"
    SKY = "#8ec8ff"

    TEXT = "#f8f4ff"
    TEXT_MUTED = "#a89bc4"
    TEXT_DIM = "#6b5f82"

    SUCCESS = "#7ee8a0"
    WARN = "#ffd166"
    ERROR = "#ff8a9b"
    IDLE = "#8b7faa"

    INPUT = "#120f1c"
    INPUT_BORDER = "#3a3058"

    FONT_TITLE = ("Segoe UI", 28, "bold")
    FONT_HEADING = ("Segoe UI", 14, "bold")
    FONT_BODY = ("Segoe UI", 12)
    FONT_SMALL = ("Segoe UI", 11)
    FONT_MONO = ("Cascadia Mono", 11)
    FONT_EMOJI = ("Segoe UI Emoji", 13)


@dataclass
class TargetRowWidgets:
    frame: ctk.CTkFrame
    label_entry: ctk.CTkEntry
    source_entry: ctk.CTkEntry
    copy_key_entry: ctk.CTkEntry
    multiplier_slider: ctk.CTkSlider
    multiplier_label: ctk.CTkLabel


class CopyTradeApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.config = AppConfig.load()
        self.monitor: MultiTradeMonitor | None = None
        self.target_rows: list[TargetRowWidgets] = []
        self._status_pulse_job: str | None = None
        self._pulse_on = False

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.title("✨ Copy Trade — Multi-Wallet Mirror")
        self.geometry("1180x860")
        self.minsize(1020, 760)
        self.configure(fg_color=Theme.BG)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._setup_ttk_styles()
        self._build_header()
        self._build_body()
        self._load_config_into_form()

    def _setup_ttk_styles(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Cute.Treeview",
            background=Theme.INPUT,
            foreground=Theme.TEXT,
            fieldbackground=Theme.INPUT,
            borderwidth=0,
            rowheight=30,
            font=Theme.FONT_SMALL,
        )
        style.configure(
            "Cute.Treeview.Heading",
            background=Theme.CARD_BORDER,
            foreground=Theme.LAVENDER,
            borderwidth=0,
            font=("Segoe UI", 11, "bold"),
        )
        style.map(
            "Cute.Treeview",
            background=[("selected", Theme.CARD_BORDER)],
            foreground=[("selected", Theme.PINK)],
        )
        style.configure(
            "Cute.Vertical.TScrollbar",
            background=Theme.CARD,
            troughcolor=Theme.INPUT,
            borderwidth=0,
            arrowcolor=Theme.LAVENDER,
        )

    def _card(self, parent, **kwargs) -> ctk.CTkFrame:
        return ctk.CTkFrame(
            parent,
            corner_radius=18,
            fg_color=Theme.CARD,
            border_width=1,
            border_color=Theme.CARD_BORDER,
            **kwargs,
        )

    def _pill(self, parent, text: str, color: str, text_color: str = Theme.TEXT) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(parent, corner_radius=20, fg_color=color, height=34)
        ctk.CTkLabel(frame, text=text, font=Theme.FONT_SMALL, text_color=text_color).pack(
            padx=14, pady=6
        )
        return frame

    def _section_title(self, parent, emoji: str, title: str, subtitle: str = "", row: int = 0) -> None:
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=row, column=0, columnspan=2, sticky="ew", padx=18, pady=(16, 4))
        ctk.CTkLabel(
            frame, text=f"{emoji}  {title}", font=Theme.FONT_HEADING, text_color=Theme.TEXT, anchor="w"
        ).pack(side="left")
        if subtitle:
            ctk.CTkLabel(
                frame, text=subtitle, font=Theme.FONT_SMALL, text_color=Theme.TEXT_DIM, anchor="w"
            ).pack(side="left", padx=(10, 0))

    def _entry(self, parent, **kwargs) -> ctk.CTkEntry:
        defaults = dict(
            height=36,
            corner_radius=10,
            border_width=1,
            border_color=Theme.INPUT_BORDER,
            fg_color=Theme.INPUT,
            text_color=Theme.TEXT,
            placeholder_text_color=Theme.TEXT_DIM,
            font=Theme.FONT_BODY,
        )
        defaults.update(kwargs)
        return ctk.CTkEntry(parent, **defaults)

    def _cute_button(
        self,
        parent,
        text: str,
        command,
        *,
        color: str = Theme.PINK,
        hover: str = Theme.PINK_SOFT,
        height: int = 44,
        state: str = "normal",
        width: int | None = None,
    ) -> ctk.CTkButton:
        kwargs = dict(
            text=text,
            command=command,
            height=height,
            corner_radius=14,
            font=("Segoe UI", 13, "bold"),
            fg_color=color,
            hover_color=hover,
            text_color="#1a1028",
            state=state,
        )
        if width is not None:
            kwargs["width"] = width
        return ctk.CTkButton(parent, **kwargs)

    def _labeled_entry(
        self,
        parent,
        label: str,
        row: int,
        *,
        show: str | None = None,
        placeholder: str = "",
        icon: str = "",
    ) -> ctk.CTkEntry:
        lbl_frame = ctk.CTkFrame(parent, fg_color="transparent")
        lbl_frame.grid(row=row, column=0, padx=(18, 8), pady=7, sticky="w")
        if icon:
            ctk.CTkLabel(lbl_frame, text=icon, font=Theme.FONT_EMOJI, width=22).pack(side="left")
        ctk.CTkLabel(
            lbl_frame, text=label, font=Theme.FONT_BODY, text_color=Theme.TEXT_MUTED, anchor="w"
        ).pack(side="left")
        entry = self._entry(parent, placeholder_text=placeholder, show=show)
        entry.grid(row=row, column=1, padx=(8, 18), pady=7, sticky="ew")
        return entry

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, corner_radius=0, fg_color=Theme.BG_GRADIENT, height=88)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(1, weight=1)
        header.grid_propagate(False)

        brand = ctk.CTkFrame(header, fg_color="transparent")
        brand.grid(row=0, column=0, padx=28, pady=18, sticky="w")

        ctk.CTkLabel(brand, text="🌙", font=("Segoe UI Emoji", 32)).pack(side="left", padx=(0, 10))
        title_block = ctk.CTkFrame(brand, fg_color="transparent")
        title_block.pack(side="left")
        ctk.CTkLabel(title_block, text="Copy Trade", font=Theme.FONT_TITLE, text_color=Theme.TEXT).pack(anchor="w")
        ctk.CTkLabel(
            title_block,
            text="mirror multiple wallets · each with its own multiplier ✨",
            font=Theme.FONT_SMALL,
            text_color=Theme.TEXT_MUTED,
        ).pack(anchor="w")

        right = ctk.CTkFrame(header, fg_color="transparent")
        right.grid(row=0, column=2, padx=28, pady=18, sticky="e")

        self.status_pill = self._pill(right, "💤  idle", Theme.CARD_BORDER, Theme.IDLE)
        self.status_pill.pack(side="right", padx=(10, 0))

        self.balance_pill = self._pill(right, "◎  — wallets", Theme.CARD, Theme.MINT)
        self.balance_pill.pack(side="right", padx=(0, 6))

        accent = ctk.CTkFrame(self, height=3, corner_radius=0, fg_color=Theme.PINK)
        accent.grid(row=0, column=0, sticky="sew")

    def _add_target_row(self, target: WalletTarget | None = None) -> None:
        idx = len(self.target_rows) + 1
        row_frame = ctk.CTkFrame(
            self.targets_list,
            corner_radius=14,
            fg_color=Theme.ROW,
            border_width=1,
            border_color=Theme.CARD_BORDER,
        )
        row_frame.pack(fill="x", padx=12, pady=6)
        row_frame.grid_columnconfigure(1, weight=1)

        header = ctk.CTkFrame(row_frame, fg_color="transparent")
        header.grid(row=0, column=0, columnspan=3, sticky="ew", padx=12, pady=(10, 4))
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            header, text=f"👛  wallet #{idx}", font=Theme.FONT_BODY, text_color=Theme.LAVENDER
        ).grid(row=0, column=0, sticky="w")

        label_entry = self._entry(header, placeholder_text="nickname (optional)", width=140)
        label_entry.grid(row=0, column=1, sticky="e", padx=(8, 8))

        def remove_this() -> None:
            self._remove_target_row(row_widgets)

        remove_btn = ctk.CTkButton(
            header,
            text="✕",
            width=32,
            height=28,
            corner_radius=8,
            fg_color=Theme.CARD_BORDER,
            hover_color=Theme.ERROR,
            text_color=Theme.TEXT,
            command=remove_this,
        )
        remove_btn.grid(row=0, column=2, sticky="e")

        ctk.CTkLabel(row_frame, text="👀 source", font=Theme.FONT_SMALL, text_color=Theme.TEXT_DIM).grid(
            row=1, column=0, padx=12, pady=4, sticky="w"
        )
        source_entry = self._entry(row_frame, placeholder_text="source wallet public key")
        source_entry.grid(row=1, column=1, columnspan=2, padx=12, pady=4, sticky="ew")

        ctk.CTkLabel(row_frame, text="🔐 copy key", font=Theme.FONT_SMALL, text_color=Theme.TEXT_DIM).grid(
            row=2, column=0, padx=12, pady=4, sticky="w"
        )
        copy_key_entry = self._entry(row_frame, placeholder_text="copy wallet private key", show="♡")
        copy_key_entry.grid(row=2, column=1, columnspan=2, padx=12, pady=4, sticky="ew")

        mult_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
        mult_frame.grid(row=3, column=0, columnspan=3, sticky="ew", padx=12, pady=(4, 12))
        mult_frame.grid_columnconfigure(0, weight=1)

        mult_top = ctk.CTkFrame(mult_frame, fg_color="transparent")
        mult_top.grid(row=0, column=0, sticky="ew")
        mult_top.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            mult_top, text="🪄 multiplier", font=Theme.FONT_SMALL, text_color=Theme.TEXT_DIM
        ).grid(row=0, column=0, sticky="w")
        multiplier_label = ctk.CTkLabel(
            mult_top, text="10.0x", font=("Segoe UI", 15, "bold"), text_color=Theme.PINK
        )
        multiplier_label.grid(row=0, column=1, sticky="e")

        def on_slide(value: float, lbl: ctk.CTkLabel = multiplier_label) -> None:
            lbl.configure(text=f"{value:.1f}x")

        multiplier_slider = ctk.CTkSlider(
            mult_frame,
            from_=1,
            to=50,
            number_of_steps=49,
            command=on_slide,
            button_color=Theme.PINK,
            button_hover_color=Theme.PINK_SOFT,
            progress_color=Theme.LAVENDER,
            fg_color=Theme.INPUT_BORDER,
        )
        multiplier_slider.set(10)
        multiplier_slider.grid(row=1, column=0, sticky="ew", pady=(6, 0))

        row_widgets = TargetRowWidgets(
            frame=row_frame,
            label_entry=label_entry,
            source_entry=source_entry,
            copy_key_entry=copy_key_entry,
            multiplier_slider=multiplier_slider,
            multiplier_label=multiplier_label,
        )
        self.target_rows.append(row_widgets)

        if target:
            if target.label:
                label_entry.insert(0, target.label)
            source_entry.insert(0, target.source_wallet)
            if target.copy_wallet_key:
                copy_key_entry.insert(0, target.copy_wallet_key)
            self._set_row_multiplier(row_widgets, target.multiplier)

    def _set_row_multiplier(self, row: TargetRowWidgets, value: float) -> None:
        clamped = max(1.0, min(50.0, value))
        row.multiplier_slider.set(clamped)
        row.multiplier_label.configure(text=f"{clamped:.1f}x")

    def _remove_target_row(self, row: TargetRowWidgets) -> None:
        if len(self.target_rows) <= 1:
            messagebox.showinfo("keep one~", "You need at least one wallet target.")
            return
        row.frame.destroy()
        self.target_rows.remove(row)
        self._renumber_target_labels()

    def _renumber_target_labels(self) -> None:
        for i, row in enumerate(self.target_rows, start=1):
            for child in row.frame.winfo_children():
                if isinstance(child, ctk.CTkFrame):
                    for lbl in child.winfo_children():
                        if isinstance(lbl, ctk.CTkLabel) and "wallet #" in str(lbl.cget("text")):
                            lbl.configure(text=f"👛  wallet #{i}")

    def _build_body(self) -> None:
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=24, pady=(16, 24))
        body.grid_columnconfigure(0, weight=0, minsize=460)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        left_outer = ctk.CTkScrollableFrame(
            body,
            fg_color="transparent",
            width=460,
            scrollbar_button_color=Theme.CARD_BORDER,
            scrollbar_button_hover_color=Theme.LAVENDER,
        )
        left_outer.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        left_outer.grid_columnconfigure(0, weight=1)

        conn = self._card(left_outer)
        conn.pack(fill="x", pady=(0, 12))
        conn.grid_columnconfigure(1, weight=1)
        self._section_title(conn, "🌐", "Connection", "RPC endpoint", row=0)
        self.rpc_entry = self._labeled_entry(
            conn, "RPC URL", 1, icon="🔗", placeholder="https://your-fast-rpc.solana.com"
        )

        targets_card = self._card(left_outer)
        targets_card.pack(fill="x", pady=(0, 12))
        targets_card.grid_columnconfigure(0, weight=1)

        targets_header = ctk.CTkFrame(targets_card, fg_color="transparent")
        targets_header.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 4))
        targets_header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            targets_header,
            text="👛  Wallet targets",
            font=Theme.FONT_HEADING,
            text_color=Theme.TEXT,
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            targets_header,
            text="each source → copy wallet + multiplier",
            font=Theme.FONT_SMALL,
            text_color=Theme.TEXT_DIM,
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))
        self._cute_button(
            targets_header,
            "+ add",
            self._add_target_row,
            color=Theme.LAVENDER,
            hover=Theme.PINK_SOFT,
            height=32,
            width=72,
        ).grid(row=0, column=1, rowspan=2, sticky="e")

        self.targets_list = ctk.CTkFrame(targets_card, fg_color="transparent")
        self.targets_list.grid(row=1, column=0, sticky="ew", pady=(4, 8))
        self.targets_list.grid_columnconfigure(0, weight=1)

        self.show_key_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            targets_card,
            text="👁  show all private keys",
            variable=self.show_key_var,
            command=self._toggle_key_visibility,
            font=Theme.FONT_SMALL,
            text_color=Theme.TEXT_MUTED,
            fg_color=Theme.PINK,
            hover_color=Theme.PINK_SOFT,
            border_color=Theme.CARD_BORDER,
            checkmark_color="#1a1028",
        ).grid(row=2, column=0, padx=18, pady=(0, 14), sticky="w")

        settings = self._card(left_outer)
        settings.pack(fill="x", pady=(0, 12))
        settings.grid_columnconfigure(1, weight=1)
        self._section_title(settings, "✨", "Global settings", row=0)

        self.slippage_entry = self._labeled_entry(settings, "Slippage (bps)", 1, icon="🌊", placeholder="300")
        self.poll_entry = self._labeled_entry(settings, "Poll interval (s)", 2, icon="⏱", placeholder="3")
        self.min_trade_entry = self._labeled_entry(settings, "Min trade (SOL)", 3, icon="💧", placeholder="0.01")

        opts = ctk.CTkFrame(settings, fg_color="transparent")
        opts.grid(row=4, column=0, columnspan=2, padx=18, pady=(4, 16), sticky="w")

        self.dry_run_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            opts,
            text="🧪  dry run — detect only, no swaps",
            variable=self.dry_run_var,
            font=Theme.FONT_SMALL,
            text_color=Theme.TEXT_MUTED,
            fg_color=Theme.SKY,
            hover_color=Theme.LAVENDER,
            border_color=Theme.CARD_BORDER,
            checkmark_color="#1a1028",
        ).pack(anchor="w", pady=3)

        self.remember_key_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            opts,
            text="💾  remember private keys locally",
            variable=self.remember_key_var,
            font=Theme.FONT_SMALL,
            text_color=Theme.TEXT_MUTED,
            fg_color=Theme.MINT,
            hover_color=Theme.LAVENDER,
            border_color=Theme.CARD_BORDER,
            checkmark_color="#1a1028",
        ).pack(anchor="w", pady=3)

        controls = ctk.CTkFrame(left_outer, fg_color="transparent")
        controls.pack(fill="x", pady=(4, 8))
        controls.grid_columnconfigure((0, 1, 2), weight=1)

        self.start_btn = self._cute_button(controls, "🚀  start copying", self._start)
        self.start_btn.grid(row=0, column=0, padx=4, sticky="ew")

        self.stop_btn = self._cute_button(
            controls,
            "💤  stop",
            self._stop,
            color=Theme.CARD_BORDER,
            hover=Theme.TEXT_DIM,
            state="disabled",
        )
        self.stop_btn.grid(row=0, column=1, padx=4, sticky="ew")

        self._cute_button(
            controls, "💾  save", self._save_config, color=Theme.MINT, hover=Theme.LAVENDER
        ).grid(row=0, column=2, padx=4, sticky="ew")

        warning_card = ctk.CTkFrame(
            left_outer, corner_radius=14, fg_color="#2a1f14", border_width=1, border_color="#4a3520"
        )
        warning_card.pack(fill="x", pady=(4, 0))
        ctk.CTkLabel(
            warning_card,
            text="🐱  each target can use a different copy wallet + multiplier. never share your private keys~",
            font=Theme.FONT_SMALL,
            text_color=Theme.PEACH,
            wraplength=410,
            justify="left",
        ).pack(padx=16, pady=12, anchor="w")

        right = self._card(body)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)

        act_header = ctk.CTkFrame(right, fg_color="transparent")
        act_header.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 4))
        ctk.CTkLabel(act_header, text="📋  Activity", font=Theme.FONT_HEADING, text_color=Theme.TEXT).pack(
            side="left"
        )
        ctk.CTkLabel(
            act_header, text="live trade mirror log", font=Theme.FONT_SMALL, text_color=Theme.TEXT_DIM
        ).pack(side="left", padx=(10, 0))

        self.tabview = ctk.CTkTabview(
            right,
            corner_radius=14,
            fg_color=Theme.INPUT,
            segmented_button_fg_color=Theme.CARD_BORDER,
            segmented_button_selected_color=Theme.PINK,
            segmented_button_selected_hover_color=Theme.PINK_SOFT,
            segmented_button_unselected_color=Theme.CARD,
            segmented_button_unselected_hover_color=Theme.CARD_HOVER,
            text_color=Theme.TEXT,
        )
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=14, pady=(4, 14))
        trades_tab = self.tabview.add("✦  trades")
        log_tab = self.tabview.add("♡  log")

        trades_tab.grid_columnconfigure(0, weight=1)
        trades_tab.grid_rowconfigure(0, weight=1)
        log_tab.grid_columnconfigure(0, weight=1)
        log_tab.grid_rowconfigure(0, weight=1)

        columns = ("time", "source", "mult", "side", "token", "status", "copy_tx")
        self.trades_tree = ttk.Treeview(
            trades_tab, columns=columns, show="headings", height=14, style="Cute.Treeview"
        )
        headings = {
            "time": "⏰",
            "source": "👛",
            "mult": "✦",
            "side": "↕",
            "token": "🪙",
            "status": "✓",
            "copy_tx": "📥",
        }
        widths = {"time": 62, "source": 88, "mult": 36, "side": 52, "token": 100, "status": 56, "copy_tx": 110}
        for col in columns:
            self.trades_tree.heading(col, text=headings[col])
            self.trades_tree.column(col, width=widths[col], anchor="w")
        self.trades_tree.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)

        scroll_trades = ttk.Scrollbar(
            trades_tab, orient="vertical", command=self.trades_tree.yview, style="Cute.Vertical.TScrollbar"
        )
        self.trades_tree.configure(yscrollcommand=scroll_trades.set)
        scroll_trades.grid(row=0, column=1, sticky="ns", pady=6)

        self.log_box = ctk.CTkTextbox(
            log_tab,
            font=Theme.FONT_MONO,
            corner_radius=12,
            fg_color=Theme.BG,
            border_width=1,
            border_color=Theme.CARD_BORDER,
            text_color=Theme.MINT,
            scrollbar_button_color=Theme.CARD_BORDER,
            scrollbar_button_hover_color=Theme.LAVENDER,
        )
        self.log_box.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        self.log_box.configure(state="disabled")

        self._append_log("hii~ add wallet targets and hit start ✨")

    def _toggle_key_visibility(self) -> None:
        show = "" if self.show_key_var.get() else "♡"
        for row in self.target_rows:
            row.copy_key_entry.configure(show=show)

    def _set_status_pill(self, emoji: str, text: str, bg: str, fg: str) -> None:
        for child in self.status_pill.winfo_children():
            child.destroy()
        ctk.CTkLabel(
            self.status_pill, text=f"{emoji}  {text}", font=Theme.FONT_SMALL, text_color=fg
        ).pack(padx=14, pady=6)
        self.status_pill.configure(fg_color=bg)

    def _clear_target_rows(self) -> None:
        for row in self.target_rows:
            row.frame.destroy()
        self.target_rows.clear()

    def _load_config_into_form(self) -> None:
        c = self.config
        self.rpc_entry.insert(0, c.rpc_url)
        self.slippage_entry.insert(0, str(c.slippage_bps))
        self.poll_entry.insert(0, str(c.poll_interval_sec))
        self.min_trade_entry.insert(0, str(c.min_sol_trade))
        self.dry_run_var.set(c.dry_run)
        self.remember_key_var.set(c.remember_key)

        self._clear_target_rows()
        if c.targets:
            for target in c.targets:
                self._add_target_row(target)
        else:
            self._add_target_row()

    def _read_targets(self) -> list[WalletTarget] | None:
        targets: list[WalletTarget] = []
        seen_sources: set[str] = set()

        for i, row in enumerate(self.target_rows, start=1):
            source = row.source_entry.get().strip()
            copy_key = row.copy_key_entry.get().strip()
            label = row.label_entry.get().strip()
            multiplier = float(row.multiplier_slider.get())

            if not source and not copy_key:
                continue

            if not source or not copy_key:
                messagebox.showerror(
                    "incomplete target~",
                    f"Wallet #{i} needs both a source wallet and copy wallet key.",
                )
                return None

            if multiplier <= 0:
                messagebox.showerror("oops~", f"Wallet #{i} multiplier must be greater than 0.")
                return None

            if source in seen_sources:
                messagebox.showerror("duplicate~", f"Wallet #{i} source is already being watched.")
                return None
            seen_sources.add(source)

            targets.append(
                WalletTarget(
                    source_wallet=source,
                    copy_wallet_key=copy_key,
                    multiplier=multiplier,
                    label=label,
                )
            )

        if not targets:
            messagebox.showerror("no targets~", "Add at least one complete wallet target.")
            return None

        return targets

    def _read_form(self) -> AppConfig | None:
        try:
            slippage = int(self.slippage_entry.get().strip() or "300")
            poll = float(self.poll_entry.get().strip() or "3")
            min_trade = float(self.min_trade_entry.get().strip() or "0.01")
        except ValueError:
            messagebox.showerror("oops~", "Slippage, poll interval, and min trade need to be numbers.")
            return None

        targets = self._read_targets()
        if targets is None:
            return None

        return AppConfig(
            rpc_url=self.rpc_entry.get().strip() or AppConfig.rpc_url,
            targets=targets,
            slippage_bps=slippage,
            poll_interval_sec=poll,
            min_sol_trade=min_trade,
            remember_key=self.remember_key_var.get(),
            dry_run=self.dry_run_var.get(),
        )

    def _save_config(self) -> None:
        cfg = self._read_form()
        if not cfg:
            return
        cfg.save()
        self.config = cfg
        self._append_log(f"settings saved — {len(cfg.targets)} target(s) 💾")
        messagebox.showinfo("saved~", "Settings tucked away in ~/.copy-trade-tool/config.json")

    def _append_log(self, message: str) -> None:
        def _write() -> None:
            stamp = datetime.now().strftime("%H:%M:%S")
            self.log_box.configure(state="normal")
            self.log_box.insert("end", f"♡ {stamp}  {message}\n")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")

        self.after(0, _write)

    def _pulse_status(self) -> None:
        if self._status_pulse_job is None:
            return
        self._pulse_on = not self._pulse_on
        bg = Theme.SUCCESS if self._pulse_on else "#1e3d2a"
        self.status_pill.configure(fg_color=bg)
        self._status_pulse_job = self.after(700, self._pulse_status)

    def _start_status_pulse(self) -> None:
        self._stop_status_pulse()
        self._status_pulse_job = self.after(700, self._pulse_status)

    def _stop_status_pulse(self) -> None:
        if self._status_pulse_job:
            self.after_cancel(self._status_pulse_job)
            self._status_pulse_job = None

    def _set_status(self, status: str) -> None:
        mapping = {
            "Running": ("✦", "mirroring", "#1e3d2a", Theme.SUCCESS),
            "Stopped": ("💤", "stopped", Theme.CARD_BORDER, Theme.IDLE),
            "Idle": ("💤", "idle", Theme.CARD_BORDER, Theme.IDLE),
            "Error": ("⚡", "error", "#3d1e28", Theme.ERROR),
        }
        emoji, label, bg, fg = mapping.get(status, ("·", status.lower(), Theme.CARD_BORDER, Theme.IDLE))

        def _apply() -> None:
            self._set_status_pill(emoji, label, bg, fg)
            if status == "Running":
                self._start_status_pulse()
            else:
                self._stop_status_pulse()

        self.after(0, _apply)

    def _on_trade_detected(self, trade: DetectedTrade, label: str, multiplier: float) -> None:
        arrow = "↑" if trade.side == "buy" else "↓"
        self._append_log(
            f"[{label}] spotted {trade.side} {arrow} @ {multiplier}x — "
            f"{trade.sol_amount:.4f} SOL ↔ {trade.token_mint[:10]}…"
        )

    def _on_trade_copied(self, result: dict) -> None:
        def _add_row() -> None:
            status = "✓ ok" if result["success"] else "✗ fail"
            side = "🟢 buy" if result["side"] == "buy" else "🔴 sell"
            label = result.get("source_label", result.get("source_wallet", "?")[:8])
            mult = result.get("multiplier", "?")
            self.trades_tree.insert(
                "",
                0,
                values=(
                    datetime.now().strftime("%H:%M:%S"),
                    label,
                    f"{mult}x",
                    side,
                    result["token_mint"][:10] + "…",
                    status,
                    (result.get("copy_tx") or "—")[:14] + ("…" if result.get("copy_tx") else ""),
                ),
            )

        self.after(0, _add_row)

    def _set_balance_pill(self, text: str) -> None:
        for child in self.balance_pill.winfo_children():
            child.destroy()
        ctk.CTkLabel(
            self.balance_pill, text=text, font=Theme.FONT_SMALL, text_color=Theme.MINT
        ).pack(padx=14, pady=6)

    def _refresh_balances(self, executors: list[SwapExecutor]) -> None:
        def _work() -> None:
            try:
                unique: dict[str, SwapExecutor] = {}
                for ex in executors:
                    unique[str(ex.pubkey)] = ex
                parts = []
                for ex in unique.values():
                    bal = ex.get_sol_balance()
                    short = str(ex.pubkey)[:4] + "…"
                    parts.append(f"{short} {bal:.3f}")
                text = "◎  " + " · ".join(parts) if parts else "◎  —"
                self.after(0, lambda: self._set_balance_pill(text))
            except Exception:
                self.after(0, lambda: self._set_balance_pill("◎  error"))

        threading.Thread(target=_work, daemon=True).start()

    def _start(self) -> None:
        cfg = self._read_form()
        if not cfg:
            return

        if self.monitor and self.monitor.running:
            messagebox.showinfo("already on~", "Copy trader is already running.")
            return

        summary = "\n".join(
            f"  • {t.display_name()} → {t.multiplier}x" for t in cfg.targets
        )
        confirmed = messagebox.askyesno(
            "ready to go? 🚀",
            f"Mirror {len(cfg.targets)} wallet target(s):\n{summary}\n\n"
            f"Dry run: {'ON 🧪' if cfg.dry_run else 'OFF'}\n\n"
            "Only continue if copy wallets are funded and you're okay with the risk~",
        )
        if not confirmed:
            return

        self.config = cfg
        if cfg.remember_key:
            cfg.save()

        self.monitor = MultiTradeMonitor(
            rpc_url=cfg.rpc_url,
            targets=cfg.targets,
            slippage_bps=cfg.slippage_bps,
            poll_interval=cfg.poll_interval_sec,
            min_sol_trade=cfg.min_sol_trade,
            dry_run=cfg.dry_run,
            on_trade_detected=self._on_trade_detected,
            on_trade_copied=self._on_trade_copied,
            on_status=self._set_status,
            on_log=self._append_log,
        )

        self.monitor.start()
        self._refresh_balances(self.monitor.executors())
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self._append_log(f"started~ watching {len(cfg.targets)} wallet(s) ✨")

    def _stop(self) -> None:
        if self.monitor:
            self.monitor.stop()
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self._append_log("stopped~ see you next time 💤")

    def on_closing(self) -> None:
        self._stop_status_pulse()
        if self.monitor:
            self.monitor.stop()
        self.destroy()


def run_app() -> None:
    app = CopyTradeApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()