"""Chapter 11: managed API or self-hosted model (MM-131, MM-132).

MM-131 the rent-or-own worksheet: API spend per ticket against a self-hosted server that
       is paid for every hour, busy or idle, plus the ops and on-call time to run it,
       with a capacity line that adds a GPU when traffic needs one.
MM-132 the KV memory estimator, with its assumption printed: full attention on every
       layer. Models that mix sliding-window and full attention layers (vLLM's hybrid
       KV cache docs list gpt-oss and Gemma 2/3 among them) keep less.

Every worksheet input is an EXAMPLE in made-up units, not a measurement or a quote.
The model shape in EXAMPLE_MODEL is illustrative, not a named model's published config.
"""
import math

GIB = 2 ** 30

# --- MM-131: the worksheet (example inputs, simulated units) -----------------
WORKSHEET = dict(
    api_per_ticket=0.50,        # API spend per ticket, all calls included
    gpu_hour=40.0,              # one rented GPU server, per hour
    hours_month=730,            # it is paid for every hour, busy or idle
    tickets_per_gpu_hour=500,   # from a load test at the SLO (example)
    gpu_month_capacity=150_000, # tickets one GPU takes in a month at peak headroom
    ops=2_400.0,                # upgrades, evals, patching: engineer time a month
    on_call=3_000.0,            # a night shift for a server you own
)


def api_cost(tickets, w=WORKSHEET):
    return tickets * w["api_per_ticket"]


def self_host_naive(tickets, w=WORKSHEET):
    """The BREAK: only the hours the GPU is busy, no ops, no on-call."""
    return tickets / w["tickets_per_gpu_hour"] * w["gpu_hour"]


def gpus_needed(tickets, w=WORKSHEET):
    return max(1, math.ceil(tickets / w["gpu_month_capacity"]))


def self_host_full(tickets, w=WORKSHEET):
    """The FIX: every GPU-hour (idle included), ops and on-call."""
    return gpus_needed(tickets, w) * w["gpu_hour"] * w["hours_month"] \
        + w["ops"] + w["on_call"]


def break_even(w=WORKSHEET):
    """Tickets a month where one fully costed GPU equals the API bill."""
    return (w["gpu_hour"] * w["hours_month"] + w["ops"] + w["on_call"]) \
        / w["api_per_ticket"]


# --- MM-132: KV memory --------------------------------------------------------
EXAMPLE_MODEL = dict(params=8e9, layers=32, kv_heads=8, head_dim=128,
                     bytes_per_value=2)          # illustrative shape, 16-bit values


def kv_bytes_per_token(m=EXAMPLE_MODEL, full_layers=None):
    """K and V, per full-attention layer, per KV head, per head dimension."""
    layers = m["layers"] if full_layers is None else full_layers
    return 2 * layers * m["kv_heads"] * m["head_dim"] * m["bytes_per_value"]


def kv_bytes(context, batch, m=EXAMPLE_MODEL, sliding=None):
    """KV memory for `batch` sequences of `context` tokens.

    Assumption: full attention on every layer, unless `sliding` = (layers, window)
    says how many layers only keep the last `window` tokens."""
    if sliding is None:
        return kv_bytes_per_token(m) * context * batch
    sw_layers, window = sliding
    full = kv_bytes_per_token(m, m["layers"] - sw_layers) * context
    sw = kv_bytes_per_token(m, sw_layers) * min(window, context)
    return (full + sw) * batch


def weight_bytes(m=EXAMPLE_MODEL, bits=16):
    return m["params"] * bits / 8


def max_sequences(gpu_gib, context, m=EXAMPLE_MODEL, bits=16, reserve=0.0):
    """An IDEALIZED memory ceiling: sequences of `context` tokens whose KV fits beside
    the weights. reserve: the share of GPU memory kept back for the runtime
    (activations, buffers, graphs); 0 counts none. Compute and the latency SLO can set
    a lower limit than memory does; that is a load test, not this formula."""
    free = gpu_gib * GIB * (1 - reserve) - weight_bytes(m, bits)
    return int(free // kv_bytes(context, 1, m))


def planned_sequences(ceiling, spare=0.25):
    """Plan below the ceiling: keep `spare` of the slots free for peaks and failover."""
    return int(ceiling * (1 - spare))
