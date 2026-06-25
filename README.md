# Solana Copy Trader

A desktop GUI tool that mirrors your Solana wallet trades onto a second wallet at a configurable multiplier (default **10x**).

When your source wallet buys or sells on a DEX, the copy wallet automatically executes the same trade through [Jupiter](https://jup.ag/) — scaled up.

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)

## Features

- **Real-time monitoring** — watches your source wallet for new swap transactions
- **10x copy trading** — mirrors buys and sells at a configurable multiplier (1x–50x)
- **Jupiter integration** — routes copied trades through Jupiter aggregator
- **Dry run mode** — detect trades without executing swaps
- **Cute dark-mode GUI** — built with CustomTkinter

## How it works

1. Polls your **source wallet** for new on-chain transactions
2. Detects swaps by reading SOL and token balance changes
3. Executes mirrored swaps on your **copy wallet** via Jupiter:
   - **Buy:** spends `multiplier ×` the SOL your source wallet spent
   - **Sell:** sells `multiplier ×` the token amount (capped by copy wallet balance)

Only transactions that occur **after** you click Start are copied. Past history is ignored.

## Requirements

- Python 3.10+
- A Solana RPC endpoint (a dedicated RPC like [Helius](https://helius.dev/) or [QuickNode](https://www.quicknode.com/) is strongly recommended — the free public RPC rate-limits heavily)
- Two wallets:
  - **Source wallet** — the one you trade from (public key only)
  - **Copy wallet** — executes mirrored trades (needs private key + SOL/tokens)

## Installation

```bash
git clone https://github.com/kandiikitten/solana-copy-trader.git
cd solana-copy-trader
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

Or on Windows, double-click `run.bat`.

### Setup in the GUI

| Field | Description |
|-------|-------------|
| **RPC URL** | Your Solana RPC endpoint |
| **Source wallet** | Public key of the wallet to watch |
| **Copy wallet key** | Base58 private key of the wallet that executes copies |
| **Multiplier** | Trade size multiplier (default `10`) |
| **Dry run** | Enable to test detection without sending swaps |

1. Fill in your RPC URL and wallet details
2. Enable **Dry run** for a first test
3. Click **Start copying** when ready

Settings are saved to `~/.copy-trade-tool/config.json`. Private keys are only stored locally if you check "Remember private key."

## Security

- **Never share your private key** or commit it to version control
- Use a **dedicated copy wallet** funded with only what you're willing to risk
- This tool stores keys locally on your machine — you are responsible for securing your system
- Always test with **Dry run** before going live

## Disclaimer

This software is provided as-is with no guarantees. Cryptocurrency trading carries significant financial risk. Copied trades may fail, execute at different prices, or behave unexpectedly due to slippage, liquidity, RPC issues, or network conditions. **Use at your own risk.** The authors are not responsible for any financial losses.

## Project structure

```
solana-copy-trader/
├── main.py              # Entry point
├── run.bat              # Windows launcher
├── requirements.txt
└── app/
    ├── gui.py           # GUI
    ├── monitor.py       # Wallet transaction watcher
    ├── parser.py        # Swap detection from tx data
    ├── executor.py      # Jupiter swap execution
    └── config.py        # Settings persistence
```

## License

MIT — see [LICENSE](LICENSE).