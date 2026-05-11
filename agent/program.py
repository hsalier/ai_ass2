# COMP30024 Artificial Intelligence, Semester 1 2026
# Project Part B: Game Playing Agent

from referee.game import PlayerColor, Coord, Direction, \
    Action, PlaceAction, MoveAction, EatAction, CascadeAction, BOARD_N


DEPTH = 2
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

    def action(self, **referee: dict) -> Action:
        """
        Called when it is this agent's turn.
        Chooses an action to return to the referee.
        """

        # Hardcoded placement phase for now.
        if self._placements_made[self._color] < 4:
            i = self._placements_made[self._color]

            if self._color == PlayerColor.RED:
                return PlaceAction(Coord(0, i))
            else:
                return PlaceAction(Coord(7, i))

        # Play phase: use minimax to choose the best action.
        legal = self._get_legal_actions(self._board, self._color)

        if not legal:
            raise ValueError("No legal actions available")

        best_action = legal[0]
        best_value = float("-inf")

        for act in legal:
            new_board = self._apply_action(self._board, self._color, act)

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

    def _get_legal_actions(self, board: Board, color: PlayerColor) -> list[Action]:
        """
        Returns legal actions for the given player colour.
        """

        # Placement phase: if this colour has placed fewer than 4 stacks,
        # all empty squares are legal placement actions.
        if self._placements_made[color] < 4:
            return [
                PlaceAction(coord)
                for coord, stack in board.items()
                if stack is None
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

        if not legal:
            return self._evaluation_function(board)

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
        Basic heuristic evaluation from this agent's perspective.

        Positive = good for us.
        Negative = good for opponent.
        """

        our_total_height = 0
        opponent_total_height = 0

        our_stack_count = 0
        opponent_stack_count = 0

        for stack in board.values():
            if stack is None:
                continue

            color, height = stack

            if color == self._color:
                our_total_height += height
                our_stack_count += 1
            else:
                opponent_total_height += height
                opponent_stack_count += 1

        height_score = our_total_height - opponent_total_height
        stack_score = our_stack_count - opponent_stack_count

        return height_score + 0.5 * stack_score

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