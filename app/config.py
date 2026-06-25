import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

CONFIG_DIR = Path.home() / ".copy-trade-tool"
CONFIG_FILE = CONFIG_DIR / "config.json"

SOL_MINT = "So11111111111111111111111111111111111111112"
JUPITER_QUOTE_URL = "https://quote-api.jup.ag/v6/quote"
JUPITER_SWAP_URL = "https://quote-api.jup.ag/v6/swap"


@dataclass
class WalletTarget:
    source_wallet: str = ""
    multiplier: float = 10.0
    label: str = ""

    def display_name(self) -> str:
        if self.label.strip():
            return self.label.strip()
        if self.source_wallet:
            return f"{self.source_wallet[:6]}…{self.source_wallet[-4:]}"
        return "unnamed"


@dataclass
class AppConfig:
    rpc_url: str = "https://api.mainnet-beta.solana.com"
    copy_wallet_key: str = ""
    targets: list[WalletTarget] = field(default_factory=list)
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
            remember_key = bool(data.get("remember_key", False))

            copy_wallet_key = data.get("copy_wallet_key", "")

            targets: list[WalletTarget] = []
            if "targets" in data:
                for item in data["targets"]:
                    if not isinstance(item, dict):
                        continue
                    if not copy_wallet_key and remember_key:
                        copy_wallet_key = item.get("copy_wallet_key", "")
                    targets.append(
                        WalletTarget(
                            source_wallet=item.get("source_wallet", ""),
                            multiplier=float(item.get("multiplier", 10.0)),
                            label=item.get("label", ""),
                        )
                    )
            elif data.get("source_wallet"):
                if not copy_wallet_key:
                    copy_wallet_key = data.get("copy_wallet_key", "") if remember_key else ""
                targets = [
                    WalletTarget(
                        source_wallet=data.get("source_wallet", ""),
                        multiplier=float(data.get("multiplier", 10.0)),
                        label=data.get("label", ""),
                    )
                ]

            if not remember_key:
                copy_wallet_key = ""

            return cls(
                rpc_url=data.get("rpc_url", cls.rpc_url),
                copy_wallet_key=copy_wallet_key,
                targets=targets,
                slippage_bps=int(data.get("slippage_bps", 300)),
                poll_interval_sec=float(data.get("poll_interval_sec", 3.0)),
                min_sol_trade=float(data.get("min_sol_trade", 0.01)),
                remember_key=remember_key,
                dry_run=bool(data.get("dry_run", False)),
            )
        except (json.JSONDecodeError, TypeError, ValueError):
            return cls()

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        payload = asdict(self)
        if not self.remember_key:
            payload["copy_wallet_key"] = ""
        CONFIG_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")