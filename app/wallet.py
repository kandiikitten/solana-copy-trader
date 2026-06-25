"""Load a Solana keypair from a seed phrase or base58 private key."""

import hashlib
import hmac

from mnemonic import Mnemonic
from solders.keypair import Keypair

_MNEMONIC_WORD_COUNTS = {12, 15, 18, 21, 24}
_HARDENED = 0x80000000


def load_keypair(secret: str, account_index: int = 0) -> Keypair:
    text = " ".join(secret.split())
    if not text:
        raise ValueError("Copy wallet secret is empty")

    words = text.lower().split()
    if len(words) in _MNEMONIC_WORD_COUNTS and Mnemonic("english").check(text):
        return _from_mnemonic(text, account_index)

    compact = text.replace(" ", "")
    try:
        return Keypair.from_base58_string(compact)
    except Exception as exc:
        raise ValueError(
            "Invalid copy wallet — paste a valid seed phrase or base58 private key"
        ) from exc


def _from_mnemonic(mnemonic: str, account_index: int) -> Keypair:
    seed = Mnemonic("english").to_seed(mnemonic)
    path = [
        _HARDENED + 44,
        _HARDENED + 501,
        _HARDENED + account_index,
        _HARDENED + 0,
    ]
    private_key = _derive_ed25519_path(seed, path)
    return Keypair.from_seed(private_key)


def _master_key_from_seed(seed: bytes) -> tuple[bytes, bytes]:
    digest = hmac.new(b"ed25519 seed", seed, hashlib.sha512).digest()
    return digest[:32], digest[32:]


def _ckd_priv(parent: tuple[bytes, bytes], index: int) -> tuple[bytes, bytes]:
    if index < _HARDENED:
        raise ValueError("ed25519 derivation requires hardened indexes")
    key, chain = parent
    data = b"\x00" + key + index.to_bytes(4, "big")
    digest = hmac.new(chain, data, hashlib.sha512).digest()
    return digest[:32], digest[32:]


def _derive_ed25519_path(seed: bytes, path: list[int]) -> bytes:
    parent = _master_key_from_seed(seed)
    for index in path:
        parent = _ckd_priv(parent, index)
    return parent[0]