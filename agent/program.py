# COMP30024 Artificial Intelligence, Semester 1 2026
# Project Part B: Game Playing Agent





from referee.game import PlayerColor, Coord, Direction, \
    Action, PlaceAction, MoveAction, EatAction, CascadeAction, BOARD_N


DEPTH = 2
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


    def _get_legal_actions(self, board: Board, color: PlayerColor) -> list[Action]:
        

            # Placement phase: if this colour has not placed 4 stacks yet,
            # return all empty board cells as legal placement actions.
            if self._placements_made[color] < 4:
                return [
                    PlaceAction(coord)
                    for coord, stack in board.items()
                    if stack is None
                ]

            eats = []
            cascades = []
            moves = []

            enemy_color = (
                PlayerColor.BLUE if color == PlayerColor.RED
                else PlayerColor.RED
            )

            enemy_coords = {
                coord
                for coord, stack in board.items()
                if stack is not None and stack[0] == enemy_color
            }

            for coord, stack in board.items():
                if stack is None:
                    continue

                stack_color, stack_height = stack

                # Only generate actions for this player's own stacks.
                if stack_color != color:
                    continue

                for direction in Direction:
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

                    # MOVE: destination is empty or has friendly stack.
                    if dest_stack is None or dest_stack[0] == color:
                        moves.append(MoveAction(coord, direction))

                    # CASCADE: stack height must be at least 2.
                    if stack_height >= 2:
                        cascades.append(CascadeAction(coord, direction))

            return eats + cascades + moves
    
   
    def action(self, **referee: dict) -> Action:
        # Placement phase
        if self._placements_made[self._color] < 4:
            i = self._placements_made[self._color]
            if self._color == PlayerColor.RED:
                return PlaceAction(Coord(0, i))
            else:
                return PlaceAction(Coord(7, i))

        # Minimax decision: try every action, pick the one with highest minimax value
        best_action = None
        best_value = float('-inf')

        legal = self._get_legal_actions(self._board, self._color)        
        if not legal:
            return best_action

        for act in legal:
            new_board = self._apply_action(self._board, self._color, act)
            value = self._minimax_value(
                board=new_board,
                color=self._opponent,
                depth=DEPTH - 1,
                alpha=float('-inf'),
                beta=float('inf')
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

    def _apply_action(
        self,
        board: Board,
        color: PlayerColor,
        action: Action
    ) -> Board:

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

        # Important: check bounds BEFORE constructing Coord.
        if not (0 <= dest_r < BOARD_N and 0 <= dest_c < BOARD_N):
            board[coord] = None
            return

        dest = Coord(dest_r, dest_c)

        if board[dest] is not None:
            self._push(board, dest, direction)

        board[dest] = board[coord]
        board[coord] = None

        def _in_bounds(self, coord: Coord) -> bool:
            return 0 <= coord.r < BOARD_N and 0 <= coord.c < BOARD_N
        
    
    