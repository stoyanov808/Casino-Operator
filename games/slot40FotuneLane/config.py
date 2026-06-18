
ROWS = 4
COLS = 5
STRIP_LEN = 120

MAX_WIN_MULTIPLIER = 5000
TARGET_RTP = 96.3

WILD = "WILD"
SCATTER = "SCATTER"

SYMBOL_IDS = [
    "CHERRY",
    "LEMON",
    "ORANGE",
    "GRAPES",
    "STRAWBERRY",
    "WATERMELON",
    "PINEAPPLE",
    "PEACH",
    WILD,
    SCATTER,
]

ASSET_BASE = "https://raw.githubusercontent.com/googlefonts/noto-emoji/main/png/128"

SYMBOL_META = {
    "CHERRY": {
        "label": "Cherry",
        "asset": f"{ASSET_BASE}/emoji_u1f352.png",
    },
    "LEMON": {
        "label": "Lemon",
        "asset": f"{ASSET_BASE}/emoji_u1f34b.png",
    },
    "ORANGE": {
        "label": "Orange",
        "asset": f"{ASSET_BASE}/emoji_u1f34a.png",
    },
    "GRAPES": {
        "label": "Grapes",
        "asset": f"{ASSET_BASE}/emoji_u1f347.png",
    },
    "STRAWBERRY": {
        "label": "Strawberry",
        "asset": f"{ASSET_BASE}/emoji_u1f353.png",
    },
    "WATERMELON": {
        "label": "Watermelon",
        "asset": f"{ASSET_BASE}/emoji_u1f349.png",
    },
    "PINEAPPLE": {
        "label": "Pineapple",
        "asset": f"{ASSET_BASE}/emoji_u1f34d.png",
    },
    "PEACH": {
        "label": "Peach",
        "asset": f"{ASSET_BASE}/emoji_u1f351.png",
    },
    WILD: {
        "label": "Wild",
        "asset": f"{ASSET_BASE}/emoji_u2b50.png",
    },
    SCATTER: {
        "label": "Scatter",
        "asset": f"{ASSET_BASE}/emoji_u1f52e.png",
    },
}

# ------------------------------------------------------------
# SYMBOL GROUPS
# ------------------------------------------------------------

NON_RARE_SYMBOLS = [
    "CHERRY",
    "LEMON",
    "ORANGE",
    "GRAPES",
    "STRAWBERRY",
]

RARE_SYMBOLS = [
    "WATERMELON",
    "PINEAPPLE",
]

RAREST_SYMBOL = "PEACH"

# ------------------------------------------------------------
# PAYTABLE
# ------------------------------------------------------------
#
# These are bet multipliers.
#
# Non-rare symbols:
#   3 = 0.5x
#   4 = 1x
#   5 = 5x
#
# Rare symbols:
#   3 = 1x
#   4 = 2x
#   5 = 10x
#
# Rarest symbol:
#   3 = 2x
#   4 = 5x
#   5 = 50x
#
# Wild pays like the rarest symbol.
# ------------------------------------------------------------

PAYTABLE = {
    # Non-rare symbols
    "CHERRY": {
        3: 0.5,
        4: 1,
        5: 5,
    },
    "LEMON": {
        3: 0.5,
        4: 1,
        5: 5,
    },
    "ORANGE": {
        3: 0.5,
        4: 1,
        5: 5,
    },
    "GRAPES": {
        3: 0.5,
        4: 1,
        5: 5,
    },
    "STRAWBERRY": {
        3: 0.5,
        4: 1,
        5: 5,
    },

    # Rare symbols
    "WATERMELON": {
        3: 1,
        4: 2,
        5: 10,
    },
    "PINEAPPLE": {
        3: 1,
        4: 2,
        5: 10,
    },

    # Rarest symbol
    "PEACH": {
        3: 2,
        4: 5,
        5: 50,
    },

    # Wild pays as rarest symbol
    WILD: {
        3: 2,
        4: 5,
        5: 50,
    },
}

# Scatter payouts stay separate from line-symbol payouts.
SCATTER_PAYOUTS = {
    3: 2,
    4: 10,
    5: 50,
}

# Free spin awards from scatters.
FREE_SPIN_AWARDS = {
    3: 10,
    4: 15,
    5: 20,
}

# ------------------------------------------------------------
# SYMBOL WEIGHT GROUPS
# ------------------------------------------------------------

LOW_FRUITS = [
    "CHERRY",
    "LEMON",
    "ORANGE",
]

MEDIUM_FRUITS = [
    "GRAPES",
    "STRAWBERRY",
]

HIGH_FRUITS = [
    "WATERMELON",
]

PREMIUM_FRUITS = [
    "PINEAPPLE",
    "PEACH",
]

CLUSTER_DROP_SYMBOLS = (
    LOW_FRUITS
    + MEDIUM_FRUITS
    + HIGH_FRUITS
    + PREMIUM_FRUITS
)

# ------------------------------------------------------------
# REEL WEIGHTS
# ------------------------------------------------------------
#
# Order matches SYMBOL_IDS:
#
# CHERRY,
# LEMON,
# ORANGE,
# GRAPES,
# STRAWBERRY,
# WATERMELON,
# PINEAPPLE,
# PEACH,
# WILD,
# SCATTER
# ------------------------------------------------------------

REEL_WEIGHTS = [
    # Reel 1
    [38, 36, 34, 20, 14, 7, 4, 3, 2, 1],

    # Reel 2
    [37, 35, 33, 19, 14, 7, 4, 3, 2, 1],

    # Reel 3
    [46, 43, 40, 14, 9, 4, 2, 1, 2, 1],

    # Reel 4
    [50, 46, 42, 11, 7, 3, 1, 1, 2, 1],

    # Reel 5
    [54, 49, 44, 9, 6, 2, 1, 1, 2, 1],
]

# ------------------------------------------------------------
# CLUSTER DROP WEIGHTS
# ------------------------------------------------------------
#
# Order matches CLUSTER_DROP_SYMBOLS:
#
# CHERRY,
# LEMON,
# ORANGE,
# GRAPES,
# STRAWBERRY,
# WATERMELON,
# PINEAPPLE,
# PEACH
# ------------------------------------------------------------

CLUSTER_DROP_WEIGHTS_BY_REEL = [
    # Reel 1
    [36, 34, 32, 17, 12, 6, 4, 3],

    # Reel 2
    [36, 34, 32, 17, 12, 6, 4, 3],

    # Reel 3
    [44, 40, 36, 11, 7, 3, 2, 1],

    # Reel 4
    [48, 43, 38, 9, 6, 2, 1, 1],

    # Reel 5
    [52, 46, 40, 8, 5, 2, 1, 1],
]

