"""Model pricing table and cost math.

Prices are USD per million tokens, from https://claude.com/pricing (API tab).
Cache multipliers are applied to the base input price:
  - 5-minute cache write: 1.25x base input
  - 1-hour cache write:   2.00x base input
  - cache read:           0.10x base input
Update PRICES when Anthropic publishes new rates; everything else derives from it.
"""

CACHE_WRITE_5M_MULT = 1.25
CACHE_WRITE_1H_MULT = 2.00
CACHE_READ_MULT = 0.10

# family -> (input $/Mtok, output $/Mtok)
FAMILY_PRICES = {
    "opus": (15.0, 75.0),
    "sonnet": (3.0, 15.0),
    "haiku": (1.0, 5.0),
    "fable": (3.0, 15.0),
}

# Relative capability tier. Used to decide whether a cheaper model could
# plausibly have done the work.
FAMILY_TIER = {"haiku": 1, "fable": 2, "sonnet": 2, "opus": 3}


def family_of(model: str) -> str:
    """Map a raw model id (claude-opus-4-8, claude-haiku-4-5-2025...) to a family."""
    m = (model or "").lower()
    for fam in ("opus", "sonnet", "haiku", "fable"):
        if fam in m:
            return fam
    return "unknown"


def prices_for(model: str):
    """Return (input_price, output_price) per million tokens for a model id."""
    return FAMILY_PRICES.get(family_of(model), (3.0, 15.0))


def cost_of(model, raw_input, cache_write_5m, cache_write_1h, cache_read, output):
    """Cost in USD for one API call's usage numbers."""
    inp, out = prices_for(model)
    per_tok = inp / 1_000_000
    return (
        raw_input * per_tok
        + cache_write_5m * per_tok * CACHE_WRITE_5M_MULT
        + cache_write_1h * per_tok * CACHE_WRITE_1H_MULT
        + cache_read * per_tok * CACHE_READ_MULT
        + output * (out / 1_000_000)
    )


def cost_without_cache(model, raw_input, cache_write_5m, cache_write_1h, cache_read, output):
    """What the same call would have cost with caching disabled entirely.

    Every token that was written-to or read-from cache would instead be billed
    as ordinary input at 1.0x.
    """
    inp, out = prices_for(model)
    total_input = raw_input + cache_write_5m + cache_write_1h + cache_read
    return total_input * (inp / 1_000_000) + output * (out / 1_000_000)
