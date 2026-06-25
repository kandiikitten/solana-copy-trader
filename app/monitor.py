import json
import logging
import threading
from typing import Callable

from solana.rpc.api import Client
from solana.rpc.commitment import Confirmed
from solders.pubkey import Pubkey
from solders.signature import Signature

from app.config import WalletTarget
from app.executor import SwapExecutor
from app.parser import DetectedTrade, parse_swap_from_transaction

logger = logging.getLogger(__name__)


class TradeMonitor:
    def __init__(
        self,
        rpc_url: str,
        source_wallet: str,
        executor: SwapExecutor,
        poll_interval: float,
        min_sol_trade: float,
        label: str = "",
        report_status: bool = True,
        on_trade_detected: Callable[[DetectedTrade, str, float], None] | None = None,
        on_trade_copied: Callable[[dict], None] | None = None,
        on_status: Callable[[str], None] | None = None,
        on_log: Callable[[str], None] | None = None,
    ) -> None:
        self.client = Client(rpc_url)
        self.source = Pubkey.from_string(source_wallet.strip())
        self.source_wallet = source_wallet.strip()
        self.label = label or self.source_wallet[:8] + "…"
        self.executor = executor
        self.poll_interval = poll_interval
        self.min_sol_trade = min_sol_trade
        self.report_status = report_status
        self.on_trade_detected = on_trade_detected or (lambda _t, _s, _m: None)
        self.on_trade_copied = on_trade_copied or (lambda _r: None)
        self.on_status = on_status or (lambda _s: None)
        self.on_log = on_log or (lambda _m: None)

        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._seen: set[str] = set()
        self._bootstrapped = False

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.running:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name=f"monitor-{self.label}")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)
        self._thread = None
        if self.report_status:
            self.on_status("Stopped")

    def _fetch_signatures(self, limit: int = 20) -> list[str]:
        resp = self.client.get_signatures_for_address(self.source, limit=limit, commitment=Confirmed)
        return [str(item.signature) for item in resp.value]

    def _bootstrap_seen(self) -> None:
        for sig in self._fetch_signatures(limit=40):
            self._seen.add(sig)
        self._bootstrapped = True
        self.on_log(f"[{self.label}] watching — skipping {len(self._seen)} past txs")

    def _loop(self) -> None:
        if self.report_status:
            self.on_status("Running")
        if not self._bootstrapped:
            try:
                self._bootstrap_seen()
            except Exception as exc:
                self.on_log(f"[{self.label}] bootstrap failed: {exc}")
                if self.report_status:
                    self.on_status("Error")
                return

        while not self._stop.is_set():
            try:
                signatures = self._fetch_signatures(limit=15)
                new_sigs = [s for s in reversed(signatures) if s not in self._seen]

                for sig in new_sigs:
                    self._seen.add(sig)
                    tx = self.client.get_transaction(
                        Signature.from_string(sig),
                        encoding="jsonParsed",
                        max_supported_transaction_version=0,
                        commitment=Confirmed,
                    )
                    tx_data = None
                    if tx.value is not None:
                        tx_data = json.loads(tx.value.to_json())
                    trade = parse_swap_from_transaction(
                        tx_data,
                        sig,
                        self.source_wallet,
                        self.min_sol_trade,
                    )
                    if not trade:
                        continue

                    mult = self.executor.multiplier
                    self.on_trade_detected(trade, self.label, mult)
                    self.on_log(f"[{self.label}] detected {trade.side.upper()}: {sig[:16]}…")
                    result = self.executor.mirror_trade(trade)
                    result["source_wallet"] = self.source_wallet
                    result["source_label"] = self.label
                    result["multiplier"] = mult
                    self.on_trade_copied(result)
                    if result["success"]:
                        self.on_log(f"[{self.label}] ✓ {result['message']}")
                    else:
                        self.on_log(f"[{self.label}] ✗ {result['message']}")

            except Exception as exc:
                logger.exception("monitor loop error for %s", self.label)
                err = str(exc)
                if "429" in err or "Too Many Requests" in err:
                    self.on_log(f"[{self.label}] RPC rate limited — use a dedicated RPC")
                    self._stop.wait(max(self.poll_interval * 3, 10))
                else:
                    self.on_log(f"[{self.label}] poll error: {exc}")

            self._stop.wait(self.poll_interval)


class MultiTradeMonitor:
    def __init__(
        self,
        rpc_url: str,
        targets: list[WalletTarget],
        slippage_bps: int,
        poll_interval: float,
        min_sol_trade: float,
        dry_run: bool = False,
        on_trade_detected: Callable[[DetectedTrade, str, float], None] | None = None,
        on_trade_copied: Callable[[dict], None] | None = None,
        on_status: Callable[[str], None] | None = None,
        on_log: Callable[[str], None] | None = None,
    ) -> None:
        self.monitors: list[TradeMonitor] = []
        self.on_status = on_status or (lambda _s: None)
        self.on_log = on_log or (lambda _m: None)

        for i, target in enumerate(targets):
            label = target.display_name()
            executor = SwapExecutor(
                rpc_url=rpc_url,
                copy_wallet_key=target.copy_wallet_key,
                multiplier=target.multiplier,
                slippage_bps=slippage_bps,
                dry_run=dry_run,
                on_log=lambda msg, lbl=label: on_log(f"[{lbl}] {msg}") if on_log else None,
            )
            monitor = TradeMonitor(
                rpc_url=rpc_url,
                source_wallet=target.source_wallet,
                executor=executor,
                poll_interval=poll_interval,
                min_sol_trade=min_sol_trade,
                label=label,
                report_status=False,
                on_trade_detected=on_trade_detected,
                on_trade_copied=on_trade_copied,
                on_log=on_log,
            )
            self.monitors.append(monitor)

    @property
    def running(self) -> bool:
        return any(m.running for m in self.monitors)

    def start(self) -> None:
        if self.running:
            return
        if not self.monitors:
            self.on_log("no wallet targets configured")
            return
        self.on_status("Running")
        self.on_log(f"starting {len(self.monitors)} wallet target(s)…")
        for monitor in self.monitors:
            monitor.start()

    def stop(self) -> None:
        for monitor in self.monitors:
            monitor.stop()
        self.on_status("Stopped")

    def executors(self) -> list[SwapExecutor]:
        return [m.executor for m in self.monitors]