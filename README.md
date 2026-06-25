# Solana Copy Trader

A desktop GUI tool that mirrors Solana wallet trades onto copy wallets at **per-wallet multipliers** (e.g. 10x, 5x, 20x).

Watch multiple source wallets at once — each with its own copy wallet and multiplier. When a source wallet buys or sells on a DEX, the matching copy wallet automatically executes the same trade through [Jupiter](https://jup.ag/), scaled up.

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)

## Features

- **Real-time monitoring** — watches your source wallet for new swap transactions
- **Multi-wallet copy trading** — watch multiple source wallets simultaneously, each with its own multiplier
- **Jupiter integration** — routes copied trades through Jupiter aggregator
- **Dry run mode** — detect trades without executing swaps
- **Cute dark-mode GUI** — built with CustomTkinter

## How it works

1. Polls your **source wallet** for new on-chain transactions
2. Detects swaps by reading SOL and token balance changes
3. Executes mirrored swaps on each target's **copy wallet** via Jupiter:
   - **Buy:** spends `multiplier ×` the SOL the source wallet spent
   - **Sell:** sells `multiplier ×` the token amount (capped by copy wallet balance)

Only transactions that occur **after** you click Start are copied. Past history is ignored.

## Requirements

- Python 3.10+
- A Solana RPC endpoint (a dedicated RPC like [Helius](https://helius.dev/) or [QuickNode](https://www.quicknode.com/) is strongly recommended — the free public RPC rate-limits heavily)
- One or more **wallet targets**, each with:
  - **Source wallet** — the wallet to watch (public key only)
  - **Copy wallet** — executes mirrored trades for that source (private key + SOL/tokens)
  - **Multiplier** — trade size scale for that pair (e.g. `10`, `5`, `20`)

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
| **Wallet targets** | Add one or more source → copy wallet pairs |
| **Multiplier** (per target) | Trade size scale for that pair (default `10`) |
| **Nickname** (optional) | Friendly label shown in logs |
| **Dry run** | Enable to test detection without sending swaps |

1. Fill in your RPC URL
2. Click **+ add** to create wallet targets (source, copy key, multiplier each)
3. Enable **Dry run** for a first test
4. Click **Start copying** when ready

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