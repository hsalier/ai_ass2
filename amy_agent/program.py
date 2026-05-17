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

        #override the winning, check if it works
        for act in legal:
            new_board = self._apply_action(self._board, self._color, act)
            if self._check_loss(new_board, self._opponent):
                return act

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
        # Common possibilities:
        # - "time_remaining"
        # - "remaining_time"
        # - "time"
        #
        # This code safely checks all of them.
        remaining_time = (
            referee.get("time_remaining")
            or referee.get("remaining_time")
            or referee.get("time")
        )

        # 2 minutes 30 seconds = 150 seconds
        if remaining_time is not None and remaining_time <= 150:
            return 4

        # ------------------------------------------------------------
        # Board-complexity depth control
        # ------------------------------------------------------------
        legal_count = len(self._get_legal_actions(board, self._color))

        stack_count = sum(
            1 for stack in board.values()
            if stack is not None
        )

        total_tokens = sum(
            height
            for stack in board.values()
            if stack is not None
            for _, height in [stack]
        )

        # Very complex board: many options, so search less deeply.
        if legal_count >= 35 or stack_count >= 18 or total_tokens >= 45:
            return 5

        # Medium-complexity board.
        if legal_count >= 20 or stack_count >= 12 or total_tokens >= 30:
            return 5

        # Simpler board.
        if legal_count >= 10 or stack_count >= 7:
            return 5

        # Endgame / very few stacks.
        return 6