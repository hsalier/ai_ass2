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

Stack = tuple[PlayerColor, int]      # (colour, height)
Board = dict[Coord, Stack | None]    # Coord -> stack or empty


class Agent:

    def __init__(self, color: PlayerColor, **referee: dict):
        """
        Runs once when the referee creates this agent.
        Sets up the agent's internal game state.
        """

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
        """
        Returns True if the opponent has a stack that could immediately cascade
        onto this coordinate.

        A cascade can affect squares in the same row or column up to the
        cascading stack's height.
        """

        enemy = self._opponent

        for enemy_coord, stack in self._board.items():
            if stack is None:
                continue

            stack_color, stack_height = stack

            if stack_color != enemy:
                continue

            # Enemy stack must have height at least 2 to cascade.
            if stack_height < 2:
                continue

            same_row = enemy_coord.r == coord.r
            same_col = enemy_coord.c == coord.c

            if not same_row and not same_col:
                continue

            distance = abs(enemy_coord.r - coord.r) + abs(enemy_coord.c - coord.c)

            # If coord is within cascade range, enemy can immediately affect it.
            if 1 <= distance <= stack_height:
                return True

        return False

    # Function for strategic placing
    def _choose_placement_action(self, legal: list[Action]) -> Action:
        """
        Chooses a placement action using a simple rule-based strategy.

        Strategy:
        - Avoid corners.
        - Avoid edges where possible.
        - Avoid squares that can be immediately cascaded by the opponent.
        - Prefer central, mobile squares.
        - Friendly adjacency is allowed.
        """

        placement_actions = [
            act for act in legal
            if isinstance(act, PlaceAction)
        ]

        if not placement_actions:
            return self._choose_placement_action(legal)

        scored_actions = []

        for act in placement_actions:
            coord = act.coord
            score = 0.0

            # ============================================================
            # DO NOT DO rules / penalties
            # ============================================================

            # Avoid corners strongly
            if (coord.r, coord.c) in {
                (0, 0), (0, BOARD_N - 1),
                (BOARD_N - 1, 0), (BOARD_N - 1, BOARD_N - 1)
            }:
                score -= 100

            # Avoid edges unless necessary
            if (
                coord.r == 0 or coord.r == BOARD_N - 1
                or coord.c == 0 or coord.c == BOARD_N - 1
            ):
                score -= 20

            # Avoid placing somewhere the opponent can immediately cascade onto
            if self._can_enemy_cascade_to(coord):
                score -= 80

            # ============================================================
            # Rough positive guidelines
            # ============================================================

            # Prefer central-ish squares
            centre_r = (BOARD_N - 1) / 2
            centre_c = (BOARD_N - 1) / 2
            dist_from_centre = abs(coord.r - centre_r) + abs(coord.c - centre_c)

            score += 10 * (BOARD_N - dist_from_centre)

            # Prefer mobility: number of empty neighbouring squares
            mobility = 0

            for direction in CARDINAL_DIRECTIONS:
                nr = coord.r + direction.r
                nc = coord.c + direction.c

                if 0 <= nr < BOARD_N and 0 <= nc < BOARD_N:
                    neighbour = self._board[Coord(nr, nc)]

                    if neighbour is None:
                        mobility += 1

            score += 5 * mobility

            scored_actions.append((score, act))

        scored_actions.sort(key=lambda item: item[0], reverse=True)

        return scored_actions[0][1]
    
    
    
    
    
    def action(self, **referee: dict) -> Action:
        """
        Called when it is this agent's turn.
        Chooses an action to return to the referee.
        """

        if self._placements_made[self._color] < 4:
            legal = self._get_legal_actions(self._board, self._color)
            return self._choose_placement_action(legal)

        # Play phase: use minimax to choose the best action.
        legal = self._get_legal_actions(self._board, self._color)
        random.shuffle(legal)

        # 1. If we can immediately win, always do it.
        for act in legal:
            new_board = self._apply_action(self._board, self._color, act)
            if self._check_loss(new_board, self._opponent):
                return act

        # 2. Simple boxed-endgame override.
        # If Blue has one stack left and is already boxed by one of our Red stacks,
        # use that Red stack to keep shrinking the box.
        boxed_endgame_action = self._boxed_endgame_action(legal)

        if boxed_endgame_action is not None:
            return boxed_endgame_action

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
        """
        Called after either player takes a valid action.
        Updates this agent's internal board state.
        """

        self._board = self._apply_action(self._board, color, action)

        self._total_turns += 1

        if color == self._color:
            self._my_turns += 1

        if isinstance(action, PlaceAction):
            self._placements_made[color] += 1
        
        self._position_history.append(self._board_hash(self._board))

    def _get_legal_actions(self, board: Board, color: PlayerColor) -> list[Action]:
        """
        Returns legal actions for the given player colour.
        """

        # Placement phase: if this colour has placed fewer than 4 stacks,
        # all empty squares are legal placement actions.
        if self._placements_made[color] < 4:
            total_placed = self._placements_made[PlayerColor.RED] + self._placements_made[PlayerColor.BLUE]
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

            # Only generate actions for this player's own stacks.
            if stack_color != color:
                continue

            for direction in CARDINAL_DIRECTIONS:
                dest_r = coord.r + direction.r
                dest_c = coord.c + direction.c

                # Check bounds before constructing Coord.
                if not (0 <= dest_r < BOARD_N and 0 <= dest_c < BOARD_N):
                    continue

                dest = Coord(dest_r, dest_c)
                dest_stack = board[dest]

                # EAT: destination has enemy stack and attacker is tall enough.
                if dest_stack is not None:
                    dest_color, dest_height = dest_stack

                    if dest_color == enemy_color and stack_height >= dest_height:
                        eats.append(EatAction(coord, direction))

                # MOVE: destination is empty or friendly.
                if dest_stack is None or dest_stack[0] == color:
                    moves.append(MoveAction(coord, direction))

                # CASCADE: stack height must be at least 2.
                if stack_height >= 2:
                    cascades.append(CascadeAction(coord, direction))

        # Simple priority ordering.
        return eats + cascades + moves

    def _apply_action(
        self,
        board: Board,
        color: PlayerColor,
        action: Action
    ) -> Board:
        """
        Applies a valid action to a copied board and returns the new board.
        Assumes the action is already valid.
        """

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
                    dest_color, dest_height = dest_stack

                    new_board[dest] = (
                        source_color,
                        source_height + dest_height
                    )

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

                    # Check bounds before constructing Coord.
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
        """
        Pushes a stack one square in the given direction.
        If pushed off the board, the stack is removed.
        """

        dest_r = coord.r + direction.r
        dest_c = coord.c + direction.c

        # Check bounds before constructing Coord.
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
        """
        Returns the minimax value of board from this agent's perspective.
        color is whose turn it is at this node.
        """

        # Terminal: we have no stacks left.
        if self._check_loss(board, self._color):
            return float("-inf")

        # Terminal: opponent has no stacks left.
        if self._check_loss(board, self._opponent):
            return float("inf")

        # Cutoff: depth reached.
        if depth == 0:
            return self._evaluation_function(board)

        legal = self._get_legal_actions(board, color)
        random.shuffle(legal)

        if color == self._color:
            # MAX node: our turn.
            value = float("-inf")

            for act in legal:
                new_board = self._apply_action(board, color, act)

                value = max(
                    value,
                    self._minimax_value(
                        board=new_board,
                        color=self._opponent,
                        depth=depth - 1,
                        alpha=alpha,
                        beta=beta
                    )
                )

                alpha = max(alpha, value)

                if value >= beta:
                    break

            return value

        else:
            # MIN node: opponent's turn.
            value = float("inf")

            for act in legal:
                new_board = self._apply_action(board, color, act)

                value = min(
                    value,
                    self._minimax_value(
                        board=new_board,
                        color=self._color,
                        depth=depth - 1,
                        alpha=alpha,
                        beta=beta
                    )
                )

                beta = min(beta, value)

                if value <= alpha:
                    break

            return value

    def _evaluation_function(self, board: Board) -> float:
        """
        Heuristic evaluation from this agent's perspective.
        Positive = good for us, negative = good for opponent.

        Components (in order of weight):
        1. Token differential  — primary signal
        2. Aggression          — reward proximity/threat to opponent
        3. Height optimality   — penalise stacks outside ideal range [3, 6]
        4. Centrality          — reward central position, especially h>=4 in centre 4
        """

        CENTRE_4 = {Coord(3, 3), Coord(3, 4), Coord(4, 3), Coord(4, 4)}

        our_tokens      = 0
        opp_tokens      = 0
        height_score    = 0.0
        centrality_score = 0.0

        our_coords = []
        opp_coords = []

        for coord, stack in board.items():
            if stack is None:
                continue

            color, height = stack
            is_ours = (color == self._color)
            sign = 1 if is_ours else -1

            # --- Token count ---
            if is_ours:
                our_tokens += height
                our_coords.append(coord)
            else:
                opp_tokens += height
                opp_coords.append(coord)

            # --- Height optimality ---
            # Ideal range is [3, 6]. Penalise stacks outside it.
            # Sign flips for opponent: we benefit if they have bad heights.
            if height < 4:
                height_score += sign * (height - 3)   # e.g. h=1 → -2, h=2 → -1
            elif height >= 4:
                height_score += sign * (7 - height)   # e.g. h=7 → -1, h=8 → -2

            # --- Centrality ---
            # Manhattan distance from board centre (3.5, 3.5); max possible = 7.
            dist = abs(coord.r - 3.5) + abs(coord.c - 3.5)
            base_centrality = (7.0 - dist) / 7.0   # 0 at corner, ~1 near centre

            # Special bonus: h>=4 in centre 4 squares dominates any row/col
            if coord in CENTRE_4 and height >= 4:
                centrality_score += sign * 2.0
            else:
                centrality_score += sign * base_centrality

        # --- Aggression ---
        # For each of our stacks, reward being close to the nearest opponent.
        # Max Manhattan distance on an 8x8 board is 14; we normalise to [0, 1].
        aggression_score = 0.0
        if our_coords and opp_coords:
            for our_c in our_coords:
                min_dist = min(
                    abs(our_c.r - opp_c.r) + abs(our_c.c - opp_c.c)
                    for opp_c in opp_coords
                )
                aggression_score += (14.0 - min_dist) / 14.0

        # --- Weighted sum ---
        token_diff = our_tokens - opp_tokens

        return (
            10.0 * token_diff       +   # primary: raw material advantage
            1.0 * aggression_score +   # secondary: stay threatening
            2.0 * height_score     +   # tertiary: stack health
            1.5 * centrality_score     # quaternary: board position
        )

    def _check_loss(self, board: Board, color: PlayerColor) -> bool:
        """
        Returns True if the given colour has no stacks left.
        """

        return not any(
            stack is not None and stack[0] == color
            for stack in board.values()
        )

    def _enemy(self, color: PlayerColor) -> PlayerColor:
        """
        Returns the opposite player colour.
        """

        return (
            PlayerColor.BLUE if color == PlayerColor.RED
            else PlayerColor.RED
        )

    def _in_bounds(self, coord: Coord) -> bool:
        """
        Returns True if coord is inside the board.
        """

        return 0 <= coord.r < BOARD_N and 0 <= coord.c < BOARD_N
        
    def _choose_search_depth(self, board: Board, referee: dict) -> int:
        """
        Chooses minimax depth based on remaining time and board complexity.

        Main rule:
        - If the referee says there are 2 minutes 30 seconds or less remaining,
        force depth down to 4.

        Otherwise:
        - Use deeper search when the board is simpler.
        - Use shallower search when the board has many legal actions/stacks.
        """

        # ------------------------------------------------------------
        # Time-based depth control
        # ------------------------------------------------------------
        # The referee dictionary may contain remaining time under different
        # possible names depending on the project scaffold.
        #
        remaining_time = referee["time_remaining"]

        if remaining_time is not None and remaining_time <= 45:
            return 4
        elif remaining_time is not None and remaining_time <= 15:
            return 3
        elif remaining_time is not None and remaining_time <= 5:
            return 2
        

        # ------------------------------------------------------------
        # Board-complexity depth control
        # ------------------------------------------------------------

        total_tokens = sum(
            height
            for stack in board.values()
            if stack is not None
            for _, height in [stack]
        )

        # Very complex board: many options, so search less deeply.
        if total_tokens > 10:
            return 5

        # Medium-complexity board.
        elif 6 <= total_tokens <= 10:
            return 6

        # Endgame / very few stacks.
        return 6
    
    def _boxed_endgame_action(self, legal: list[Action]) -> Action | None:
        """
        Simple hardcoded endgame strategy.

        Activates only when:
        - Opponent has exactly one stack.
        - We have total token count >= 7.
        - One of our stacks is already boxing the opponent into a smaller grid.

        Once activated:
        - If we can immediately win, win.
        - Otherwise, move the boxing stack inward to shrink the box.
        - If no safe boxed move exists, fall back to minimax.
        """

        enemy_stacks = self._get_stacks_of_color(self._board, self._opponent)
        our_total_tokens = self._total_tokens(self._board, self._color)

        # Only use this endgame rule in the specific winning-material case.
        if len(enemy_stacks) != 1:
            return None

        if our_total_tokens < 7:
            return None

        enemy_coord, enemy_height = enemy_stacks[0]

        # If we can win immediately, do it.
        immediate_win = self._find_immediate_win(self._board, self._color, legal)

        if immediate_win is not None:
            return immediate_win

        # Find a Red stack that is already boxing Blue.
        boxed_info = self._boxed_guard(enemy_coord)

        if boxed_info is None:
            return None

        guard_coord, guard_height = boxed_info

        candidates = []

        for act in legal:
            # For the simplified strategy, only move the boxing Red stack.
            if not isinstance(act, MoveAction):
                continue

            if act.coord != guard_coord:
                continue

            new_board = self._apply_action(self._board, self._color, act)

            # Do not choose a move that lets Blue immediately win.
            if self._opponent_has_immediate_win(new_board):
                continue

            # After the move, Blue must still be boxed by the moved guard stack.
            new_guard_coord = guard_coord + act.direction

            if not self._in_bounds(new_guard_coord):
                continue

            new_guard_stack = new_board[new_guard_coord]

            if new_guard_stack is None:
                continue

            new_guard_color, new_guard_height = new_guard_stack

            if new_guard_color != self._color:
                continue

            # Blue should still be boxed after this move.
            if not self._is_boxed_by_guard(
                blue_coord=enemy_coord,
                guard_coord=new_guard_coord,
                guard_height=new_guard_height
            ):
                continue

            old_box_area = self._box_area(enemy_coord, guard_coord)
            new_box_area = self._box_area(enemy_coord, new_guard_coord)

            # We want moves that shrink Blue's available box.
            shrink_amount = old_box_area - new_box_area

            if shrink_amount <= 0:
                continue

            # Prefer:
            # - shrinking the box more
            # - keeping / making the guard taller
            # - staying reasonably central, so the guard can still cascade well
            centre_dist = abs(new_guard_coord.r - 3.5) + abs(new_guard_coord.c - 3.5)

            score = (
                100.0 * shrink_amount
                + 5.0 * new_guard_height
                - 2.0 * centre_dist
            )

            candidates.append((score, act))

        if not candidates:
            return None

        candidates.sort(key=lambda item: item[0], reverse=True)

        return candidates[0][1]
    
    def _get_stacks_of_color(
        self,
        board: Board,
        color: PlayerColor
    ) -> list[tuple[Coord, int]]:
        """
        Returns all stacks belonging to a given color as (coord, height).
        """

        stacks = []

        for coord, stack in board.items():
            if stack is None:
                continue

            stack_color, stack_height = stack

            if stack_color == color:
                stacks.append((coord, stack_height))

        return stacks


    def _total_tokens(self, board: Board, color: PlayerColor) -> int:
        """
        Returns the total token count for one player.
        Example: R3 + R4 = 7 tokens.
        """

        total = 0

        for stack in board.values():
            if stack is None:
                continue

            stack_color, stack_height = stack

            if stack_color == color:
                total += stack_height

        return total


    def _find_immediate_win(
        self,
        board: Board,
        color: PlayerColor,
        legal: list[Action] | None = None
    ) -> Action | None:
        """
        Returns an action that immediately removes the opponent's last stack.
        """

        opponent = self._enemy(color)

        if legal is None:
            legal = self._get_legal_actions(board, color)

        for act in legal:
            new_board = self._apply_action(board, color, act)

            if self._check_loss(new_board, opponent):
                return act

        return None


    def _opponent_has_immediate_win(self, board: Board) -> bool:
        """
        Returns True if the opponent can immediately win from this board.
        This prevents our hardcoded strategy from walking into obvious losses.
        """

        opponent_legal = self._get_legal_actions(board, self._opponent)

        for act in opponent_legal:
            new_board = self._apply_action(board, self._opponent, act)

            if self._check_loss(new_board, self._color):
                return True

        return False
    
    def _boxed_guard(self, blue_coord: Coord) -> tuple[Coord, int] | None:
        """
        Finds one of our Red stacks that is already boxing Blue into a smaller grid.

        A Red stack boxes Blue if:
        - The Red stack is not on the outer edge.
        - Blue is not on the same row or column as the Red stack.
        - The Red stack's row and column form internal boundaries.
        - Blue is therefore trapped inside one of the four smaller rectangles
        formed by the Red stack's row and column.

        This is intentionally simple and conservative.
        """

        candidates = []

        for red_coord, red_height in self._get_stacks_of_color(self._board, self._color):

            if self._is_boxed_by_guard(
                blue_coord=blue_coord,
                guard_coord=red_coord,
                guard_height=red_height
            ):
                area = self._box_area(blue_coord, red_coord)

                centre_dist = abs(red_coord.r - 3.5) + abs(red_coord.c - 3.5)

                score = (
                    -10.0 * area
                    + 5.0 * red_height
                    - 2.0 * centre_dist
                )

                candidates.append((score, red_coord, red_height))

        if not candidates:
            return None

        candidates.sort(key=lambda item: item[0], reverse=True)

        _, best_coord, best_height = candidates[0]

        return best_coord, best_height


    def _is_boxed_by_guard(
        self,
        blue_coord: Coord,
        guard_coord: Coord,
        guard_height: int
    ) -> bool:
        """
        Returns True if guard_coord acts like an internal row/column wall
        that boxes Blue into a smaller region of the board.

        The guard does not need to be R5 here, because this helper is only
        detecting an already-good boxed position. The actual action choice
        still checks that the box remains valid after moving.
        """

        # A stack of height 1 cannot cascade, so it is not a real wall.
        if guard_height < 2:
            return False

        # The guard's row and column need to be internal boundaries.
        # If it is on the edge, it does not create a smaller box.
        if guard_coord.r == 0 or guard_coord.r == BOARD_N - 1:
            return False

        if guard_coord.c == 0 or guard_coord.c == BOARD_N - 1:
            return False

        # If Blue is on the same row/column already, then this is not a box;
        # it is either an immediate tactical position or a danger line.
        if blue_coord.r == guard_coord.r:
            return False

        if blue_coord.c == guard_coord.c:
            return False

        return True


    def _box_area(self, blue_coord: Coord, guard_coord: Coord) -> int:
        """
        Calculates the area of the smaller rectangle that Blue is trapped in,
        using the guard's row and column as internal walls.

        Example:
        If guard is at (4, 4) and Blue is in the top-left region,
        then Blue's box is rows 0..3 and cols 0..3, area 16.
        """

        if blue_coord.r < guard_coord.r:
            row_size = guard_coord.r
        else:
            row_size = BOARD_N - guard_coord.r - 1

        if blue_coord.c < guard_coord.c:
            col_size = guard_coord.c
        else:
            col_size = BOARD_N - guard_coord.c - 1

        return row_size * col_size