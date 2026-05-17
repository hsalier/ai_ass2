from referee.game import Board
from referee.game import Coord
from referee.game import PlayerColor

PROXIMITY = 2
W_BLANK = 1
W_OPP = -3
W_PLAYER = 2
W_OUT = 0


def get_stack_coords(board, PlayerColor):
    return  [coord for coord, cellstate in board._state.items() if cellstate.color == PlayerColor]


def proximity_score(board,coord):
    score = 0
    current_color = board.turn_color
    
    for r in range(coord.r-PROXIMITY,coord.r+PROXIMITY):
        for c in range(coord.c-PROXIMITY, coord.c+PROXIMITY):
            
            try:
                state = board[Coord(r,c)]
                if state.color == current_color:
                    score += W_PLAYER
                elif state.height == 0:
                    score += W_BLANK
                else:
                    score += W_OPP
                
            except (ValueError, IndexError):
                score += W_OUT
                
    return score
    
