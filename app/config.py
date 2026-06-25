import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

CONFIG_DIR = Path.home() / ".copy-trade-tool"
CONFIG_FILE = CONFIG_DIR / "config.json"

SOL_MINT = "So11111111111111111111111111111111111111112"
JUPITER_QUOTE_URL = "https://quote-api.jup.ag/v6/quote"
JUPITER_SWAP_URL = "https://quote-api.jup.ag/v6/swap"


@dataclass
class AppConfig:
    rpc_url: str = "https://api.mainnet-beta.solana.com"
    source_wallet: str = ""
    copy_wallet_key: str = ""
    multiplier: float = 10.0
    slippage_bps: int = 300
    poll_interval_sec: float = 3.0
    min_sol_trade: float = 0.01
    remember_key: bool = False
    dry_run: bool = False

    @classmethod
    def load(cls) -> "AppConfig":
        if not CONFIG_FILE.exists():
            return cls()
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            cfg = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
            if not cfg.remember_key:
                cfg.copy_wallet_key = ""
            return cfg
        except (json.JSONDecodeError, TypeError, ValueError):
            return cls()

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        payload = asdict(self)
        if not self.remember_key:
            payload["copy_wallet_key"] = ""
        CONFIG_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")