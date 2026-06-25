import threading
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

import customtkinter as ctk

from app.config import AppConfig
from app.executor import SwapExecutor
from app.monitor import TradeMonitor
from app.parser import DetectedTrade


class Theme:
    """Soft dark + pastel cute palette."""

    BG = "#0c0a12"
    BG_GRADIENT = "#14101f"
    CARD = "#1a1528"
    CARD_HOVER = "#221c34"
    CARD_BORDER = "#2e2548"

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


class CopyTradeApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.config = AppConfig.load()
        self.monitor: TradeMonitor | None = None
        self._status_pulse_job: str | None = None
        self._pulse_on = False

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.title("✨ Copy Trade — 10x Mirror")
        self.geometry("1140x820")
        self.minsize(980, 720)
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
            frame,
            text=f"{emoji}  {title}",
            font=Theme.FONT_HEADING,
            text_color=Theme.TEXT,
            anchor="w",
        ).pack(side="left")
        if subtitle:
            ctk.CTkLabel(
                frame,
                text=subtitle,
                font=Theme.FONT_SMALL,
                text_color=Theme.TEXT_DIM,
                anchor="w",
            ).pack(side="left", padx=(10, 0))

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
        ctk.CTkLabel(lbl_frame, text=label, font=Theme.FONT_BODY, text_color=Theme.TEXT_MUTED, anchor="w").pack(
            side="left"
        )

        entry = ctk.CTkEntry(
            parent,
            placeholder_text=placeholder,
            show=show,
            height=38,
            corner_radius=12,
            border_width=1,
            border_color=Theme.INPUT_BORDER,
            fg_color=Theme.INPUT,
            text_color=Theme.TEXT,
            placeholder_text_color=Theme.TEXT_DIM,
            font=Theme.FONT_BODY,
        )
        entry.grid(row=row, column=1, padx=(8, 18), pady=7, sticky="ew")
        return entry

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
    ) -> ctk.CTkButton:
        return ctk.CTkButton(
            parent,
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
        ctk.CTkLabel(
            title_block,
            text="Copy Trade",
            font=Theme.FONT_TITLE,
            text_color=Theme.TEXT,
        ).pack(anchor="w")
        ctk.CTkLabel(
            title_block,
            text="mirror your trades · 10x on a second wallet ✨",
            font=Theme.FONT_SMALL,
            text_color=Theme.TEXT_MUTED,
        ).pack(anchor="w")

        right = ctk.CTkFrame(header, fg_color="transparent")
        right.grid(row=0, column=2, padx=28, pady=18, sticky="e")

        self.status_pill = self._pill(right, "💤  idle", Theme.CARD_BORDER, Theme.IDLE)
        self.status_pill.pack(side="right", padx=(10, 0))

        self.balance_pill = self._pill(right, "◎  — SOL", Theme.CARD, Theme.MINT)
        self.balance_pill.pack(side="right", padx=(0, 6))

        accent = ctk.CTkFrame(self, height=3, corner_radius=0, fg_color=Theme.PINK)
        accent.grid(row=0, column=0, sticky="sew")

    def _build_body(self) -> None:
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=24, pady=(16, 24))
        body.grid_columnconfigure(0, weight=0, minsize=440)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        left_outer = ctk.CTkScrollableFrame(
            body,
            fg_color="transparent",
            width=440,
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

        wallets = self._card(left_outer)
        wallets.pack(fill="x", pady=(0, 12))
        wallets.grid_columnconfigure(1, weight=1)
        self._section_title(wallets, "👛", "Wallets", "watch + copy", row=0)
        self.source_entry = self._labeled_entry(
            wallets, "Source (watch)", 1, icon="👀", placeholder="Your trading wallet public key"
        )
        self.copy_key_entry = self._labeled_entry(
            wallets,
            "Copy wallet key",
            2,
            icon="🔐",
            show="♡",
            placeholder="Base58 private key — keep it secret!",
        )
        self.show_key_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            wallets,
            text="👁  show private key",
            variable=self.show_key_var,
            command=self._toggle_key_visibility,
            font=Theme.FONT_SMALL,
            text_color=Theme.TEXT_MUTED,
            fg_color=Theme.PINK,
            hover_color=Theme.PINK_SOFT,
            border_color=Theme.CARD_BORDER,
            checkmark_color="#1a1028",
        ).grid(row=3, column=1, padx=18, pady=(0, 14), sticky="w")

        settings = self._card(left_outer)
        settings.pack(fill="x", pady=(0, 12))
        settings.grid_columnconfigure(1, weight=1)
        self._section_title(settings, "✨", "Copy settings", row=0)

        mult_row = ctk.CTkFrame(settings, fg_color="transparent")
        mult_row.grid(row=1, column=0, columnspan=2, padx=18, pady=(4, 0), sticky="ew")
        mult_row.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(mult_row, text="🪄  Multiplier", font=Theme.FONT_BODY, text_color=Theme.TEXT_MUTED).grid(
            row=0, column=0, sticky="w", pady=4
        )
        self.multiplier_label = ctk.CTkLabel(
            mult_row, text="10.0x", font=("Segoe UI", 16, "bold"), text_color=Theme.PINK
        )
        self.multiplier_label.grid(row=0, column=2, sticky="e", padx=(8, 0))

        self.multiplier_slider = ctk.CTkSlider(
            mult_row,
            from_=1,
            to=50,
            number_of_steps=49,
            command=self._on_multiplier_slide,
            button_color=Theme.PINK,
            button_hover_color=Theme.PINK_SOFT,
            progress_color=Theme.LAVENDER,
            fg_color=Theme.INPUT_BORDER,
        )
        self.multiplier_slider.set(10)
        self.multiplier_slider.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(2, 10))

        self.multiplier_entry = ctk.CTkEntry(
            settings,
            placeholder_text="10",
            height=38,
            corner_radius=12,
            border_width=1,
            border_color=Theme.INPUT_BORDER,
            fg_color=Theme.INPUT,
            width=80,
        )
        self.multiplier_entry.grid(row=2, column=1, padx=(8, 18), pady=(0, 6), sticky="w")

        self.slippage_entry = self._labeled_entry(settings, "Slippage (bps)", 3, icon="🌊", placeholder="300")
        self.poll_entry = self._labeled_entry(settings, "Poll interval (s)", 4, icon="⏱", placeholder="3")
        self.min_trade_entry = self._labeled_entry(settings, "Min trade (SOL)", 5, icon="💧", placeholder="0.01")

        opts = ctk.CTkFrame(settings, fg_color="transparent")
        opts.grid(row=6, column=0, columnspan=2, padx=18, pady=(4, 16), sticky="w")

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
            text="💾  remember private key locally",
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
            controls,
            "💾  save",
            self._save_config,
            color=Theme.MINT,
            hover=Theme.LAVENDER,
        ).grid(row=0, column=2, padx=4, sticky="ew")

        warning_card = ctk.CTkFrame(
            left_outer,
            corner_radius=14,
            fg_color="#2a1f14",
            border_width=1,
            border_color="#4a3520",
        )
        warning_card.pack(fill="x", pady=(4, 0))
        ctk.CTkLabel(
            warning_card,
            text="🐱  keep your key safe! use a dedicated copy wallet with only the funds you're okay risking~",
            font=Theme.FONT_SMALL,
            text_color=Theme.PEACH,
            wraplength=390,
            justify="left",
        ).pack(padx=16, pady=12, anchor="w")

        right = self._card(body)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)

        act_header = ctk.CTkFrame(right, fg_color="transparent")
        act_header.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 4))
        ctk.CTkLabel(
            act_header,
            text="📋  Activity",
            font=Theme.FONT_HEADING,
            text_color=Theme.TEXT,
        ).pack(side="left")
        ctk.CTkLabel(
            act_header,
            text="live trade mirror log",
            font=Theme.FONT_SMALL,
            text_color=Theme.TEXT_DIM,
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

        columns = ("time", "side", "token", "source_tx", "status", "copy_tx")
        self.trades_tree = ttk.Treeview(
            trades_tab,
            columns=columns,
            show="headings",
            height=14,
            style="Cute.Treeview",
        )
        headings = {
            "time": "⏰ time",
            "side": "↕ side",
            "token": "🪙 token",
            "source_tx": "📤 source",
            "status": "✓ status",
            "copy_tx": "📥 copy",
        }
        widths = {"time": 72, "side": 52, "token": 108, "source_tx": 120, "status": 72, "copy_tx": 120}
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

        self._append_log("hii~ ready when you are ✨")

    def _on_multiplier_slide(self, value: float) -> None:
        self.multiplier_label.configure(text=f"{value:.1f}x")
        self.multiplier_entry.delete(0, "end")
        self.multiplier_entry.insert(0, str(int(value) if value == int(value) else round(value, 1)))

    def _toggle_key_visibility(self) -> None:
        self.copy_key_entry.configure(show="" if self.show_key_var.get() else "♡")

    def _set_status_pill(self, emoji: str, text: str, bg: str, fg: str) -> None:
        for child in self.status_pill.winfo_children():
            child.destroy()
        ctk.CTkLabel(
            self.status_pill,
            text=f"{emoji}  {text}",
            font=Theme.FONT_SMALL,
            text_color=fg,
        ).pack(padx=14, pady=6)
        self.status_pill.configure(fg_color=bg)

    def _load_config_into_form(self) -> None:
        c = self.config
        self.rpc_entry.insert(0, c.rpc_url)
        self.source_entry.insert(0, c.source_wallet)
        if c.copy_wallet_key:
            self.copy_key_entry.insert(0, c.copy_wallet_key)
        self.multiplier_slider.set(c.multiplier)
        self._on_multiplier_slide(c.multiplier)
        self.slippage_entry.insert(0, str(c.slippage_bps))
        self.poll_entry.insert(0, str(c.poll_interval_sec))
        self.min_trade_entry.insert(0, str(c.min_sol_trade))
        self.dry_run_var.set(c.dry_run)
        self.remember_key_var.set(c.remember_key)

    def _read_form(self) -> AppConfig | None:
        try:
            mult_text = self.multiplier_entry.get().strip() or str(self.multiplier_slider.get())
            multiplier = float(mult_text)
            slippage = int(self.slippage_entry.get().strip() or "300")
            poll = float(self.poll_entry.get().strip() or "3")
            min_trade = float(self.min_trade_entry.get().strip() or "0.01")
        except ValueError:
            messagebox.showerror("oops~", "Multiplier, slippage, poll interval, and min trade need to be numbers.")
            return None

        if multiplier <= 0:
            messagebox.showerror("oops~", "Multiplier has to be greater than 0.")
            return None

        source = self.source_entry.get().strip()
        copy_key = self.copy_key_entry.get().strip()
        if not source or not copy_key:
            messagebox.showerror("missing info~", "Source wallet and copy wallet private key are both needed.")
            return None

        return AppConfig(
            rpc_url=self.rpc_entry.get().strip() or AppConfig.rpc_url,
            source_wallet=source,
            copy_wallet_key=copy_key,
            multiplier=multiplier,
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
        self._append_log("settings saved~ 💾")
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

    def _on_trade_detected(self, trade: DetectedTrade) -> None:
        arrow = "↑" if trade.side == "buy" else "↓"
        self._append_log(
            f"spotted {trade.side} {arrow}  {trade.sol_amount:.4f} SOL ↔ {trade.token_mint[:10]}…"
        )

    def _on_trade_copied(self, result: dict) -> None:
        def _add_row() -> None:
            status = "✓ ok" if result["success"] else "✗ fail"
            side = "🟢 buy" if result["side"] == "buy" else "🔴 sell"
            self.trades_tree.insert(
                "",
                0,
                values=(
                    datetime.now().strftime("%H:%M:%S"),
                    side,
                    result["token_mint"][:10] + "…",
                    result["signature"][:14] + "…",
                    status,
                    (result.get("copy_tx") or "—")[:14] + ("…" if result.get("copy_tx") else ""),
                ),
            )

        self.after(0, _add_row)

    def _set_balance_pill(self, text: str) -> None:
        for child in self.balance_pill.winfo_children():
            child.destroy()
        ctk.CTkLabel(
            self.balance_pill,
            text=text,
            font=Theme.FONT_SMALL,
            text_color=Theme.MINT,
        ).pack(padx=14, pady=6)

    def _refresh_balance(self, executor: SwapExecutor) -> None:
        def _work() -> None:
            try:
                bal = executor.get_sol_balance()
                self.after(0, lambda: self._set_balance_pill(f"◎  {bal:.4f} SOL"))
            except Exception as exc:
                self.after(0, lambda: self._set_balance_pill(f"◎  error"))

        threading.Thread(target=_work, daemon=True).start()

    def _start(self) -> None:
        cfg = self._read_form()
        if not cfg:
            return

        if self.monitor and self.monitor.running:
            messagebox.showinfo("already on~", "Copy trader is already running.")
            return

        confirmed = messagebox.askyesno(
            "ready to go? 🚀",
            f"Mirror trades from your source wallet to the copy wallet at {cfg.multiplier}x.\n\n"
            f"Dry run: {'ON 🧪' if cfg.dry_run else 'OFF'}\n\n"
            "Only continue if the copy wallet is funded and you're okay with the risk~",
        )
        if not confirmed:
            return

        self.config = cfg
        if cfg.remember_key:
            cfg.save()

        executor = SwapExecutor(
            rpc_url=cfg.rpc_url,
            copy_wallet_key=cfg.copy_wallet_key,
            multiplier=cfg.multiplier,
            slippage_bps=cfg.slippage_bps,
            dry_run=cfg.dry_run,
            on_log=self._append_log,
        )

        self.monitor = TradeMonitor(
            rpc_url=cfg.rpc_url,
            source_wallet=cfg.source_wallet,
            executor=executor,
            poll_interval=cfg.poll_interval_sec,
            min_sol_trade=cfg.min_sol_trade,
            on_trade_detected=self._on_trade_detected,
            on_trade_copied=self._on_trade_copied,
            on_status=self._set_status,
            on_log=self._append_log,
        )

        self.monitor.start()
        self._refresh_balance(executor)
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self._append_log(f"started~ mirroring at {cfg.multiplier}x ✨")

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