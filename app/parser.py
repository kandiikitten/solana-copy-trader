from dataclasses import dataclass
from typing import Any

from app.config import SOL_MINT


@dataclass
class DetectedTrade:
    signature: str
    side: str  # "buy" or "sell"
    token_mint: str
    sol_amount: float
    token_amount: float
    token_decimals: int

    @property
    def scaled_sol_lamports(self) -> int:
        return int(self.sol_amount * 1_000_000_000)

    @property
    def scaled_token_amount(self) -> int:
        return int(self.token_amount * (10**self.token_decimals))


def _find_account_index(account_keys: list[str], wallet: str) -> int | None:
    for i, key in enumerate(account_keys):
        if key == wallet:
            return i
    return None


def _extract_account_keys(tx: dict[str, Any]) -> list[str]:
    message = tx.get("transaction", {}).get("message", {})
    account_keys = message.get("accountKeys", [])
    keys: list[str] = []
    for entry in account_keys:
        if isinstance(entry, str):
            keys.append(entry)
        elif isinstance(entry, dict):
            keys.append(entry.get("pubkey", ""))
    return keys


def parse_swap_from_transaction(
    tx: dict[str, Any] | None,
    signature: str,
    source_wallet: str,
    min_sol_trade: float,
) -> DetectedTrade | None:
    if not tx or tx.get("meta", {}).get("err") is not None:
        return None

    meta = tx["meta"]
    account_keys = _extract_account_keys(tx)
    wallet_index = _find_account_index(account_keys, source_wallet)
    if wallet_index is None:
        return None

    pre_sol = meta["preBalances"][wallet_index] / 1_000_000_000
    post_sol = meta["postBalances"][wallet_index] / 1_000_000_000
    sol_delta = post_sol - pre_sol

    token_changes: dict[str, dict[str, Any]] = {}

    for bal in meta.get("preTokenBalances", []):
        if bal.get("owner") != source_wallet:
            continue
        mint = bal["mint"]
        token_changes.setdefault(mint, {"pre": 0.0, "post": 0.0, "decimals": bal["uiTokenAmount"]["decimals"]})
        token_changes[mint]["pre"] = float(bal["uiTokenAmount"]["uiAmount"] or 0)

    for bal in meta.get("postTokenBalances", []):
        if bal.get("owner") != source_wallet:
            continue
        mint = bal["mint"]
        token_changes.setdefault(mint, {"pre": 0.0, "post": 0.0, "decimals": bal["uiTokenAmount"]["decimals"]})
        token_changes[mint]["post"] = float(bal["uiTokenAmount"]["uiAmount"] or 0)

    best: DetectedTrade | None = None
    best_score = 0.0

    for mint, change in token_changes.items():
        if mint == SOL_MINT:
            continue
        token_delta = change["post"] - change["pre"]
        if abs(token_delta) < 1e-12:
            continue

        if token_delta > 0 and sol_delta < 0:
            side = "buy"
            sol_spent = abs(sol_delta)
            if sol_spent < min_sol_trade:
                continue
            score = sol_spent
            candidate = DetectedTrade(
                signature=signature,
                side=side,
                token_mint=mint,
                sol_amount=sol_spent,
                token_amount=token_delta,
                token_decimals=change["decimals"],
            )
        elif token_delta < 0 and sol_delta > 0:
            side = "sell"
            sol_received = sol_delta
            if sol_received < min_sol_trade:
                continue
            score = sol_received
            candidate = DetectedTrade(
                signature=signature,
                side=side,
                token_mint=mint,
                sol_amount=sol_received,
                token_amount=abs(token_delta),
                token_decimals=change["decimals"],
            )
        else:
            continue

        if score > best_score:
            best_score = score
            best = candidate

    return best