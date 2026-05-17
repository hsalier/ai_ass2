# COMP30024 Artificial Intelligence, Semester 1 2026
# Project Part B: Game Playing Agent

from referee.game import PlayerColor, Coord, Direction, \
    Action, PlaceAction, MoveAction, EatAction, CascadeAction
from referee.game.board import Board
from referee.game.coord import CARDINAL_DIRECTIONS
from .helper import get_stack_coords, proximity_score
from .heuristic import h_play
import math
from referee.game.constants import BOARD_N
from referee.game.exceptions import IllegalActionException
import random
POSSIBLE_ACTIONS = (MoveAction, EatAction, CascadeAction)
CUTOFF_DEPTH = 3

class Agent:
    """
    This class is the "entry point" for your agent, providing an interface to
    respond to various Cascade game events.
    """

    def __init__(self, color: PlayerColor, **referee: dict):
        """
        This constructor method runs when the referee instantiates the agent.
        Any setup and/or precomputation should be done here.
        """
        self._color = color
        self._turn_count = 0
        self._board = Board()
        self._tt = {}

        self._zobrist_table = {}
        for r in range(BOARD_N):
            for c in range(BOARD_N):
                for col in [PlayerColor.RED, PlayerColor.BLUE]:
                    for h in range(1,13):
                        self._zobrist_table[(r,c,col,h)] = random.getrandbits(64)
        match color:
            case PlayerColor.RED:
                print("Testing: I am playing as RED (first player)")
            case PlayerColor.BLUE:
                print("Testing: I am playing as BLUE")
        self._zobrist_turn= { PlayerColor.RED: random.getrandbits(64), PlayerColor.BLUE: random.getrandbits(64)}
        self._turn_flip_mask = self._zobrist_turn[PlayerColor.RED] ^  self._zobrist_turn[PlayerColor.BLUE]
    
    def compute_root_hash(self, board):
        h = self._zobrist_turn[board._turn_color]
        for r in range(BOARD_N):
            for c in range(BOARD_N):
                cell = board[Coord(r,c)]
                if not cell.is_empty:
                    h ^= self._zobrist_table[(r,c,cell.color,cell.height)]
        return h
    def max_value(self, board, current_hash, a, b, current_depth)-> float:
        depth_left = current_depth + CUTOFF_DEPTH - board.play_phase_turn_count
        if depth_left <= 0:
            eval = h_play(board)
            return eval
        if current_hash in self._tt:
            cached_depth,cached_value = self._tt[current_hash]
            if cached_depth >= depth_left:
                return cached_value
        
        coords = get_stack_coords(board, board._turn_color)
        best_v = -math.inf
                                  
        for coord in coords:                         
            for direction in CARDINAL_DIRECTIONS:
                for action in POSSIBLE_ACTIONS:
                    try:
                        mutation = board.apply_action(action(coord, direction))
                    except IllegalActionException:
                        continue
                    try:
                        next_hash = current_hash^ self._turn_flip_mask

                        for cells in mutation.cell_mutations:
                            if not cells.prev.is_empty:
                                next_hash ^= self._zobrist_table[(cells.cell.r,cells.cell.c, cells.prev.color, cells.prev.height)]
                            if not cells.next.is_empty:
                                next_hash ^= self._zobrist_table[(cells.cell.r,cells.cell.c, cells.next.color, cells.next.height)]
                        
                                
                        v =  self.min_value(board,next_hash, a, b, current_depth)
                        best_v = max(best_v,v)
                        if best_v >= b:
                            self._tt[current_hash] = (depth_left,best_v)
                            return best_v
                        a = max(a,best_v)
                    finally:
                        board.undo_action()

        self._tt[current_hash] = (depth_left,best_v)                
        return best_v

    def min_value(self, board,current_hash, a, b, current_depth) -> float:
        depth_left = current_depth + CUTOFF_DEPTH - board.play_phase_turn_count
        if depth_left <= 0:
            eval = h_play(board)
            return eval
        if current_hash in self._tt:
            cached_depth,cached_value = self._tt[current_hash]
            if cached_depth >= depth_left:
                return cached_value
        
        coords = get_stack_coords(board, board._turn_color)
        best_v = math.inf                          
        for coord in coords:                         
            for direction in CARDINAL_DIRECTIONS:
                for action in POSSIBLE_ACTIONS:
                    try:
                        mutation = board.apply_action(action(coord, direction))
                    except IllegalActionException:
                        continue
                    try:
                        next_hash = current_hash^ self._turn_flip_mask

                        for cells in mutation.cell_mutations:
                            if not cells.prev.is_empty:
                                next_hash ^= self._zobrist_table[(cells.cell.r,cells.cell.c, cells.prev.color, cells.prev.height)]
                            if not cells.next.is_empty:
                                next_hash ^= self._zobrist_table[(cells.cell.r,cells.cell.c, cells.next.color, cells.next.height)]
                        
                                
                        v =  self.max_value(board,next_hash, a, b, current_depth)
                        best_v = min(best_v,v)
                        if best_v <= a:
                            self._tt[current_hash] = (depth_left, best_v)
                            return best_v
                        b = min(b,best_v)
                    finally:
                        board.undo_action()
        self._tt[current_hash] = (depth_left,best_v)                
        return best_v
    def action(self, **referee: dict) -> Action:
        """
        This method is called by the referee each time it is the agent's turn
        to take an action. It must always return an action object.
        """

        # Below we have hardcoded actions to be played depending on whether
        # the agent is playing as BLUE or RED. Obviously this won't work beyond
        # the initial moves of the game, so you should use some game playing
        # technique(s) to determine the best action to take.

        # During placement phase (first 8 turns total, 4 per player)
        
        if self._turn_count < 4:
            match self._color:
                case PlayerColor.RED:
                    red_scores = {}
                    for r in range (BOARD_N):
                        for c in range(BOARD_N):
                            try:
                                self._board.apply_action(PlaceAction(Coord(r,c)))
                                red_scores[(r,c)] = proximity_score(self._board,Coord(r,c))
                                self._board.undo_action()
                            except Exception:
                                continue
                    best_coord = max(red_scores, key = lambda x: red_scores[x])
                    return PlaceAction(Coord(best_coord[0],best_coord[1]))
                case PlayerColor.BLUE:
                    blue_scores = {}
                    for r in range (BOARD_N):
                        for c in range(BOARD_N):
                            try:
                                self._board.apply_action(PlaceAction(Coord(r,c)))
                                blue_scores[(r,c)] = proximity_score(self._board,Coord(r,c))
                                self._board.undo_action()
                            except Exception:
                                continue
                    best_coord = max(blue_scores, key = lambda x: blue_scores[x])
                    return PlaceAction(Coord(best_coord[0],best_coord[1]))

        
        
        
   
             
        # During play phase
        board = self._board
        root_hash = self.compute_root_hash(board)
        match self._color:
            case PlayerColor.RED:
                coords = get_stack_coords(board, PlayerColor.RED)
                value = {}
                a = - math.inf
                b = math.inf
                for coord in coords:                       
                    for direction in CARDINAL_DIRECTIONS:
                        for action in POSSIBLE_ACTIONS:
                            try:
                                mutation = board.apply_action(action(coord, direction))
                            except IllegalActionException:
                                continue
                            try:
                                next_hash = root_hash ^ self._turn_flip_mask
                                for cells in mutation.cell_mutations:
                                    if not cells.prev.is_empty:
                                        next_hash ^= self._zobrist_table[(cells.cell.r,cells.cell.c, cells.prev.color, cells.prev.height)]
                                    if not cells.next.is_empty:
                                        next_hash ^= self._zobrist_table[(cells.cell.r,cells.cell.c, cells.next.color, cells.next.height)]
                        
                                value[action(coord,direction)] = self.min_value(board,next_hash, a, b, board.play_phase_turn_count)
                            finally:
                                board.undo_action()
                best_move =  max(value, key=value.get)
                print("Testing: RED is playing a MOVE action")
                return best_move
            case PlayerColor.BLUE:
                coords = get_stack_coords(board, PlayerColor.BLUE)
                value = {}
                a = - math.inf
                b = math.inf
                for coord in coords:            
                    for direction in CARDINAL_DIRECTIONS:
                        for action in POSSIBLE_ACTIONS:
                            try:
                                mutation = board.apply_action(action(coord, direction))
                            except IllegalActionException:
                                continue
                            try:
                                next_hash = root_hash ^ self._turn_flip_mask
                                for cells in mutation.cell_mutations:
                                    if not cells.prev.is_empty:
                                        next_hash ^= self._zobrist_table[(cells.cell.r,cells.cell.c, cells.prev.color, cells.prev.height)]
                                    if not cells.next.is_empty:
                                        next_hash ^= self._zobrist_table[(cells.cell.r,cells.cell.c, cells.next.color, cells.next.height)]
                                value[action(coord,direction)] = self.max_value(board,next_hash, a, b, board.play_phase_turn_count)
                            finally:
                                board.undo_action()

                best_move =  min(value, key=value.get)
                print("Testing: BLUE is playing a MOVE action")
                return best_move

    def update(self, color: PlayerColor, action: Action, **referee: dict):
        """
        This method is called by the referee after a player has taken their
        turn. You should use it to update the agent's internal game state.
        """
        if color == self._color:
            self._turn_count += 1
        self._board.apply_action(action)

        # There are four possible action types: PLACE, MOVE, EAT, and CASCADE.
        # Below we check which type of action was played and print out the
        # details of the action for demonstration purposes. You should replace
        # this with your own logic to update your agent's internal game state.
        match action:
            case PlaceAction(coord):
                print(f"Testing: {color} played PLACE action at {coord}")
            case MoveAction(coord, direction):
                print(f"Testing: {color} played MOVE action:")
                print(f"  Coord: {coord}")
                print(f"  Direction: {direction}")
            case EatAction(coord, direction):
                print(f"Testing: {color} played EAT action:")
                print(f"  Coord: {coord}")
                print(f"  Direction: {direction}")
            case CascadeAction(coord, direction):
                print(f"Testing: {color} played CASCADE action:")
                print(f"  Coord: {coord}")
                print(f"  Direction: {direction}")
            case _:
                raise ValueError(f"Unknown action type: {action}")
