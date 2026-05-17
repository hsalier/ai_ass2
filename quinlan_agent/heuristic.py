from referee.game import PlayerColor
from .helper import get_stack_coords
import math
# Weights of our heuristic function
W_TOKENS = 8
W_MIN_DISTANCE = 9
W_DISTANCE_FROM_EDGE = 3
W_SMALLEST_RECTANGLE = 2
W_STACK_HEIGHT = [0,1,2,3,4,5,3,2.5,0.5,0.5,0.5,0.25,0.1]


def h_play(board):
    
    red_coords = get_stack_coords(board, PlayerColor.RED)
    if not red_coords:
        return - math.inf
    blue_coords = get_stack_coords(board, PlayerColor.BLUE)
    if not blue_coords:
        return math.inf
    
    # First heuristic element
    
    # Finding the difference between the number of stacks
    num_blue_stacks = board._count_stacks(PlayerColor.BLUE)
    num_red_stacks = board._count_stacks(PlayerColor.RED)
    stack_diff = num_red_stacks - num_blue_stacks
    
    # Second heuristic element
    
    # Finding the smallest rectangle that covers all red stacks
    red_r = [r for r, c in red_coords]
    red_c = [c for r, c in red_coords]

    red_area = (max(red_r) - min(red_r)) * (max(red_c)-min(red_c))

    # Finding the smallest rectangle that covers all blue stacks
    blue_r = [r for r, c in blue_coords]
    blue_c = [c for r, c in blue_coords]

    blue_area = (max(blue_r) - min(blue_r)) * (max(blue_c)-min(blue_c))

    # `area_diff` formatted as blue's area minus red's since a smaller area is better
    area_diff = blue_area - red_area

    
    # Third heuristic element
    
    # Finding minimum distance between any red and blue stack
    min_distance = math.inf
    for red_coord in red_coords:
        for blue_coord in blue_coords:
            manhattan_distance = abs(red_coord.r - blue_coord.r) + abs(red_coord.c - blue_coord.c)
            if manhattan_distance < min_distance:
                min_distance = manhattan_distance
    
    # Fourth heuristic element
    
    # Finding the minimum distance between any red stack and the edge
    min_dis_to_edge_r = []
    for coords in red_coords:
        r,c = coords
        dist_to_edge = [r,c,7-c,7-r]
        min_dis_to_edge_r.append(min(dist_to_edge))
    avg_dis_edge_r = sum(min_dis_to_edge_r)/len(min_dis_to_edge_r)
    
    #Finding the minimum distance between any blue stack and the edge
    min_dis_to_edge_b = []
    for coords in blue_coords:
        r,c = coords
        dist_to_edge = [r,c,7-c,7-r]
        min_dis_to_edge_b.append(min(dist_to_edge))
    avg_dis_edge_b = sum(min_dis_to_edge_b)/len(min_dis_to_edge_b)
    
    diff_dis_to_edge = avg_dis_edge_r - avg_dis_edge_b
    
    # Fifth heuristic element
    # Finding the difference between the number of red and blue stacks
    blue_num = board.blue_tokens
    red_num = board.red_tokens
    token_diff = red_num - blue_num
    
    # Sixth heuristic element
    
    # Finding stack heights
    tallest_red_height = 0
    for stack in red_coords:
        if board[stack].height > tallest_red_height:
            tallest_red_height = board[stack].height
            
    tallest_blue_height = 0
    for stack in blue_coords:
        if board[stack].height > tallest_blue_height:
            tallest_blue_height = board[stack].height

    
        
    # Calculating heuristic value
    eval = W_TOKENS*token_diff + W_MIN_DISTANCE*min_distance + W_DISTANCE_FROM_EDGE*diff_dis_to_edge + W_SMALLEST_RECTANGLE*area_diff + W_STACK_HEIGHT[tallest_red_height] - W_STACK_HEIGHT[tallest_blue_height]
    
    return eval
