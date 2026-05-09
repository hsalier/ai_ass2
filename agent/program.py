# COMP30024 Artificial Intelligence, Semester 1 2026
# Project Part B: Game Playing Agent





from referee.game import PlayerColor, Coord, Direction, \
    Action, PlaceAction, MoveAction, EatAction, CascadeAction, BOARD_N



Stack = tuple[PlayerColor, int]   # (colour, height)
Board = dict[Coord, Stack | None]

class Agent:
    
    def __init__(self, color: PlayerColor, **referee: dict):
        """
        Runs once when the referee creates this agent.
        Sets up the agent's internal game state.
        """

        # The colour this agent is playing as
        self._color = color

        # The opponent's colour
        self._opponent = (
            PlayerColor.BLUE if color == PlayerColor.RED
            else PlayerColor.RED
        )

        # Internal board representation:
        # key: Coord
        # value: None OR (PlayerColor, height)
        self._board: dict[Coord, tuple[PlayerColor, int] | None] = {
            Coord(r, c): None
            for r in range(BOARD_N)
            for c in range(BOARD_N)
        }

        # Number of total turns that have happened in the game
        self._total_turns = 0

        # Number of placements made by each player
        self._placements_made = {
            PlayerColor.RED: 0,
            PlayerColor.BLUE: 0,
        }

        # Number of turns made by this agent only
        self._my_turns = 0

    def action(self, **referee: dict) -> Action:
        """
        Called when it is this agent's turn.
        For now, this returns simple hardcoded placement actions.
        """

        # Placement phase: each player places 4 stacks.
        if self._placements_made[self._color] < 4:
            i = self._placements_made[self._color]

            if self._color == PlayerColor.RED:
                return PlaceAction(Coord(0, i))
            else:
                return PlaceAction(Coord(7, i))

        # Temporary play-phase fallback.
        # This is not strategically correct yet and may become invalid later.
        if self._color == PlayerColor.RED:
            return CascadeAction(Coord(0, 3), Direction.Left)
        else:
            return MoveAction(Coord(7, 0), Direction.Up)

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


    def _apply_action(
        self,
        board: Board,
        color: PlayerColor,
        action: Action
    ) -> Board:
        """
        Applies a valid action to a copied board and returns the new board.
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
                    pos = Coord(
                        coord.r + direction.r * i,
                        coord.c + direction.c * i
                    )

                    if not self._in_bounds(pos):
                        break

                    if new_board[pos] is not None:
                        self._push(new_board, pos, direction)

                    new_board[pos] = (source_color, 1)

            case _:
                raise ValueError(f"Unknown action type: {action}")

        return new_board


    def _push(self, board: Board, coord: Coord, direction: Direction):
        """
        Pushes one stack in the given direction.
        Removes it if pushed off the board.
        """

        dest = Coord(
            coord.r + direction.r,
            coord.c + direction.c
        )

        if not self._in_bounds(dest):
            board[coord] = None
            return

        if board[dest] is not None:
            self._push(board, dest, direction)

        board[dest] = board[coord]
        board[coord] = None


    def _in_bounds(self, coord: Coord) -> bool:
        return 0 <= coord.r < BOARD_N and 0 <= coord.c < BOARD_N