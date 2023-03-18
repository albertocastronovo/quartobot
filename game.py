from enum import Enum
from math import prod
from uuid import uuid4
from copy import deepcopy

pieces_matrix = {
            0: {
                0: "LRTF", 1: "LRTH", 2: "LRSF", 3: "LRSH"
            },
            1: {
                0: "LQTF", 1: "LQTH", 2: "LQSF", 3: "LQSH"
            },
            2: {
                0: "DRTF", 1: "DRTH", 2: "DRSF", 3: "DRSH"
            },
            3: {
                0: "DQTF", 1: "DQTH", 2: "DQSF", 3: "DQSH"
            }
        }


class Piece:
    def __init__(self, piece_code: str = "LRTS"):
        try:
            self.__label = piece_code
            self.__code: int = int(PieceVal[piece_code])
        except KeyError:
            self.__label = "NULL"
            self.__code: int = 0

    @property
    def code(self):
        return self.__code

    @property
    def label(self):
        return self.__label


class Board:
    def __init__(self):
        self.__board_dim = 4
        self.__board = [
            [
                0 for _ in range(self.__board_dim)
            ] for _ in range(self.__board_dim)
        ]

    @property
    def board_dim(self):
        return self.__board_dim

    @property
    def board(self):
        return self.__board

    def set_board_dim(self, new_dim: int):
        self.__board_dim = new_dim

    def set_board(self, new_board: list[list[int]]):
        self.__board = deepcopy(new_board)

    def place_piece(self, new_piece: Piece, pos_x: int, pos_y: int):
        if not (0 <= pos_x < self.__board_dim and 0 <= pos_y < self.__board_dim):
            raise Exception("Input arguments out of range")
        self.__board[pos_x][pos_y] = new_piece.code

    def is_cell_free(self, pos_x: int, pos_y: int):
        return self.__board[pos_x][pos_y] == 0

    def is_board_full(self):
        return not any(0 in sublist for sublist in self.__board)

    def check_victory(self, pos_x: int, pos_y: int) -> (int, int):
        if not (0 <= pos_x < self.__board_dim and 0 <= pos_y < self.__board_dim):
            raise Exception("Input arguments out of range")
        # row check: multiply together all values in the row at x position
        row_prod = prod(self.__board[pos_x])
        row_win = self.is_winning_score(row_prod)
        if row_win > 0:
            return 1, row_win   # 1 means victory by row, row_win is the win code

        # col check: multiply together all values in the col at y position
        col_list = [x[pos_y] for x in self.__board]
        col_prod = prod(col_list)
        col_win = self.is_winning_score(col_prod)
        if col_win > 0:
            return 2, col_win   # 2 means victory by col, col_win is the win code

        # diag check: if the position is on a main diagonal, multiply together all values in that diagonal
        if pos_x == pos_y:  # diagonal from top left to bottom right
            diag_list = [self.__board[i][i] for i in range(self.__board_dim)]
            diag_prod = prod(diag_list)
            diag_win = self.is_winning_score(diag_prod)
            if diag_win > 0:
                return 3, diag_win  # 3 means victory by first diag, diag_win is the win code

        elif (pos_x + pos_y) == self.__board_dim - 1:   # diagonal from bottom left to top right
            diag_list = [self.__board[i][self.__board_dim - 1 - i] for i in range(self.__board_dim)]
            diag_prod = prod(diag_list)
            diag_win = self.is_winning_score(diag_prod)
            if diag_win > 0:
                return 4, diag_win  # 4 means victory by second diag, diag_win is the winning code

        return 0, 0

    @staticmethod
    def is_winning_score(score: int):
        if score == 0:
            return 0
        if (score / float(PieceVal.L4)) % 1 == 0:   # victory with light pieces
            return 1
        if (score / float(PieceVal.D4)) % 1 == 0:   # victory with dark pieces
            return 2
        if (score / float(PieceVal.R4)) % 1 == 0:   # victory with round pieces
            return 3
        if (score / float(PieceVal.Q4)) % 1 == 0:   # victory with square pieces
            return 4
        if (score / float(PieceVal.T4)) % 1 == 0:   # victory with tall pieces
            return 5
        if (score / float(PieceVal.S4)) % 1 == 0:   # victory with short pieces
            return 6
        if (score / float(PieceVal.F4)) % 1 == 0:   # victory with full pieces
            return 7
        if (score / float(PieceVal.H4)) % 1 == 0:   # victory with hollow pieces
            return 8
        return 0

    def display(self):
        message = "| ---- | ---- | ---- | ---- |\n"
        for line_list in self.__board:
            parsed_list = [PieceVal(x).name for x in line_list]
            message += "| " + " | ".join(parsed_list) + " |\n"
        message += "| ---- | ---- | ---- | ---- |\n"
        return message

    def to_string(self):
        matrix_string = ""
        for line in self.__board:
            matrix_string += "_" + "_".join([str(x) for x in line])

        output_string = f"BRD__{self.__board_dim}_{matrix_string}"
        return output_string

    @staticmethod
    def from_string(board_string: str):
        board_params = board_string.split("__")
        board_dim = int(board_params[1])
        board_list = board_params[2].split("_")
        board_list = [int(x) for x in board_list]
        board = [board_list[x*board_dim: x*board_dim + board_dim] for x in range(board_dim)]
        new_board = Board()
        new_board.set_board(board)
        new_board.set_board_dim(board_dim)
        return new_board


class Game:
    def __init__(self, player_1, player_2):
        self.__board = Board()
        self.__id = str(uuid4())
        self.__p1 = player_1
        self.__p2 = player_2
        self.__turn: int = 1    # 1 for player 1, 2 for player 2
        self.__stage: int = 1   # 1 for selection, 2 for placement
        self.__state: int = 0   # 0 = in progress, 1 = player 1 won, 2 = player 2 won, 3 = draw
        self.__win_cond: int = 0    # 1 row, 2 col, 3 d1, 4 d2
        self.__last_xy: tuple = (0, 0)
        self.__last_selected_piece: Piece = Piece("NULL")
        self.__last_message = "default"
        self.__pieces = {
            "LRTF": Piece("LRTF"),
            "LRTH": Piece("LRTH"),
            "LRSF": Piece("LRSF"),
            "LRSH": Piece("LRSH"),
            "LQTF": Piece("LQTF"),
            "LQTH": Piece("LQTH"),
            "LQSF": Piece("LQSF"),
            "LQSH": Piece("LQSH"),
            "DRTF": Piece("DRTF"),
            "DRTH": Piece("DRTH"),
            "DRSF": Piece("DRSF"),
            "DRSH": Piece("DRSH"),
            "DQTF": Piece("DQTF"),
            "DQTH": Piece("DQTH"),
            "DQSF": Piece("DQSF"),
            "DQSH": Piece("DQSH")
        }
        self.__pieces_matrix = deepcopy(pieces_matrix)

    @property
    def board(self):
        return self.__board

    @property
    def id(self):
        return self.__id

    @property
    def turn(self):
        return self.__turn

    @property
    def stage(self):
        return self.__stage

    @property
    def pieces(self):
        return self.__pieces

    @property
    def pieces_matrix(self):
        return self.__pieces_matrix

    @property
    def state(self):
        return self.__state

    @property
    def last_xy(self):
        return self.__last_xy

    @property
    def win_cond(self):
        return self.__win_cond

    @property
    def last_message(self):
        return self.__last_message

    @property
    def last_selected_piece(self):
        return self.__last_selected_piece

    def set_pieces(self, new_pieces: dict[str, Piece]):
        self.__pieces = dict(new_pieces)

    def set_last_xy(self, new_xy: tuple[int, int]):
        self.__last_xy = new_xy

    def set_win_cond(self, new_win_cond: int):
        self.__win_cond = new_win_cond

    def set_state(self, new_state: int):
        self.__state = new_state

    def set_stage(self, new_stage: int):
        self.__stage = new_stage

    def set_turn(self, new_turn: int):
        self.__turn = new_turn

    def set_board(self, new_board: Board):
        self.__board = new_board

    def set_id(self, new_id: str):
        self.__id = new_id

    def set_selected_piece(self, new_label):
        self.__last_selected_piece = Piece(new_label)

    def set_last_message(self, new_message):
        self.__last_message = str(new_message.id)

    def set_last_message_id(self, new_message_id: str):
        self.__last_message = new_message_id

    def next_turn(self):
        self.__turn = 3 - self.__turn

    def change_stage(self):
        self.__stage = 3 - self.__stage

    def is_board_full(self):
        return self.__board.is_board_full()

    def place_stage(self, pos_x: int, pos_y: int) -> (int, int):
        if not (0 <= pos_x < self.__board.board_dim and 0 <= pos_y < self.__board.board_dim):
            raise Exception("Input arguments out of range")
        if self.__board.is_cell_free(pos_x, pos_y):
            self.__board.place_piece(self.__last_selected_piece, pos_x, pos_y)
            victory_by, victory_code = self.__board.check_victory(pos_x, pos_y)
            self.__last_xy = (pos_x, pos_y)
            if victory_by > 0:
                self.__state = self.__turn  # if the placement resulted in a win, the player who placed it wins
                self.__win_cond = victory_by
            return victory_by, victory_code
        else:
            return -1, -1

    def select_stage(self, piece_label: str = "NULL"):
        if not self.__pieces:               # if there are no more pieces available to place
            self.__state = 3                # the game results in a draw
            return 2

        if piece_label in self.__pieces:    # if the piece is still available
            self.__last_selected_piece = self.__pieces[piece_label]
            del self.__pieces[piece_label]
        else:
            return 0                        # if the piece was already placed, or does not exist
        return 1

    def to_string(self):
        output_string = self.__board.to_string()
        output_string += f"_ENDBRD_{self.__turn}_{self.__stage}_{self.__state}_{self.__win_cond}"
        output_string += f"_{self.__last_xy[0]}_{self.__last_xy[1]}"
        output_string += f"_{self.__last_selected_piece.label}_{self.__last_message}"
        output_string += f"_{self.__id}_"
        output_string += "_".join(list(self.__pieces.keys()))
        return output_string

    @staticmethod
    def from_string(game_string: str, player_1: int, player_2: int):
        board_sep = game_string.split("_ENDBRD_")     # separate board string from the rest
        new_game = Game(player_1, player_2)
        new_game.set_board(Board.from_string(board_sep[0]))
        game_params = board_sep[1].split("_")
        new_game.set_turn(int(game_params[0]))
        new_game.set_stage(int(game_params[1]))
        new_game.set_state(int(game_params[2]))
        new_game.set_win_cond(int(game_params[3]))
        new_game.set_last_xy((int(game_params[4]), int(game_params[5])))
        new_game.set_selected_piece(game_params[6])
        new_game.set_last_message_id(game_params[7])
        new_game.set_id(game_params[8])
        piece_labels = game_params[9:]
        new_game_pieces = {
            x: Piece(x) for x in piece_labels
        }
        new_game.set_pieces(new_game_pieces)

        return new_game

    def __repr__(self):
        return f"Game object: {self.__p1} vs {self.__p2}"


class VictoryPieceType(Enum):
    LIGHT = 1
    DARK = 2
    ROUND = 3
    SQUARE = 4
    TALL = 5
    SHORT = 6
    FULL = 7
    HOLLOW = 8


class PieceVal(Enum):
    def __mul__(self, other):
        if isinstance(other, PieceVal):
            return self.value * other.value
        elif isinstance(other, int):
            return self.value * other
        else:
            raise TypeError(f"Unsupported types for multiplication: PieceVal and {type(other)}")

    def __rmul__(self, other):
        return self.__mul__(other)

    def __pow__(self, other):
        if isinstance(other, int):
            return self.value ** other
        else:
            raise TypeError(f"Power of PieceVal is only supported with type int as exponent")

    def __float__(self):
        return float(self.value)

    def __int__(self):
        return int(self.value)

    L = 2
    D = 3
    R = 5
    Q = 7
    T = 11
    S = 13
    F = 17
    H = 19

    L4 = L**4
    D4 = D**4
    R4 = R**4
    Q4 = Q**4
    T4 = T**4
    S4 = S**4
    F4 = F**4
    H4 = H**4

    NULL = 0
    LRTF = L*R*T*F
    LRTH = L*R*T*H
    LRSF = L*R*S*F
    LRSH = L*R*S*H
    LQTF = L*Q*T*F
    LQTH = L*Q*T*H
    LQSF = L*Q*S*F
    LQSH = L*Q*S*H
    DRTF = D*R*T*F
    DRTH = D*R*T*H
    DRSF = D*R*S*F
    DRSH = D*R*S*H
    DQTF = D*Q*T*F
    DQTH = D*Q*T*H
    DQSF = D*Q*S*F
    DQSH = D*Q*S*H


class PieceEmoji(Enum):
    NULL = 1085958929051287639
    DQSF = 1085956958777000046
    DQSH = 1085956982126686309
    DQTF = 1085957005463797821
    DQTH = 1085957006780813373
    DRSF = 1085957008710185071
    DRSH = 1085957010509549668
    DRTF = 1085957012581527624
    DRTH = 1085957014146003024
    LQSF = 1085957015391707307
    LQSH = 1085957017505632296
    LQTF = 1085957018730381352
    LQTH = 1085957024141033683
    LRSF = 1085957027173502976
    LRSH = 1085957028318552176
    LRTF = 1085957030566699131
    LRTH = 1085957154722287636
