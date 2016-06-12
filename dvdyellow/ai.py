import sys
from random import randint

import dvdyellow.game as g


def game_found(game : g.Game):
    game.on_your_turn = my_turn
    game.on_finish = game_finished


def _check_move(pawn : g.TransformablePawn, point, board):
    x, y = point
    if len(board) < x + pawn.width:
        return False
    if len(board[0]) < y + pawn.height:
        return False

    for ix in range(pawn.width):
        for iy in range(pawn.height):
            if pawn.get_pawn_point(ix, iy):
                if board[x + ix][y + iy] != 0:
                    return False

    return True


def _print_move(pawn : g.TransformablePawn, point, new_board, nr):
    x, y = point
    for ix in range(pawn.width):
        for iy in range(pawn.height):
            if pawn.get_pawn_point(ix, iy):
                new_board[x + ix][y + iy] = nr


def _calc_points(pawn : g.TransformablePawn, point, move_board, point_board):
    """
    :param pawn: pawn used for the game
    :param move_board: game history board
    :param nr: nr which should be printed on unreachable fields
    :return:
    """
    #
    # we create new board, which starts with all fields set as possible to block
    #
    # new_board -> 1 is blocked, 0 is not blocked
    new_board = [[0 for j in range(len(move_board[0]))] for i in range(len(move_board))]
    new_board2 = [[0 for j in range(len(move_board[0]))] for i in range(len(move_board))]
    for i in range(len(move_board)):
        for j in range(len(move_board[0])):
            if move_board[i][j] != 0:
                new_board[i][j] = 1
                new_board2[i][j] = 1
    _print_move(pawn, point, new_board, 1)
    _print_move(pawn, point, new_board2, 1)
    pawn = pawn.copy()
    for k in range(4):
        pawn.rotate_clockwise()
        for i in range(len(move_board)):
            for j in range(len(move_board[0])):
                #
                # we remove fields which can be covered by a valid move from those possibly blocked
                #
                if _check_move(pawn, (i, j), new_board):
                    _print_move(pawn, (i, j), new_board2, 1)
    sum_of_points = 0
    for i in range(len(move_board)):
        for j in range(len(move_board[0])):
            #
            # sum points
            #
            if new_board2[i][j] == 0:
                sum_of_points += point_board[i][j]

    return sum_of_points


def my_turn(game):
    result_set = set() # contains (x, y, pawn, points)
    quantity = 0
    w = len(game.move_board)
    h = len(game.move_board[0])
    while quantity < 16:     # 8 - number of samples
        while True:
            x = randint(0, w - 1)
            y = randint(0, h - 1)
            r = randint(0, 3)
            p = game.get_transformable_pawn()
            for i in range(r):
                p.rotate_clockwise()
            if _check_move(p, (x, y), game.move_board):
                break
        v = _calc_points(p, (x,y), game.move_board, game.point_board)
        result_set.add((x, y, p, v))
        quantity += 1
    x, y, p, v = max(result_set, key=lambda x: x[3])
    game.move((x,y), p).result


def game_finished(game):
    pass


def accept_invite(user, func):
    func(True).result


def main():
    if len(sys.argv) != 5:
        print('Call: <host> <port> <user> <password>')
        return

    try:
        S = g.Session.create(sys.argv[1], int(sys.argv[2]), blocking=True).result
    except:
        print("Could not connect to host!")
        return

    if not S.sign_in(sys.argv[3], sys.argv[4]).result:
        print("Could not sign in.")
        return

    S.game_invitation = accept_invite
    S.on_game_found = game_found

    S.get_waiting_room().result

    try:
        while True:
            S.process_events()
    except KeyboardInterrupt:
        S.del_waiting_room().result
        S.sign_out().result
        return

if __name__ == '__main__':
    main()