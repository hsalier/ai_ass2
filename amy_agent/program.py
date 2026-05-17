# COMP30024 Artificial Intelligence, Semester 1 2026
# Project Part B: Game Playing Agent

from referee.game import PlayerColor, Coord, Direction, \
    Action, PlaceAction, MoveAction, EatAction, CascadeAction, BOARD_N
import random

DEPTH = 4
CARDINAL_DIRECTIONS = [
    Direction.Up,
    Direction.Down,
    Direction.Left,
    Direction.Right,
]

Stack = tuple[PlayerColor, int]
Board = dict[Coord, Stack | None]


class Agent:

    def __init__(self, color: PlayerColor, **referee: dict):
        self._color = color
        self._opponent = (
            PlayerColor.BLUE if color == PlayerColor.RED
            else PlayerColor.RED
        )
        self._board: Board = {
            Coord(r, c): None
            for r in range(BOARD_N)
            for c in range(BOARD_N)
        }
        self._total_turns = 0
        self._my_turns = 0
        self._placements_made = {
            PlayerColor.RED: 0,
            PlayerColor.BLUE: 0,
        }
        self._position_history: list[int] = []

    def _board_hash(self, board: Board) -> int:
        return hash(frozenset(
            (coord, stack)
            for coord, stack in board.items()
            if stack is not None
        ))

    def _can_enemy_cascade_to(self, coord: Coord) -> bool:
        enemy = self._opponent
        for enemy_coord, stack in self._board.items():
            if stack is None:
                continue
            stack_color, stack_height = stack
            if stack_color != enemy:
                continue
            if stack_height < 2:
                continue
            same_row = enemy_coord.r == coord.r
            same_col = enemy_coord.c == coord.c
            if not same_row and not same_col:
                continue
            distance = abs(enemy_coord.r - coord.r) + abs(enemy_coord.c - coord.c)
            if 1 <= distance <= stack_height:
                return True
        return False

    def _choose_placement_action(self, legal: list[Action]) -> Action:
        placement_actions = [act for act in legal if isinstance(act, PlaceAction)]
        if not placement_actions:
            return self._choose_placement_action(legal)

        scored_actions = []
        for act in placement_actions:
            coord = act.coord
            score = 0.0

            if (coord.r, coord.c) in {
                (0, 0), (0, BOARD_N - 1),
                (BOARD_N - 1, 0), (BOARD_N - 1, BOARD_N - 1)
            }:
                score -= 100

            if (
                coord.r == 0 or coord.r == BOARD_N - 1
                or coord.c == 0 or coord.c == BOARD_N - 1
            ):
                score -= 20

            if self._can_enemy_cascade_to(coord):
                score -= 80

            centre_r = (BOARD_N - 1) / 2
            centre_c = (BOARD_N - 1) / 2
            dist_from_centre = abs(coord.r - centre_r) + abs(coord.c - centre_c)
            score += 10 * (BOARD_N - dist_from_centre)

            mobility = 0
            for direction in CARDINAL_DIRECTIONS:
                nr = coord.r + direction.r
                nc = coord.c + direction.c
                if 0 <= nr < BOARD_N and 0 <= nc < BOARD_N:
                    if self._board[Coord(nr, nc)] is None:
                        mobility += 1
            score += 5 * mobility

            scored_actions.append((score, act))

        scored_actions.sort(key=lambda item: item[0], reverse=True)
        return scored_actions[0][1]

    def action(self, **referee: dict) -> Action:
        if self._placements_made[self._color] < 4:
            legal = self._get_legal_actions(self._board, self._color)
            return self._choose_placement_action(legal)

        legal = self._get_legal_actions(self._board, self._color)
        random.shuffle(legal)

        # Immediate win
        for act in legal:
            new_board = self._apply_action(self._board, self._color, act)
            if self._check_loss(new_board, self._opponent):
                return act

        # Boxed endgame override
        boxed_action = self._boxed_endgame_action(legal)
        if boxed_action is not None:
            return boxed_action

        safe = [
            act for act in legal
            if self._position_history.count(
                self._board_hash(self._apply_action(self._board, self._color, act))
            ) < 2
        ]
        legal = safe if safe else legal

        best_action = legal[0]
        best_value = float("-inf")

        for act in legal:
            new_board = self._apply_action(self._board, self._color, act)
            search_depth = self._choose_search_depth(self._board, referee)
            value = self._minimax_value(
                board=new_board,
                color=self._opponent,
                depth=search_depth - 1,
                alpha=float("-inf"),
                beta=float("inf")
            )
            if value > best_value:
                best_value = value
                best_action = act

        return best_action

    def update(self, color: PlayerColor, action: Action, **referee: dict):
        self._board = self._apply_action(self._board, color, action)
        self._total_turns += 1
        if color == self._color:
            self._my_turns += 1
        if isinstance(action, PlaceAction):
            self._placements_made[color] += 1
        self._position_history.append(self._board_hash(self._board))

    def _get_legal_actions(self, board: Board, color: PlayerColor) -> list[Action]:
        if self._placements_made[color] < 4:
            total_placed = (
                self._placements_made[PlayerColor.RED]
                + self._placements_made[PlayerColor.BLUE]
            )
            opponent = self._enemy(color)

            def is_adjacent_to_opponent(coord):
                for direction in CARDINAL_DIRECTIONS:
                    nr, nc = coord.r + direction.r, coord.c + direction.c
                    if 0 <= nr < BOARD_N and 0 <= nc < BOARD_N:
                        neighbor = board[Coord(nr, nc)]
                        if neighbor is not None and neighbor[0] == opponent:
                            return True
                return False

            return [
                PlaceAction(coord)
                for coord, stack in board.items()
                if stack is None
                and (total_placed == 0 or not is_adjacent_to_opponent(coord))
            ]

        eats = []
        cascades = []
        moves = []
        enemy_color = self._enemy(color)

        for coord, stack in board.items():
            if stack is None:
                continue
            stack_color, stack_height = stack
            if stack_color != color:
                continue

            for direction in CARDINAL_DIRECTIONS:
                dest_r = coord.r + direction.r
                dest_c = coord.c + direction.c
                if not (0 <= dest_r < BOARD_N and 0 <= dest_c < BOARD_N):
                    continue

                dest = Coord(dest_r, dest_c)
                dest_stack = board[dest]

                if dest_stack is not None:
                    dest_color, dest_height = dest_stack
                    if dest_color == enemy_color and stack_height >= dest_height:
                        eats.append(EatAction(coord, direction))

                if dest_stack is None or dest_stack[0] == color:
                    moves.append(MoveAction(coord, direction))

                if stack_height >= 2:
                    cascades.append(CascadeAction(coord, direction))

        return eats + cascades + moves

    def _apply_action(self, board: Board, color: PlayerColor, action: Action) -> Board:
        new_board = dict(board)

        match action:
            case PlaceAction(coord):
                new_board[coord] = (color, 3)

            case MoveAction(coord, direction):
                source = new_board[coord]
                new_board[coord] = None
                dest = coord + direction
                dest_stack = new_board[dest]
                if dest_stack is None:
                    new_board[dest] = source
                else:
                    source_color, source_height = source
                    _, dest_height = dest_stack
                    new_board[dest] = (source_color, source_height + dest_height)

            case EatAction(coord, direction):
                source = new_board[coord]
                new_board[coord] = None
                dest = coord + direction
                source_color, source_height = source
                new_board[dest] = (source_color, source_height)

            case CascadeAction(coord, direction):
                source = new_board[coord]
                new_board[coord] = None
                source_color, source_height = source
                for i in range(1, source_height + 1):
                    pos_r = coord.r + direction.r * i
                    pos_c = coord.c + direction.c * i
                    if not (0 <= pos_r < BOARD_N and 0 <= pos_c < BOARD_N):
                        break
                    pos = Coord(pos_r, pos_c)
                    if new_board[pos] is not None:
                        self._push(new_board, pos, direction)
                    new_board[pos] = (source_color, 1)

            case _:
                raise ValueError(f"Unknown action type: {action}")

        return new_board

    def _push(self, board: Board, coord: Coord, direction: Direction):
        dest_r = coord.r + direction.r
        dest_c = coord.c + direction.c
        if not (0 <= dest_r < BOARD_N and 0 <= dest_c < BOARD_N):
            board[coord] = None
            return
        dest = Coord(dest_r, dest_c)
        if board[dest] is not None:
            self._push(board, dest, direction)
        board[dest] = board[coord]
        board[coord] = None

    def _minimax_value(
        self,
        board: Board,
        color: PlayerColor,
        depth: int,
        alpha: float,
        beta: float
    ) -> float:
        if self._check_loss(board, self._color):
            return float("-inf")
        if self._check_loss(board, self._opponent):
            return float("inf")
        if depth == 0:
            return self._evaluation_function(board)

        legal = self._get_legal_actions(board, color)
        random.shuffle(legal)

        if color == self._color:
            value = float("-inf")
            for act in legal:
                new_board = self._apply_action(board, color, act)
                value = max(
                    value,
                    self._minimax_value(new_board, self._opponent, depth - 1, alpha, beta)
                )
                alpha = max(alpha, value)
                if value >= beta:
                    break
            return value
        else:
            value = float("inf")
            for act in legal:
                new_board = self._apply_action(board, color, act)
                value = min(
                    value,
                    self._minimax_value(new_board, self._color, depth - 1, alpha, beta)
                )
                beta = min(beta, value)
                if value <= alpha:
                    break
            return value

    def _evaluation_function(self, board: Board) -> float:
        CENTRE_4 = {Coord(3, 3), Coord(3, 4), Coord(4, 3), Coord(4, 4)}

        our_tokens = 0
        opp_tokens = 0
        height_score = 0.0
        centrality_score = 0.0
        our_coords = []
        opp_coords = []

        for coord, stack in board.items():
            if stack is None:
                continue
            color, height = stack
            is_ours = (color == self._color)
            sign = 1 if is_ours else -1

            if is_ours:
                our_tokens += height
                our_coords.append(coord)
            else:
                opp_tokens += height
                opp_coords.append(coord)

            if height < 4:
                height_score += sign * (height - 3)
            elif height >= 4:
                height_score += sign * (7 - height)

            dist = abs(coord.r - 3.5) + abs(coord.c - 3.5)
            base_centrality = (7.0 - dist) / 7.0

            if coord in CENTRE_4 and height >= 4:
                centrality_score += sign * 2.0
            else:
                centrality_score += sign * base_centrality

        aggression_score = 0.0
        if our_coords and opp_coords:
            for our_c in our_coords:
                min_dist = min(
                    abs(our_c.r - opp_c.r) + abs(our_c.c - opp_c.c)
                    for opp_c in opp_coords
                )
                aggression_score += (14.0 - min_dist) / 14.0

        token_diff = our_tokens - opp_tokens
        return (
            10.0 * token_diff
            + 1.0 * aggression_score
            + 2.0 * height_score
            + 1.5 * centrality_score
        )

    def _check_loss(self, board: Board, color: PlayerColor) -> bool:
        return not any(
            stack is not None and stack[0] == color
            for stack in board.values()
        )

    def _enemy(self, color: PlayerColor) -> PlayerColor:
        return PlayerColor.BLUE if color == PlayerColor.RED else PlayerColor.RED

    def _in_bounds(self, coord: Coord) -> bool:
        return 0 <= coord.r < BOARD_N and 0 <= coord.c < BOARD_N

    def _choose_search_depth(self, board: Board, referee: dict) -> int:
        remaining_time = referee["time_remaining"]
        if remaining_time is not None and remaining_time <= 45:
            return 4
        elif remaining_time is not None and remaining_time <= 15:
            return 3
        elif remaining_time is not None and remaining_time <= 5:
            return 2

        total_tokens = sum(
            height
            for stack in board.values()
            if stack is not None
            for _, height in [stack]
        )

        if total_tokens > 10:
            return 5
        elif 6 <= total_tokens <= 10:
            return 6
        return 7

    # =========================================================================
    # Endgame: boxed strategy
    # =========================================================================

    def _is_valid_box(
        self,
        guard_coord: Coord,
        guard_height: int,
        enemy_coord: Coord
    ) -> bool:
        """
        Returns True if our stack at guard_coord (height guard_height) truly
        boxes the enemy at enemy_coord.

        A valid box means: if the enemy tries to cross the guard's row OR the
        guard's column boundary, the guard can cascade them off the board.
        Both directions must hold simultaneously.

        Derivation of the cascade-off condition:
          Guard at column gc cascading LEFT with height h pushes any stack on
          the guard's row to final column gc - h - 1. For this to be off the
          board we need gc - h - 1 < 0, i.e. h >= gc.
          Similarly for RIGHT: final column gc + h + 1 >= BOARD_N → h >= BOARD_N-1-gc.
          Same logic applies to rows for UP/DOWN.
        """
        br, bc = enemy_coord.r, enemy_coord.c
        gr, gc = guard_coord.r, guard_coord.c
        h = guard_height

        # Enemy must be in a strictly different row and column.
        if br == gr or bc == gc:
            return False

        # Guard needs at least height 2 to cascade.
        if h < 2:
            return False

        # Can guard cascade enemy off the board if they cross the row boundary?
        # Enemy would arrive at (gr, bc); guard cascades toward bc.
        if bc < gc:
            can_trap_row = h >= gc           # cascade LEFT, push off left edge
        else:
            can_trap_row = h >= BOARD_N - 1 - gc  # cascade RIGHT, push off right edge

        # Can guard cascade enemy off the board if they cross the col boundary?
        # Enemy would arrive at (br, gc); guard cascades toward br.
        if br < gr:
            can_trap_col = h >= gr           # cascade UP, push off top edge
        else:
            can_trap_col = h >= BOARD_N - 1 - gr  # cascade DOWN, push off bottom edge

        return can_trap_row and can_trap_col

    def _find_boxing_guard(
        self,
        enemy_coord: Coord
    ) -> tuple[Coord, int] | None:
        """
        Finds our stack that forms the tightest valid box around the enemy.
        Returns (coord, height) or None.
        """
        best = None
        best_area = float('inf')

        for coord, height in self._get_stacks_of_color(self._board, self._color):
            if self._is_valid_box(coord, height, enemy_coord):
                area = self._box_area(enemy_coord, coord)
                if area < best_area:
                    best_area = area
                    best = (coord, height)

        return best

    def _boxed_endgame_action(self, legal: list[Action]) -> Action | None:
        """
        Activates when:
          - Opponent has exactly one stack.
          - We have at least two stacks (guard + one for waiting moves).
          - One of our stacks forms a valid box around the opponent.

        Strategy:
          1. Take an immediate win if available.
          2. If opponent is diagonally adjacent to the guard (1 row, 1 col away):
             play a waiting move with any OTHER stack. This forces the opponent
             to break diagonal adjacency, after which we can resume shrinking.
          3. Otherwise: move the guard one step toward the opponent, staying
             off the opponent's row and column, verifying the box still holds.
          4. If no valid boxed move exists, return None (fall back to minimax).
        """
        enemy_stacks = self._get_stacks_of_color(self._board, self._opponent)
        if len(enemy_stacks) != 1:
            return None

        our_stacks = self._get_stacks_of_color(self._board, self._color)
        if len(our_stacks) < 2:
            return None

        enemy_coord, _ = enemy_stacks[0]

        immediate_win = self._find_immediate_win(self._board, self._color, legal)
        if immediate_win is not None:
            return immediate_win

        guard = self._find_boxing_guard(enemy_coord)
        if guard is None:
            return None

        guard_coord, _ = guard
        br, bc = enemy_coord.r, enemy_coord.c
        gr, gc = guard_coord.r, guard_coord.c

        diagonal = (abs(br - gr) == 1 and abs(bc - gc) == 1)

        if diagonal:
            return self._waiting_move(legal, guard_coord)
        else:
            return self._shrink_box_move(legal, guard_coord, enemy_coord)

    def _shrink_box_move(
        self,
        legal: list[Action],
        guard_coord: Coord,
        enemy_coord: Coord
    ) -> Action | None:
        """
        Moves the guard one step toward the enemy without entering the enemy's
        row or column. Verifies the box still holds after the move. Picks the
        move that produces the smallest remaining box.
        """
        br, bc = enemy_coord.r, enemy_coord.c
        gr, gc = guard_coord.r, guard_coord.c

        # Only consider directions that don't land on the enemy's row or col.
        candidate_dirs = []
        if abs(br - gr) > 1:
            candidate_dirs.append(Direction.Up if br < gr else Direction.Down)
        if abs(bc - gc) > 1:
            candidate_dirs.append(Direction.Left if bc < gc else Direction.Right)

        best = None
        best_area = float('inf')

        for direction in candidate_dirs:
            move = next(
                (a for a in legal
                 if isinstance(a, MoveAction)
                 and a.coord == guard_coord
                 and a.direction == direction),
                None
            )
            if move is None:
                continue

            new_gr = gr + direction.r
            new_gc = gc + direction.c
            if not (0 <= new_gr < BOARD_N and 0 <= new_gc < BOARD_N):
                continue
            new_guard_coord = Coord(new_gr, new_gc)

            new_board = self._apply_action(self._board, self._color, move)

            if self._opponent_has_immediate_win(new_board):
                continue

            new_stack = new_board[new_guard_coord]
            if new_stack is None:
                continue
            new_height = new_stack[1]

            if not self._is_valid_box(new_guard_coord, new_height, enemy_coord):
                continue

            area = self._box_area(enemy_coord, new_guard_coord)
            if area < best_area:
                best_area = area
                best = move

        return best

    def _waiting_move(
        self,
        legal: list[Action],
        guard_coord: Coord
    ) -> Action | None:
        """
        Plays the best move (by minimax) with any stack OTHER than the guard.
        Used when opponent is diagonally adjacent — we can't shrink the box
        without entering their row/col, so we pass the move back to them.
        """
        non_guard_legal = [
            act for act in legal
            if not (isinstance(act, MoveAction) and act.coord == guard_coord)
        ]

        if not non_guard_legal:
            return None

        best_action = None
        best_value = float("-inf")

        for act in non_guard_legal:
            new_board = self._apply_action(self._board, self._color, act)

            if self._opponent_has_immediate_win(new_board):
                continue

            value = self._minimax_value(
                board=new_board,
                color=self._opponent,
                depth=DEPTH - 1,
                alpha=float("-inf"),
                beta=float("inf")
            )

            if value > best_value:
                best_value = value
                best_action = act

        return best_action

    # =========================================================================
    # Shared helpers
    # =========================================================================

    def _get_stacks_of_color(
        self,
        board: Board,
        color: PlayerColor
    ) -> list[tuple[Coord, int]]:
        return [
            (coord, stack[1])
            for coord, stack in board.items()
            if stack is not None and stack[0] == color
        ]

    def _find_immediate_win(
        self,
        board: Board,
        color: PlayerColor,
        legal: list[Action] | None = None
    ) -> Action | None:
        opponent = self._enemy(color)
        if legal is None:
            legal = self._get_legal_actions(board, color)
        for act in legal:
            new_board = self._apply_action(board, color, act)
            if self._check_loss(new_board, opponent):
                return act
        return None

    def _opponent_has_immediate_win(self, board: Board) -> bool:
        for act in self._get_legal_actions(board, self._opponent):
            new_board = self._apply_action(board, self._opponent, act)
            if self._check_loss(new_board, self._color):
                return True
        return False

    def _box_area(self, enemy_coord: Coord, guard_coord: Coord) -> int:
        """
        Area of the sub-rectangle the enemy is trapped in, bounded by
        the guard's row and column on one side and the board edge on the other.
        """
        row_size = (
            guard_coord.r if enemy_coord.r < guard_coord.r
            else BOARD_N - guard_coord.r - 1
        )
        col_size = (
            guard_coord.c if enemy_coord.c < guard_coord.c
            else BOARD_N - guard_coord.c - 1
        )
        return row_size * col_size