# Lumatrix Chess AI
# Raspberry Pi Pico / MicroPython / 8x8 WS2812B
# Weiss = Spieler, Schwarz = Pico-KI

from machine import Pin
from neopixel import NeoPixel
from utime import sleep_ms, ticks_ms, ticks_diff
import random

# ============================================================
# EINSTELLUNGEN
# ============================================================
LED_PIN = 19
AI_TIME_MS = 4000          # ca. 2-5 s Bedenkzeit
AI_MAX_DEPTH = 4           # iterative Vertiefung
LOOP_DELAY_MS = 35
MOVE_ANIMATION_MS = 170
RESTART_HOLD_MS = 2000

# Weiss: kühl/hell
WHITE_PAWN   = (18, 18, 18)
WHITE_KNIGHT = (0, 30, 55)
WHITE_BISHOP = (0, 50, 18)
WHITE_ROOK   = (0, 55, 55)
WHITE_QUEEN  = (38, 0, 52)
WHITE_KING   = (55, 45, 0)

# Schwarz: warm/rot
BLACK_PAWN   = (20, 0, 0)
BLACK_KNIGHT = (55, 20, 0)
BLACK_BISHOP = (50, 28, 0)
BLACK_ROOK   = (38, 0, 18)
BLACK_QUEEN = (55, 25, 25)
BLACK_KING   = (55, 55, 20)

# Bedienfarben
C_CURSOR   = (55, 55, 55)
C_SELECTED = (55, 45, 0)
C_MOVE     = (0, 28, 0)
C_CAPTURE  = (55, 18, 0)
C_CHECK    = (55, 0, 0)
C_LAST     = (0, 12, 28)
C_THINK    = (18, 0, 35)
C_OFF      = (0, 0, 0)

# ============================================================
# HARDWARE
# ============================================================
np = NeoPixel(Pin(LED_PIN, Pin.OUT), 64)

rechts = Pin(2, Pin.IN, Pin.PULL_UP)
hoch = Pin(3, Pin.IN, Pin.PULL_UP)
runter = Pin(6, Pin.IN, Pin.PULL_UP)
links = Pin(7, Pin.IN, Pin.PULL_UP)
mitte = Pin(8, Pin.IN, Pin.PULL_UP)
schalter = Pin(9, Pin.IN, Pin.PULL_UP)

# ============================================================
# SCHACH-KONSTANTEN
# Positive Zahl = Weiss, negative Zahl = Schwarz
# ============================================================
EMPTY = 0
PAWN = 1
KNIGHT = 2
BISHOP = 3
ROOK = 4
QUEEN = 5
KING = 6

WK = 1
WQ = 2
BK = 4
BQ = 8

ALL_CASTLING = WK | WQ | BK | BQ

INF = 1000000
MATE = 100000

VALUE = [
    0,
    100,
    320,
    330,
    500,
    900,
    20000
]

COLORS = {
    PAWN: WHITE_PAWN,
    KNIGHT: WHITE_KNIGHT,
    BISHOP: WHITE_BISHOP,
    ROOK: WHITE_ROOK,
    QUEEN: WHITE_QUEEN,
    KING: WHITE_KING,

    -PAWN: BLACK_PAWN,
    -KNIGHT: BLACK_KNIGHT,
    -BISHOP: BLACK_BISHOP,
    -ROOK: BLACK_ROOK,
    -QUEEN: BLACK_QUEEN,
    -KING: BLACK_KING,
}

KNIGHT_STEPS = (
    (1, 2),
    (2, 1),
    (2, -1),
    (1, -2),
    (-1, -2),
    (-2, -1),
    (-2, 1),
    (-1, 2)
)

KING_STEPS = (
    (-1, -1),
    (0, -1),
    (1, -1),
    (-1, 0),
    (1, 0),
    (-1, 1),
    (0, 1),
    (1, 1)
)

DIAG = (
    (1, 1),
    (1, -1),
    (-1, 1),
    (-1, -1)
)

STRAIGHT = (
    (1, 0),
    (-1, 0),
    (0, 1),
    (0, -1)
)

PROMOS = (
    QUEEN,
    ROOK,
    BISHOP,
    KNIGHT
)

search_start = 0
search_timeout = False
search_nodes = 0

# ============================================================
# KOORDINATEN / MATRIX
# ============================================================

def sq(x, y):
    return y * 8 + x


def xy(s):
    return s % 8, s // 8


def inside(x, y):
    return 0 <= x < 8 and 0 <= y < 8


def clear_leds():
    for i in range(64):
        np[i] = C_OFF


def half(c):
    return (
        c[0] // 2,
        c[1] // 2,
        c[2] // 2
    )


def third(c):
    return (
        c[0] // 3,
        c[1] // 3,
        c[2] // 3
    )


def blend(a, b):
    return (
        (a[0] + b[0]) // 2,
        (a[1] + b[1]) // 2,
        (a[2] + b[2]) // 2
    )

# ============================================================
# STARTBRETT
# ============================================================

def new_board():
    b = [0] * 64

    white_back = (
        ROOK,
        KNIGHT,
        BISHOP,
        QUEEN,
        KING,
        BISHOP,
        KNIGHT,
        ROOK
    )

    black_back = tuple(
        -p for p in white_back
    )

    for x in range(8):
        b[sq(x, 0)] = white_back[x]
        b[sq(x, 1)] = PAWN

        b[sq(x, 6)] = -PAWN
        b[sq(x, 7)] = black_back[x]

    return b

# ============================================================
# ANGRIFFE / SCHACH
# ============================================================

def find_king(board, white):
    king = KING if white else -KING

    for i in range(64):
        if board[i] == king:
            return i

    return -1


def attacked(board, target, by_white):
    tx, ty = xy(target)

    # Bauern
    pawn = PAWN if by_white else -PAWN
    py = ty - 1 if by_white else ty + 1

    if 0 <= py < 8:

        if (
            tx > 0
            and board[sq(tx - 1, py)] == pawn
        ):
            return True

        if (
            tx < 7
            and board[sq(tx + 1, py)] == pawn
        ):
            return True

    # Springer
    knight = (
        KNIGHT
        if by_white
        else -KNIGHT
    )

    for dx, dy in KNIGHT_STEPS:
        x = tx + dx
        y = ty + dy

        if (
            inside(x, y)
            and board[sq(x, y)] == knight
        ):
            return True

    # König
    king = (
        KING
        if by_white
        else -KING
    )

    for dx, dy in KING_STEPS:
        x = tx + dx
        y = ty + dy

        if (
            inside(x, y)
            and board[sq(x, y)] == king
        ):
            return True

    # Läufer / Dame
    bishop = (
        BISHOP
        if by_white
        else -BISHOP
    )

    queen = (
        QUEEN
        if by_white
        else -QUEEN
    )

    for dx, dy in DIAG:
        x = tx + dx
        y = ty + dy

        while inside(x, y):
            p = board[sq(x, y)]

            if p:
                if (
                    p == bishop
                    or p == queen
                ):
                    return True

                break

            x += dx
            y += dy

    # Turm / Dame
    rook = (
        ROOK
        if by_white
        else -ROOK
    )

    for dx, dy in STRAIGHT:
        x = tx + dx
        y = ty + dy

        while inside(x, y):
            p = board[sq(x, y)]

            if p:
                if (
                    p == rook
                    or p == queen
                ):
                    return True

                break

            x += dx
            y += dy

    return False


def in_check(board, white):
    k = find_king(
        board,
        white
    )

    return (
        k < 0
        or attacked(
            board,
            k,
            not white
        )
    )

# ============================================================
# ZÜGE
# Move = (von, nach, promotion, en_passant)
# ============================================================

def add_promotions(
    moves,
    start,
    end
):
    for p in PROMOS:
        moves.append(
            (
                start,
                end,
                p,
                0
            )
        )


def pseudo_moves(
    board,
    white,
    rights,
    ep
):
    moves = []

    for start in range(64):

        piece = board[start]

        if piece == 0:
            continue

        if (
            white
            and piece < 0
        ):
            continue

        if (
            (not white)
            and piece > 0
        ):
            continue

        p = abs(piece)
        x, y = xy(start)

        # ----------------------------------------------------
        # BAUER
        # ----------------------------------------------------
        if p == PAWN:

            d = (
                1
                if white
                else -1
            )

            start_rank = (
                1
                if white
                else 6
            )

            promo_rank = (
                7
                if white
                else 0
            )

            ny = y + d

            if 0 <= ny < 8:

                one = sq(x, ny)

                # Ein Feld vor
                if board[one] == 0:

                    if ny == promo_rank:
                        add_promotions(
                            moves,
                            start,
                            one
                        )

                    else:
                        moves.append(
                            (
                                start,
                                one,
                                0,
                                0
                            )
                        )

                    # Zwei Felder aus Startposition
                    two_y = y + 2 * d

                    if (
                        y == start_rank
                        and board[sq(x, two_y)] == 0
                    ):
                        moves.append(
                            (
                                start,
                                sq(x, two_y),
                                0,
                                0
                            )
                        )

                # Diagonal schlagen
                for dx in (-1, 1):

                    nx = x + dx

                    if not inside(nx, ny):
                        continue

                    target = sq(nx, ny)

                    q = board[target]

                    enemy = (
                        q < 0
                        if white
                        else q > 0
                    )

                    if (
                        enemy
                        and abs(q) != KING
                    ):
                        if ny == promo_rank:
                            add_promotions(
                                moves,
                                start,
                                target
                            )

                        else:
                            moves.append(
                                (
                                    start,
                                    target,
                                    0,
                                    0
                                )
                            )

                    elif target == ep:
                        moves.append(
                            (
                                start,
                                target,
                                0,
                                1
                            )
                        )

        # ----------------------------------------------------
        # SPRINGER
        # ----------------------------------------------------
        elif p == KNIGHT:

            for dx, dy in KNIGHT_STEPS:

                nx = x + dx
                ny = y + dy

                if inside(nx, ny):

                    target = sq(nx, ny)
                    q = board[target]

                    if (
                        q == 0
                        or (
                            white
                            and q < 0
                            and abs(q) != KING
                        )
                        or (
                            (not white)
                            and q > 0
                            and abs(q) != KING
                        )
                    ):
                        moves.append(
                            (
                                start,
                                target,
                                0,
                                0
                            )
                        )

        # ----------------------------------------------------
        # LÄUFER / TURM / DAME
        # ----------------------------------------------------
        elif p in (
            BISHOP,
            ROOK,
            QUEEN
        ):

            dirs = ()

            if p in (
                BISHOP,
                QUEEN
            ):
                dirs += DIAG

            if p in (
                ROOK,
                QUEEN
            ):
                dirs += STRAIGHT

            for dx, dy in dirs:

                nx = x + dx
                ny = y + dy

                while inside(nx, ny):

                    target = sq(nx, ny)
                    q = board[target]

                    if q == 0:
                        moves.append(
                            (
                                start,
                                target,
                                0,
                                0
                            )
                        )

                    else:

                        if (
                            (
                                white
                                and q < 0
                                and abs(q) != KING
                            )
                            or (
                                (not white)
                                and q > 0
                                and abs(q) != KING
                            )
                        ):
                            moves.append(
                                (
                                    start,
                                    target,
                                    0,
                                    0
                                )
                            )

                        break

                    nx += dx
                    ny += dy

        # ----------------------------------------------------
        # KÖNIG
        # ----------------------------------------------------
        elif p == KING:

            for dx, dy in KING_STEPS:

                nx = x + dx
                ny = y + dy

                if inside(nx, ny):

                    target = sq(nx, ny)
                    q = board[target]

                    if (
                        q == 0
                        or (
                            white
                            and q < 0
                            and abs(q) != KING
                        )
                        or (
                            (not white)
                            and q > 0
                            and abs(q) != KING
                        )
                    ):
                        moves.append(
                            (
                                start,
                                target,
                                0,
                                0
                            )
                        )

            # Weisse Rochade
            if (
                white
                and start == sq(4, 0)
                and not in_check(
                    board,
                    True
                )
            ):

                # Kurz
                if (
                    rights & WK
                    and board[sq(7, 0)] == ROOK
                    and board[sq(5, 0)] == 0
                    and board[sq(6, 0)] == 0
                ):

                    if (
                        not attacked(
                            board,
                            sq(5, 0),
                            False
                        )
                        and not attacked(
                            board,
                            sq(6, 0),
                            False
                        )
                    ):
                        moves.append(
                            (
                                start,
                                sq(6, 0),
                                0,
                                0
                            )
                        )

                # Lang
                if (
                    rights & WQ
                    and board[sq(0, 0)] == ROOK
                    and board[sq(1, 0)] == 0
                    and board[sq(2, 0)] == 0
                    and board[sq(3, 0)] == 0
                ):

                    if (
                        not attacked(
                            board,
                            sq(3, 0),
                            False
                        )
                        and not attacked(
                            board,
                            sq(2, 0),
                            False
                        )
                    ):
                        moves.append(
                            (
                                start,
                                sq(2, 0),
                                0,
                                0
                            )
                        )

            # Schwarze Rochade
            if (
                (not white)
                and start == sq(4, 7)
                and not in_check(
                    board,
                    False
                )
            ):

                # Kurz
                if (
                    rights & BK
                    and board[sq(7, 7)] == -ROOK
                    and board[sq(5, 7)] == 0
                    and board[sq(6, 7)] == 0
                ):

                    if (
                        not attacked(
                            board,
                            sq(5, 7),
                            True
                        )
                        and not attacked(
                            board,
                            sq(6, 7),
                            True
                        )
                    ):
                        moves.append(
                            (
                                start,
                                sq(6, 7),
                                0,
                                0
                            )
                        )

                # Lang
                if (
                    rights & BQ
                    and board[sq(0, 7)] == -ROOK
                    and board[sq(1, 7)] == 0
                    and board[sq(2, 7)] == 0
                    and board[sq(3, 7)] == 0
                ):

                    if (
                        not attacked(
                            board,
                            sq(3, 7),
                            True
                        )
                        and not attacked(
                            board,
                            sq(2, 7),
                            True
                        )
                    ):
                        moves.append(
                            (
                                start,
                                sq(2, 7),
                                0,
                                0
                            )
                        )

    return moves


def apply_move(
    board,
    rights,
    ep,
    move
):
    start, end, promo, ep_flag = move

    b = board[:]

    piece = b[start]
    captured = b[end]

    b[start] = 0
    b[end] = piece

    # En passant
    if ep_flag:

        ex, ey = xy(end)

        if piece > 0:
            capture_y = ey - 1

        else:
            capture_y = ey + 1

        b[sq(ex, capture_y)] = 0

    sx, sy = xy(start)
    ex, ey = xy(end)

    # Turm bei Rochade mitnehmen
    if (
        abs(piece) == KING
        and abs(ex - sx) == 2
    ):

        if ex == 6:
            rook_from = sq(7, sy)
            rook_to = sq(5, sy)

        else:
            rook_from = sq(0, sy)
            rook_to = sq(3, sy)

        b[rook_to] = b[rook_from]
        b[rook_from] = 0

    # Bauernumwandlung
    if promo:

        if piece > 0:
            b[end] = promo

        else:
            b[end] = -promo

    # Rochaderechte verwalten
    r = rights

    if piece == KING:
        r &= ~(WK | WQ)

    elif piece == -KING:
        r &= ~(BK | BQ)

    if start == sq(0, 0):
        r &= ~WQ

    elif start == sq(7, 0):
        r &= ~WK

    elif start == sq(0, 7):
        r &= ~BQ

    elif start == sq(7, 7):
        r &= ~BK

    # Wurde ein Turm geschlagen?
    if (
        end == sq(0, 0)
        and captured == ROOK
    ):
        r &= ~WQ

    elif (
        end == sq(7, 0)
        and captured == ROOK
    ):
        r &= ~WK

    elif (
        end == sq(0, 7)
        and captured == -ROOK
    ):
        r &= ~BQ

    elif (
        end == sq(7, 7)
        and captured == -ROOK
    ):
        r &= ~BK

    # En-passant-Zielfeld
    new_ep = -1

    if (
        abs(piece) == PAWN
        and abs(ey - sy) == 2
    ):
        new_ep = sq(
            sx,
            (sy + ey) // 2
        )

    return b, r, new_ep


def legal_moves(
    board,
    white,
    rights,
    ep
):
    result = []

    for m in pseudo_moves(
        board,
        white,
        rights,
        ep
    ):

        b2, r2, e2 = apply_move(
            board,
            rights,
            ep,
            m
        )

        if not in_check(
            b2,
            white
        ):
            result.append(m)

    return result

# ============================================================
# KI
# ============================================================

def evaluate(board):
    score = 0

    for s in range(64):

        piece = board[s]

        if piece == 0:
            continue

        p = abs(piece)

        x, y = xy(s)

        v = VALUE[p]

        center = max(
            0,
            10
            - (
                abs(2 * x - 7)
                + abs(2 * y - 7)
            )
        )

        # Bauern erhalten Bonus
        # für Fortschritt
        if p == PAWN:

            if piece > 0:
                progress = y

            else:
                progress = 7 - y

            v += progress * 7

        elif p == KNIGHT:
            v += center * 4

        elif p == BISHOP:
            v += center * 2

        elif p == QUEEN:
            v += center

        elif (
            p == KING
            and y in (0, 7)
        ):
            v += 12

        if piece > 0:
            score += v

        else:
            score -= v

    if in_check(
        board,
        True
    ):
        score -= 25

    if in_check(
        board,
        False
    ):
        score += 25

    return score


def move_score(board, m):

    start, end, promo, ep_flag = m

    attacker = abs(
        board[start]
    )

    if ep_flag:
        victim = PAWN

    else:
        victim = abs(
            board[end]
        )

    score = 0

    # Gute Schlagzüge zuerst
    if victim:

        score += (
            10 * VALUE[victim]
            - VALUE[attacker]
        )

    # Promotion priorisieren
    if promo:

        score += (
            VALUE[promo]
            + 800
        )

    sx, sy = xy(start)
    ex, ey = xy(end)

    # Rochade leicht bevorzugen
    if (
        attacker == KING
        and abs(ex - sx) == 2
    ):
        score += 60

    return score


def order_moves(
    board,
    moves
):
    # Einfügesortierung:
    # gute Züge zuerst
    for i in range(
        1,
        len(moves)
    ):

        current = moves[i]

        value = move_score(
            board,
            current
        )

        j = i - 1

        while (
            j >= 0
            and move_score(
                board,
                moves[j]
            ) < value
        ):
            moves[j + 1] = moves[j]
            j -= 1

        moves[j + 1] = current


def time_over():
    return (
        ticks_diff(
            ticks_ms(),
            search_start
        )
        >= AI_TIME_MS
    )


def alphabeta(
    board,
    white,
    rights,
    ep,
    depth,
    alpha,
    beta,
    ply
):
    global search_timeout
    global search_nodes

    search_nodes += 1

    # Zeit nicht bei jedem Knoten prüfen
    if (
        (search_nodes & 63) == 0
        and time_over()
    ):
        search_timeout = True

        return evaluate(board)

    if depth == 0:
        return evaluate(board)

    moves = legal_moves(
        board,
        white,
        rights,
        ep
    )

    # Matt oder Patt
    if not moves:

        if in_check(
            board,
            white
        ):

            if white:
                return -MATE + ply

            else:
                return MATE - ply

        return 0

    order_moves(
        board,
        moves
    )

    # Weiss maximiert
    if white:

        value = -INF

        for m in moves:

            b2, r2, e2 = apply_move(
                board,
                rights,
                ep,
                m
            )

            score = alphabeta(
                b2,
                False,
                r2,
                e2,
                depth - 1,
                alpha,
                beta,
                ply + 1
            )

            if search_timeout:

                if value == -INF:
                    return score

                return value

            if score > value:
                value = score

            if value > alpha:
                alpha = value

            if alpha >= beta:
                break

        return value

    # Schwarz minimiert
    else:

        value = INF

        for m in moves:

            b2, r2, e2 = apply_move(
                board,
                rights,
                ep,
                m
            )

            score = alphabeta(
                b2,
                True,
                r2,
                e2,
                depth - 1,
                alpha,
                beta,
                ply + 1
            )

            if search_timeout:

                if value == INF:
                    return score

                return value

            if score < value:
                value = score

            if value < beta:
                beta = value

            if alpha >= beta:
                break

        return value


def choose_ai_move(
    board,
    rights,
    ep
):
    global search_start
    global search_timeout
    global search_nodes

    root = legal_moves(
        board,
        False,
        rights,
        ep
    )

    if not root:
        return None

    order_moves(
        board,
        root
    )

    best = root[0]
    completed = 0

    search_start = ticks_ms()

    # Iterative Vertiefung
    for depth in range(
        1,
        AI_MAX_DEPTH + 1
    ):

        search_timeout = False
        search_nodes = 0

        depth_best = None
        depth_score = INF
        equal = []

        beta = INF

        for m in root:

            if time_over():
                search_timeout = True
                break

            b2, r2, e2 = apply_move(
                board,
                rights,
                ep,
                m
            )

            score = alphabeta(
                b2,
                True,
                r2,
                e2,
                depth - 1,
                -INF,
                beta,
                1
            )

            if search_timeout:
                break

            if score < depth_score:

                depth_score = score
                depth_best = m
                equal = [m]

            elif score == depth_score:

                equal.append(m)

            if score < beta:
                beta = score

        # Nur vollständig berechnete
        # Tiefe übernehmen
        if (
            search_timeout
            or depth_best is None
        ):
            break

        best = equal[
            random.randint(
                0,
                len(equal) - 1
            )
        ]

        completed = depth

        # Besten Zug für nächste Tiefe
        # zuerst prüfen
        root.remove(best)
        root.insert(
            0,
            best
        )

    print(
        "KI Tiefe:",
        completed
    )

    print(
        "KI Zug:",
        move_name(best)
    )

    return best

# ============================================================
# STATUS / TEXTAUSGABE
# ============================================================

def status(
    board,
    white,
    rights,
    ep
):
    moves = legal_moves(
        board,
        white,
        rights,
        ep
    )

    if moves:
        return "PLAY"

    if in_check(
        board,
        white
    ):

        if white:
            return "BLACK_WIN"

        return "WHITE_WIN"

    return "DRAW"


def move_name(m):

    if m is None:
        return "-"

    a, b, promo, ep_flag = m

    ax, ay = xy(a)
    bx, by = xy(b)

    files = "abcdefgh"

    result = (
        files[ax]
        + str(ay + 1)
        + "-"
        + files[bx]
        + str(by + 1)
    )

    if promo:

        names = {
            QUEEN: "Q",
            ROOK: "R",
            BISHOP: "B",
            KNIGHT: "N"
        }

        result += (
            "="
            + names[promo]
        )

    if ep_flag:
        result += " e.p."

    return result

# ============================================================
# LED-DARSTELLUNG
# ============================================================

def render(
    board,
    cursor,
    selected,
    selected_moves,
    last_move,
    white_turn,
    promo_piece=0
):
    clear_leds()

    fast = (
        ticks_ms() // 220
    ) % 2

    slow = (
        ticks_ms() // 450
    ) % 2

    # Figuren
    for i in range(64):

        if board[i]:
            np[i] = COLORS[
                board[i]
            ]

    # Letzten Zug dezent zeigen
    if (
        last_move is not None
        and selected < 0
        and slow == 0
    ):

        for s in (
            last_move[0],
            last_move[1]
        ):

            if board[s] == 0:
                np[s] = C_LAST

            else:
                np[s] = blend(
                    np[s],
                    C_LAST
                )

    # Legale Zielfelder
    if selected >= 0:

        for m in selected_moves:

            target = m[1]

            capture = (
                board[target] != 0
                or m[3]
            )

            if capture:

                if fast:
                    np[target] = C_CAPTURE

            else:
                np[target] = C_MOVE

        if fast:
            np[selected] = C_SELECTED

    # Schach anzeigen
    if in_check(
        board,
        white_turn
    ):

        k = find_king(
            board,
            white_turn
        )

        if (
            k >= 0
            and fast
        ):
            np[k] = C_CHECK

    # Promotion
    if promo_piece:

        np[cursor] = COLORS[
            promo_piece
        ]

        if fast:
            np[cursor] = C_SELECTED

    # Normaler Cursor
    elif fast:
        np[cursor] = C_CURSOR

    np.write()


def show_thinking(board):

    clear_leds()

    # Brett abdunkeln
    for i in range(64):

        if board[i]:
            np[i] = half(
                COLORS[board[i]]
            )

    # Kleines KI-Symbol
    for s in (
        sq(3, 3),
        sq(4, 3),
        sq(3, 4),
        sq(4, 4)
    ):
        np[s] = C_THINK

    np.write()


def animate_move(
    before,
    after,
    m,
    ai=False
):

    flash = (
        C_THINK
        if ai
        else C_SELECTED
    )

    for _ in range(3):

        clear_leds()

        for i in range(64):

            if before[i]:
                np[i] = COLORS[
                    before[i]
                ]

        np[m[0]] = flash
        np[m[1]] = flash

        np.write()

        sleep_ms(
            MOVE_ANIMATION_MS
        )

        clear_leds()

        for i in range(64):

            if after[i]:
                np[i] = COLORS[
                    after[i]
                ]

        np.write()

        sleep_ms(
            MOVE_ANIMATION_MS
        )


def error_flash(square):

    old = np[square]

    for _ in range(2):

        np[square] = C_CHECK
        np.write()

        sleep_ms(120)

        np[square] = old
        np.write()

        sleep_ms(100)


def game_over_animation(result):

    if result == "WHITE_WIN":
        color = WHITE_KING

    elif result == "BLACK_WIN":
        color = BLACK_KING

    else:
        color = (
            20,
            20,
            35
        )

    # Ring vom Zentrum
    for radius in range(8):

        clear_leds()

        for y in range(8):

            for x in range(8):

                d = (
                    abs(2 * x - 7)
                    + abs(2 * y - 7)
                )

                if (
                    radius * 2
                    <= d
                    < radius * 2 + 4
                ):
                    np[
                        sq(x, y)
                    ] = color

        np.write()

        sleep_ms(120)


def render_game_over(
    board,
    result,
    armed
):

    clear_leds()

    blink = (
        ticks_ms() // 350
    ) % 2

    # Restliches Brett abdunkeln
    for i in range(64):

        if board[i]:
            np[i] = third(
                COLORS[board[i]]
            )

    if result == "WHITE_WIN":

        k = find_king(
            board,
            False
        )

        color = WHITE_KING

    elif result == "BLACK_WIN":

        k = find_king(
            board,
            True
        )

        color = BLACK_KING

    else:

        k = -1

        color = (
            20,
            20,
            35
        )

    if (
        k >= 0
        and blink
    ):
        np[k] = color

    # Schalter-Reset vorbereitet
    if armed:

        for x in range(8):

            np[
                sq(x, 7)
            ] = (
                0,
                35,
                35
            )

    np.write()

# ============================================================
# BEDIENUNG
# ============================================================

def moves_from(
    moves,
    square
):
    return [
        m
        for m in moves
        if m[0] == square
    ]


def moves_to(
    moves,
    square
):
    return [
        m
        for m in moves
        if m[1] == square
    ]


def reset_state():

    return {
        "board": new_board(),
        "rights": ALL_CASTLING,
        "ep": -1,
        "white_turn": True,

        # Startcursor auf e2
        "cursor": sq(4, 1),

        "selected": -1,
        "selected_moves": [],

        "last_move": None,

        "promo": [],
        "promo_index": 0,

        "game_over": False,
        "result": "PLAY",

        "restart_armed": False,
    }


def finish_human_move(
    state,
    m
):

    before = state["board"]

    after, rights, ep = apply_move(
        before,
        state["rights"],
        state["ep"],
        m
    )

    animate_move(
        before,
        after,
        m,
        False
    )

    state["board"] = after
    state["rights"] = rights
    state["ep"] = ep

    state["white_turn"] = False

    state["last_move"] = m

    state["selected"] = -1
    state["selected_moves"] = []

    state["promo"] = []

    print(
        "Spieler:",
        move_name(m)
    )


def ai_turn(state):

    current_status = status(
        state["board"],
        False,
        state["rights"],
        state["ep"]
    )

    if current_status != "PLAY":

        state["game_over"] = True
        state["result"] = current_status

        game_over_animation(
            current_status
        )

        return

    show_thinking(
        state["board"]
    )

    move = choose_ai_move(
        state["board"],
        state["rights"],
        state["ep"]
    )

    if move is None:
        return

    before = state["board"]

    after, rights, ep = apply_move(
        before,
        state["rights"],
        state["ep"],
        move
    )

    animate_move(
        before,
        after,
        move,
        True
    )

    state["board"] = after
    state["rights"] = rights
    state["ep"] = ep

    state["white_turn"] = True

    state["last_move"] = move

    # Cursor springt auf
    # das KI-Zielfeld
    state["cursor"] = move[1]

    current_status = status(
        after,
        True,
        rights,
        ep
    )

    if current_status != "PLAY":

        state["game_over"] = True
        state["result"] = current_status

        game_over_animation(
            current_status
        )


def center_pressed(state):

    # Bauernumwandlung bestätigen
    if state["promo"]:

        finish_human_move(
            state,
            state["promo"][
                state["promo_index"]
            ]
        )

        return

    if (
        not state["white_turn"]
        or state["game_over"]
    ):
        return

    current = state["cursor"]
    selected = state["selected"]

    board = state["board"]

    # Noch nichts ausgewählt
    if selected < 0:

        if board[current] <= 0:

            error_flash(
                current
            )

            return

        all_moves = legal_moves(
            board,
            True,
            state["rights"],
            state["ep"]
        )

        own_moves = moves_from(
            all_moves,
            current
        )

        if not own_moves:

            error_flash(
                current
            )

            return

        state["selected"] = current

        state["selected_moves"] = (
            own_moves
        )

        return

    # Startfeld erneut drücken:
    # Auswahl abbrechen
    if current == selected:

        state["selected"] = -1
        state["selected_moves"] = []

        return

    # Andere eigene Figur:
    # direkt neu auswählen
    if board[current] > 0:

        all_moves = legal_moves(
            board,
            True,
            state["rights"],
            state["ep"]
        )

        own_moves = moves_from(
            all_moves,
            current
        )

        if own_moves:

            state["selected"] = (
                current
            )

            state[
                "selected_moves"
            ] = own_moves

        else:

            error_flash(
                current
            )

        return

    # Zielfeld prüfen
    options = moves_to(
        state["selected_moves"],
        current
    )

    if not options:

        error_flash(
            current
        )

    # Mehrere Optionen:
    # Bauernumwandlung
    elif len(options) > 1:

        state["promo"] = options
        state["promo_index"] = 0

    else:

        finish_human_move(
            state,
            options[0]
        )


def direction_pressed(
    state,
    direction
):

    # Während Promotion
    # Figur auswählen
    if state["promo"]:

        if direction in (
            "LEFT",
            "DOWN"
        ):
            step = -1

        else:
            step = 1

        state["promo_index"] = (
            state["promo_index"]
            + step
        ) % len(
            state["promo"]
        )

        return

    x, y = xy(
        state["cursor"]
    )

    if direction == "LEFT":
        x -= 1

    elif direction == "RIGHT":
        x += 1

    elif direction == "UP":
        y += 1

    elif direction == "DOWN":
        y -= 1

    x = max(
        0,
        min(7, x)
    )

    y = max(
        0,
        min(7, y)
    )

    state["cursor"] = sq(
        x,
        y
    )

# ============================================================
# HAUPTSCHLEIFE
# ============================================================

def main():

    state = reset_state()

    # Schalterstellung beim Start merken.
    # Ein Reset funktioniert jederzeit:
    #
    # 1) Mitte ca. 2 s halten
    #
    # ODER
    #
    # 2) Schalter umlegen
    #    -> Hoch drücken
    #    -> Schalter zurück
    home_switch = (
        schalter.value()
    )

    restart_armed = False

    prev_l = 1
    prev_r = 1
    prev_u = 1
    prev_d = 1
    prev_c = 1

    hold_start = -1

    print(
        "Lumatrix Chess AI gestartet"
    )

    print(
        "Du spielst Weiss."
    )

    while True:

        # Eingänge zuerst lesen,
        # damit Reset jederzeit
        # erkannt wird.
        l = links.value()
        r = rechts.value()
        u = hoch.value()
        d = runter.value()
        c = mitte.value()
        sw = schalter.value()

        # ====================================================
        # RESET A
        # Mitte ca. 2 Sekunden halten
        # ====================================================
        if c == 0:

            if hold_start < 0:

                hold_start = (
                    ticks_ms()
                )

            elif (
                ticks_diff(
                    ticks_ms(),
                    hold_start
                )
                >= RESTART_HOLD_MS
            ):

                state = reset_state()

                home_switch = sw

                restart_armed = False

                hold_start = -1

                # Tastenstatus übernehmen,
                # damit kein alter Tastendruck
                # direkt nochmals erkannt wird.
                prev_l = l
                prev_r = r
                prev_u = u
                prev_d = d
                prev_c = c

                clear_leds()
                np.write()

                sleep_ms(250)

                continue

        else:

            hold_start = -1

        # ====================================================
        # RESET B
        # Schalter umlegen
        # -> Hoch drücken
        # -> Schalter zurück
        # ====================================================
        if sw != home_switch:

            # Hoch muss nur gedrückt sein.
            # Keine Flankenerkennung mehr.
            if u == 0:

                restart_armed = True

        elif restart_armed:

            # Der Schalter wurde nach
            # Aktivierung wieder zurückgelegt.
            state = reset_state()

            home_switch = sw

            restart_armed = False

            hold_start = -1

            prev_l = l
            prev_r = r
            prev_u = u
            prev_d = d
            prev_c = c

            clear_leds()
            np.write()

            sleep_ms(250)

            continue

        # ====================================================
        # KI-ZUG
        # ====================================================
        if (
            not state["game_over"]
            and not state["white_turn"]
        ):

            ai_turn(state)

            # Die KI-Berechnung blockiert
            # einige Sekunden.
            # Danach Eingänge neu lesen.
            l = links.value()
            r = rechts.value()
            u = hoch.value()
            d = runter.value()
            c = mitte.value()
            sw = schalter.value()

        # ====================================================
        # SPIELENDE
        # ====================================================
        if state["game_over"]:

            render_game_over(
                state["board"],
                state["result"],
                restart_armed
            )

        # ====================================================
        # NORMALES SPIEL
        # ====================================================
        else:

            # Wenn der Schalter umgelegt ist,
            # werden normale Cursorbefehle
            # unterdrückt.
            #
            # Dadurch kann "Hoch" eindeutig
            # für den Reset genutzt werden.
            if sw == home_switch:

                if (
                    l == 0
                    and prev_l == 1
                ):
                    direction_pressed(
                        state,
                        "LEFT"
                    )

                if (
                    r == 0
                    and prev_r == 1
                ):
                    direction_pressed(
                        state,
                        "RIGHT"
                    )

                if (
                    u == 0
                    and prev_u == 1
                ):
                    direction_pressed(
                        state,
                        "UP"
                    )

                if (
                    d == 0
                    and prev_d == 1
                ):
                    direction_pressed(
                        state,
                        "DOWN"
                    )

                if (
                    c == 0
                    and prev_c == 1
                ):
                    center_pressed(
                        state
                    )

            promo_piece = 0

            if state["promo"]:

                promo_piece = (
                    state["promo"][
                        state["promo_index"]
                    ][2]
                )

            render(
                state["board"],
                state["cursor"],
                state["selected"],
                state[
                    "selected_moves"
                ],
                state["last_move"],
                state["white_turn"],
                promo_piece
            )

        # Tastenstatus für
        # Flankenerkennung speichern
        prev_l = l
        prev_r = r
        prev_u = u
        prev_d = d
        prev_c = c

        sleep_ms(
            LOOP_DELAY_MS
        )


if __name__ == "__main__":
    main()
