import base64
import logging
from typing import Callable

import requests
from solana.rpc.api import Client
from solana.rpc.commitment import Confirmed
from solana.rpc.types import TokenAccountOpts
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction

from app.config import JUPITER_QUOTE_URL, JUPITER_SWAP_URL, SOL_MINT
from app.parser import DetectedTrade
from app.wallet import load_keypair

logger = logging.getLogger(__name__)


class SwapExecutor:
    def __init__(
        self,
        rpc_url: str,
        copy_wallet_key: str,
        multiplier: float,
        slippage_bps: int,
        dry_run: bool = False,
        on_log: Callable[[str], None] | None = None,
    ) -> None:
        self.client = Client(rpc_url)
        self.keypair = load_keypair(copy_wallet_key)
        self.pubkey = self.keypair.pubkey()
        self.multiplier = multiplier
        self.slippage_bps = slippage_bps
        self.dry_run = dry_run
        self.on_log = on_log or (lambda _msg: None)

    def get_sol_balance(self) -> float:
        resp = self.client.get_balance(self.pubkey, commitment=Confirmed)
        return resp.value / 1_000_000_000

    def get_token_balance(self, mint: str) -> float:
        mint_pk = Pubkey.from_string(mint)
        resp = self.client.get_token_accounts_by_owner_json_parsed(
            self.pubkey,
            TokenAccountOpts(mint=mint_pk),
            commitment=Confirmed,
        )
        total = 0.0
        for account in resp.value:
            parsed = account.account.data.parsed
            amount = parsed["info"]["tokenAmount"]["uiAmount"]
            if amount is not None:
                total += float(amount)
        return total

    def _quote_and_swap(self, input_mint: str, output_mint: str, amount: int) -> str | None:
        quote_resp = requests.get(
            JUPITER_QUOTE_URL,
            params={
                "inputMint": input_mint,
                "outputMint": output_mint,
                "amount": amount,
                "slippageBps": self.slippage_bps,
            },
            timeout=30,
        )
        quote_resp.raise_for_status()
        quote = quote_resp.json()
        if not quote.get("routePlan"):
            return None

        swap_resp = requests.post(
            JUPITER_SWAP_URL,
            json={
                "quoteResponse": quote,
                "userPublicKey": str(self.pubkey),
                "wrapAndUnwrapSol": True,
                "dynamicComputeUnitLimit": True,
                "prioritizationFeeLamports": "auto",
            },
            timeout=30,
        )
        swap_resp.raise_for_status()
        swap_tx_b64 = swap_resp.json().get("swapTransaction")
        if not swap_tx_b64:
            return None

        raw = base64.b64decode(swap_tx_b64)
        tx = VersionedTransaction.from_bytes(raw)
        signed = VersionedTransaction(tx.message, [self.keypair])
        send_resp = self.client.send_raw_transaction(bytes(signed))
        return str(send_resp.value)

    def mirror_trade(self, trade: DetectedTrade) -> dict:
        result = {
            "success": False,
            "signature": trade.signature,
            "side": trade.side,
            "token_mint": trade.token_mint,
            "message": "",
            "copy_tx": None,
        }

        try:
            if trade.side == "buy":
                scaled_sol = trade.sol_amount * self.multiplier
                reserve = 0.02 * self.multiplier
                balance = self.get_sol_balance()
                if balance < scaled_sol + reserve:
                    scaled_sol = max(0, balance - reserve)
                if scaled_sol < 0.005:
                    result["message"] = f"Insufficient SOL (have {balance:.4f}, need ~{trade.sol_amount * self.multiplier:.4f})"
                    return result

                amount_lamports = int(scaled_sol * 1_000_000_000)
                self.on_log(
                    f"BUY {trade.token_mint[:8]}… | source {trade.sol_amount:.4f} SOL → copy {scaled_sol:.4f} SOL ({self.multiplier}x)"
                )
                if self.dry_run:
                    result["success"] = True
                    result["message"] = "Dry run — buy simulated"
                    return result

                copy_tx = self._quote_and_swap(SOL_MINT, trade.token_mint, amount_lamports)
                if not copy_tx:
                    result["message"] = "Jupiter returned no route for buy"
                    return result
                result["success"] = True
                result["copy_tx"] = copy_tx
                result["message"] = f"Copied buy at {self.multiplier}x"
                return result

            scaled_tokens = trade.token_amount * self.multiplier
            held = self.get_token_balance(trade.token_mint)
            if held <= 0:
                result["message"] = f"No {trade.token_mint[:8]}… balance to sell"
                return result
            if scaled_tokens > held:
                scaled_tokens = held

            raw_amount = int(scaled_tokens * (10**trade.token_decimals))
            if raw_amount <= 0:
                result["message"] = "Scaled sell amount too small"
                return result

            self.on_log(
                f"SELL {trade.token_mint[:8]}… | source {trade.token_amount:.4f} → copy {scaled_tokens:.4f} tokens ({self.multiplier}x)"
            )
            if self.dry_run:
                result["success"] = True
                result["message"] = "Dry run — sell simulated"
                return result

            copy_tx = self._quote_and_swap(trade.token_mint, SOL_MINT, raw_amount)
            if not copy_tx:
                result["message"] = "Jupiter returned no route for sell"
                return result
            result["success"] = True
            result["copy_tx"] = copy_tx
            result["message"] = f"Copied sell at {self.multiplier}x"
            return result

        except Exception as exc:
            logger.exception("mirror_trade failed")
            result["message"] = str(exc)
            return result