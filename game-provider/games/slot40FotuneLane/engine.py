import random
from functools import reduce
from operator import mul

from games.slot40FotuneLane.config import (
    CLUSTER_DROP_SYMBOLS,
    CLUSTER_DROP_WEIGHTS_BY_REEL,
    COLS,
    FREE_SPIN_AWARDS,
    HIGH_FRUITS,
    LOW_FRUITS,
    MAX_WIN_MULTIPLIER,
    MEDIUM_FRUITS,
    PAYTABLE,
    PREMIUM_FRUITS,
    REEL_WEIGHTS,
    ROWS,
    SCATTER,
    SCATTER_PAYOUTS,
    STRIP_LEN,
    SYMBOL_IDS,
    WILD,
)
from games.slot40FotuneLane.paylines import PAYLINES


def build_reel_strip(reel_index):
    return random.choices(
        SYMBOL_IDS,
        weights=REEL_WEIGHTS[reel_index],
        k=STRIP_LEN,
    )


def neighbors(r, c):
    for nr, nc in [(r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)]:
        if 0 <= nr < ROWS and 0 <= nc < COLS:
            yield nr, nc


def pick_cluster_fruit_for_reel(col):
    return random.choices(
        CLUSTER_DROP_SYMBOLS,
        weights=CLUSTER_DROP_WEIGHTS_BY_REEL[col],
        k=1,
    )[0]


def reel_spread_penalty(fruit, col):
    if fruit in PREMIUM_FRUITS:
        return [1.0, 1.0, 0.24, 0.16, 0.10][col]

    if fruit in HIGH_FRUITS:
        return [1.0, 1.0, 0.38, 0.27, 0.20][col]

    if fruit in MEDIUM_FRUITS:
        return [1.0, 1.0, 0.58, 0.47, 0.38][col]

    return [1.0, 1.0, 0.84, 0.78, 0.72][col]


def apply_cluster_style_drop(grid, mode="base"):
    full_screen_chance = 0.00006 if mode == "base" else 0.00016

    if random.random() < full_screen_chance:
        fruit = random.choice(LOW_FRUITS)

        for r in range(ROWS):
            for c in range(COLS):
                grid[r][c] = fruit

        return grid

    blob_count = random.choices(
        [0, 1, 2],
        weights=[48, 44, 8] if mode == "base" else [34, 54, 12],
        k=1,
    )[0]

    for _ in range(blob_count):
        start_c = random.randint(0, COLS - 1)
        start_r = random.randint(0, ROWS - 1)
        fruit = pick_cluster_fruit_for_reel(start_c)

        if grid[start_r][start_c] == SCATTER and random.random() < 0.82:
            continue

        grid[start_r][start_c] = fruit
        frontier = [(start_r, start_c)]

        steps = random.randint(1, 3)

        for depth in range(steps):
            new_frontier = []

            for r, c in frontier:
                for nr, nc in neighbors(r, c):
                    base_spread = max(0.08, 0.30 - depth * 0.075)

                    if nc >= 2:
                        base_spread *= 0.66

                    if random.random() < base_spread:
                        penalty = reel_spread_penalty(fruit, nc)

                        if random.random() < penalty:
                            if grid[nr][nc] not in [SCATTER, WILD] or random.random() < 0.06:
                                grid[nr][nc] = fruit
                                new_frontier.append((nr, nc))

            frontier = new_frontier

            if not frontier:
                break

    return grid


def write_grid_back_to_reels(reels, stops, grid):
    for c in range(COLS):
        for r in range(ROWS):
            reels[c][stops[c] + r] = grid[r][c]


def create_spin(mode="base"):
    reels = []
    stops = []
    expanding_wild_reel = None

    for c in range(COLS):
        strip = build_reel_strip(c)
        stop = random.randint(8, STRIP_LEN - ROWS - 50)

        reels.append(strip)
        stops.append(stop)

    grid = [
        [reels[c][stops[c] + r] for c in range(COLS)]
        for r in range(ROWS)
    ]

    grid = apply_cluster_style_drop(grid, mode)
    write_grid_back_to_reels(reels, stops, grid)

    if mode == "free" and random.random() < 0.16:
        expanding_wild_reel = random.randint(0, COLS - 1)
        stop = stops[expanding_wild_reel]

        for r in range(ROWS):
            reels[expanding_wild_reel][stop + r] = WILD
            grid[r][expanding_wild_reel] = WILD

    wild_multipliers = {}

    if mode == "free":
        for r in range(ROWS):
            for c in range(COLS):
                if grid[r][c] == WILD:
                    wild_multipliers[f"{r}:{c}"] = random.choice([2, 3])

    return reels, stops, grid, expanding_wild_reel, wild_multipliers


def evaluate_line(grid, line, wild_multipliers):
    base_symbol = None
    count = 0
    matched_cells = []

    for c in range(COLS):
        row = line[c]
        symbol = grid[row][c]

        if symbol == SCATTER:
            break

        if base_symbol is None:
            if symbol == WILD:
                count += 1
                matched_cells.append([row, c])
            else:
                base_symbol = symbol
                count += 1
                matched_cells.append([row, c])
        else:
            if symbol == base_symbol or symbol == WILD:
                count += 1
                matched_cells.append([row, c])
            else:
                break

    if count < 3:
        return None

    if base_symbol is None:
        base_symbol = WILD

    if base_symbol not in PAYTABLE:
        return None

    if count not in PAYTABLE[base_symbol]:
        return None

    wild_mults_on_line = []

    for r, c in matched_cells:
        if grid[r][c] == WILD:
            key = f"{r}:{c}"

            if key in wild_multipliers:
                wild_mults_on_line.append(wild_multipliers[key])

    wild_multiplier_total = 1

    if wild_mults_on_line:
        wild_multiplier_total = reduce(mul, wild_mults_on_line, 1)
        wild_multiplier_total = min(wild_multiplier_total, 27)

    return {
        "symbol": base_symbol,
        "count": count,
        "baseMultiplier": PAYTABLE[base_symbol][count],
        "wildMultiplier": wild_multiplier_total,
        "matchedCells": matched_cells,
    }


def get_scatter_cells(grid):
    scatter_cells = []

    for r in range(ROWS):
        for c in range(COLS):
            if grid[r][c] == SCATTER:
                scatter_cells.append([r, c])

    return scatter_cells


def evaluate_grid(grid, bet, mode, wild_multipliers):
    total_win = 0.0
    wins = []
    winning_cells = set()
    winning_line_indices = []

    line_bet = bet 

    for line_index, line in enumerate(PAYLINES):
        result = evaluate_line(grid, line, wild_multipliers)

        if not result:
            continue

        win = line_bet * result["baseMultiplier"] * result["wildMultiplier"]
        total_win += win

        for cell in result["matchedCells"]:
            winning_cells.add(tuple(cell))

        winning_line_indices.append(line_index)

        wins.append({
            "type": "line",
            "lineIndex": line_index,
            "lineNumber": line_index + 1,
            "line": line,
            "symbol": result["symbol"],
            "count": result["count"],
            "baseMultiplier": result["baseMultiplier"],
            "wildMultiplier": result["wildMultiplier"],
            "win": round(win, 2),
            "cells": result["matchedCells"],
        })

    scatter_cells = get_scatter_cells(grid)
    scatter_count = len(scatter_cells)

    if scatter_count >= 3:
        scatter_key = min(scatter_count, 5)
        scatter_win = bet * SCATTER_PAYOUTS[scatter_key]
        total_win += scatter_win

        for cell in scatter_cells:
            winning_cells.add(tuple(cell))

        wins.append({
            "type": "scatter",
            "lineIndex": -1,
            "lineNumber": None,
            "line": None,
            "symbol": SCATTER,
            "count": scatter_count,
            "baseMultiplier": SCATTER_PAYOUTS[scatter_key],
            "wildMultiplier": 1,
            "win": round(scatter_win, 2),
            "cells": scatter_cells,
        })

    free_spin_award = 0
    free_spin_retrigger = 0

    if scatter_count >= 3:
        award_key = min(scatter_count, 5)

        if mode == "base":
            free_spin_award = FREE_SPIN_AWARDS[award_key]
        else:
            free_spin_retrigger = FREE_SPIN_AWARDS[award_key]

    max_win = bet * MAX_WIN_MULTIPLIER
    uncapped_total = total_win
    cap_applied = total_win > max_win

    if cap_applied:
        total_win = max_win

    return {
        "totalWin": round(total_win, 2),
        "uncappedTotalWin": round(uncapped_total, 2),
        "maxWinCap": round(max_win, 2),
        "maxWinMultiplier": MAX_WIN_MULTIPLIER,
        "capApplied": cap_applied,
        "wins": wins,
        "winningCells": [list(cell) for cell in sorted(winning_cells)],
        "winningLineIndices": winning_line_indices,
        "scatterCount": scatter_count,
        "scatterCells": scatter_cells,
        "freeSpinAward": free_spin_award,
        "freeSpinRetrigger": free_spin_retrigger,
    }