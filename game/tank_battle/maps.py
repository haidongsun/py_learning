"""Level maps and map expansion for Tank Battle."""

from .config import EMPTY, BRICK, STEEL, BASE, WATER, TREE, ICE, MAP_W, MAP_H

# Level maps (13x13 encoded, expanded to 26x26 tiles)
# . = empty, B = brick, S = steel, W = water, T = tree, I = ice
LEVEL_MAPS = [
    # Stage 1 — classic intro layout
    [
        ".............",
        "..BB..B..BB..",
        ".B...B.B...B.",
        ".....B.B.....",
        ".BB.S...S.BB.",
        "B...B...B...B",
        ".....BBB.....",
        "B...B...B...B",
        ".BB.S...S.BB.",
        ".....B.B.....",
        ".B...B.B...B.",
        "..BB..B..BB..",
        ".............",
    ],
    # Stage 2 — open field with steel pockets
    [
        ".............",
        ".B.B.B.B.B.B.",
        "..............",
        "B.B.B.B.B.B.B",
        "..S..S..S..S.",
        ".B.B.B.B.B.B.",
        "..............",
        ".B.B.B.B.B.B.",
        "..S..S..S..S.",
        "B.B.B.B.B.B.B",
        "..............",
        ".B.B.B.B.B.B.",
        ".............",
    ],
    # Stage 3 — fortress style
    [
        "....BBBBB....",
        ".B..B...B..B.",
        ".B..B...B..B.",
        ".BB.B...B.BB.",
        "..S.......S..",
        "BB.B.B.B.B.BB",
        "....B.B.B....",
        "BB.B.B.B.B.BB",
        "..S.......S..",
        ".BB.B...B.BB.",
        ".B..B...B..B.",
        ".B..B...B..B.",
        "....BBBBB....",
    ],
    # Stage 4 — steel corridors
    [
        ".............",
        ".SSS.S.S.SSS.",
        ".B..........B",
        ".B.BB.B.BB.B",
        ".B..........B",
        ".B.BSSSSB.B.",
        "..B.......B..",
        ".B.BSSSSB.B.",
        ".B..........B",
        ".B.BB.B.BB.B",
        ".B..........B",
        ".SSS.S.S.SSS.",
        ".............",
    ],
    # Stage 5 — diamond pattern
    [
        ".............",
        "..B.BBB.B.B..",
        ".B.B...B.B.B.",
        ".B..B...B..B.",
        "B...BS.SB...B",
        ".B..B...B..B.",
        "..B..B.B..B..",
        ".B..B...B..B.",
        "B...BS.SB...B",
        ".B..B...B..B.",
        ".B.B...B.B.B.",
        "..B.BBB.B.B..",
        ".............",
    ],
    # Stage 6 — water maze
    [
        "..WWW...WWW..",
        ".WBBB.W.BBBW.",
        "W.B.SB...B.BW",
        "W.B..B.B..B.W",
        "W....B.B....W",
        "..B...B...B..",
        "W....B.B....W",
        "W.B..B.B..B.W",
        "W.B.SB...B.BW",
        ".WBBB.W.BBBW.",
        "..WWW...WWW..",
        ".............",
        ".............",
    ],
    # Stage 7 — forest ambush
    [
        ".............",
        "..TT..T..TT..",
        ".TBB.T.T.BBT.",
        "T....T.T....T",
        ".T.S.....S.T.",
        "..T..BBB..T..",
        "...T.....T...",
        "..T..BBB..T..",
        ".T.S.....S.T.",
        "T....T.T....T",
        ".TBB.T.T.BBT.",
        "..TT..T..TT..",
        ".............",
    ],
    # Stage 8 — ice rink
    [
        ".............",
        ".IIIIIIIIIII.",
        ".IB.B.I.B.BI.",
        ".I...I.I...I.",
        ".I.S.I.I.S.I.",
        ".I...I.I...I.",
        ".IB.B.I.B.BI.",
        ".I...I.I...I.",
        ".I.S.I.I.S.I.",
        ".I...I.I...I.",
        ".IB.B.I.B.BI.",
        ".IIIIIIIIIII.",
        ".............",
    ],
    # Stage 9 — mixed terrain
    [
        ".....WWW.....",
        ".BB.T...T.BB.",
        "B...T.B.T...B",
        "B.S.W.B.W.S.B",
        ".B..W.B.W..B.",
        "..B.......B..",
        ".B..W.B.W..B.",
        "B.S.W.B.W.S.B",
        "B...T.B.T...B",
        ".BB.T...T.BB.",
        ".....WWW.....",
        ".............",
        ".............",
    ],
    # Stage 10 — gauntlet
    [
        ".....SSS.....",
        ".B.B.B.B.B.B.",
        ".B.B.B.B.B.B.",
        "....B.B.B....",
        "B..B.B.B.B..B",
        "B...S.B.S...B",
        "..B.B...B.B..",
        "B...S.B.S...B",
        "B..B.B.B.B..B",
        "....B.B.B....",
        ".B.B.B.B.B.B.",
        ".B.B.B.B.B.B.",
        ".....SSS.....",
    ],
]


_CHAR_MAP = {
    '.': EMPTY, 'B': BRICK, 'S': STEEL,
    'W': WATER, 'T': TREE, 'I': ICE,
}


def expand_map(level_13x13):
    """Expand a 13x13 level layout into a 26x26 tile map."""
    grid = [[EMPTY] * MAP_W for _ in range(MAP_H)]
    for row in range(13):
        for col in range(13):
            ch = level_13x13[row][col]
            tile = _CHAR_MAP.get(ch, EMPTY)
            r2, c2 = row * 2, col * 2
            grid[r2][c2] = tile
            grid[r2][c2 + 1] = tile
            grid[r2 + 1][c2] = tile
            grid[r2 + 1][c2 + 1] = tile
    # Force spawn zones (top) to be empty
    for spawn_col_13 in (0, 6, 12):
        r, c = 0, spawn_col_13 * 2
        for dr in range(2):
            for dc in range(2):
                grid[r + dr][c + dc] = EMPTY
    # Place base at bottom center, with brick walls around it
    grid[MAP_H - 1][12] = BASE
    grid[MAP_H - 1][13] = BASE
    grid[MAP_H - 2][12] = BASE
    grid[MAP_H - 2][13] = BASE
    # Clear a small area around base (so player can spawn)
    for r in range(MAP_H - 2, MAP_H):
        for c in range(10, 16):
            if grid[r][c] not in (BASE, STEEL):
                grid[r][c] = EMPTY
    return grid
