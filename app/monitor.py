import json
import logging
import threading
import time
from typing import Callable

from solana.rpc.api import Client
from solana.rpc.commitment import Confirmed
from solders.pubkey import Pubkey
from solders.signature import Signature

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
        on_trade_detected: Callable[[DetectedTrade], None] | None = None,
        on_trade_copied: Callable[[dict], None] | None = None,
        on_status: Callable[[str], None] | None = None,
        on_log: Callable[[str], None] | None = None,
    ) -> None:
        self.client = Client(rpc_url)
        self.source = Pubkey.from_string(source_wallet.strip())
        self.executor = executor
        self.poll_interval = poll_interval
        self.min_sol_trade = min_sol_trade
        self.on_trade_detected = on_trade_detected or (lambda _t: None)
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
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)
        self._thread = None
        self.on_status("Stopped")

    def _fetch_signatures(self, limit: int = 20) -> list[str]:
        resp = self.client.get_signatures_for_address(self.source, limit=limit, commitment=Confirmed)
        return [str(item.signature) for item in resp.value]

    def _bootstrap_seen(self) -> None:
        for sig in self._fetch_signatures(limit=40):
            self._seen.add(sig)
        self._bootstrapped = True
        self.on_log(f"Watching {self.source} — ignoring {len(self._seen)} past transactions")

    def _loop(self) -> None:
        self.on_status("Running")
        if not self._bootstrapped:
            try:
                self._bootstrap_seen()
            except Exception as exc:
                self.on_log(f"Bootstrap failed: {exc}")
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
                        str(self.source),
                        self.min_sol_trade,
                    )
                    if not trade:
                        continue

                    self.on_trade_detected(trade)
                    self.on_log(f"Detected {trade.side.upper()} on source: {sig[:16]}…")
                    result = self.executor.mirror_trade(trade)
                    self.on_trade_copied(result)
                    if result["success"]:
                        self.on_log(f"✓ {result['message']}")
                    else:
                        self.on_log(f"✗ Copy failed: {result['message']}")

            except Exception as exc:
                logger.exception("monitor loop error")
                err = str(exc)
                if "429" in err or "Too Many Requests" in err:
                    self.on_log("RPC rate limited — use a dedicated RPC (Helius, QuickNode, etc.)")
                    self._stop.wait(max(self.poll_interval * 3, 10))
                else:
                    self.on_log(f"Poll error: {exc}")

            self._stop.wait(self.poll_interval)