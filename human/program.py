from referee.game import PlayerColor, Coord, Direction, \
    Action, PlaceAction, MoveAction, EatAction, CascadeAction, BOARD_N
import tkinter as tk

DIR_MAP = {'U': Direction.Up, 'D': Direction.Down, 'L': Direction.Left, 'R': Direction.Right}

CELL_SIZE = 56
COLORS = {
    'RED':      {'bg': '#C0392B', 'fg': 'white'},
    'BLUE':     {'bg': '#2471A3', 'fg': 'white'},
    'empty_a':  {'bg': '#ECF0F1', 'fg': '#888'},
    'empty_b':  {'bg': '#D5D8DC', 'fg': '#888'},
}

class BoardDialog(tk.Toplevel):
    def __init__(self, parent, board, color, placement_phase):
        super().__init__(parent)
        self.result = None
        self.title(f"Your turn — {color}")
        self.resizable(False, False)
        self.grab_set()

        # ── Board grid ──────────────────────────────────────────
        gf = tk.Frame(self, bg='#2C3E50', padx=2, pady=2)
        gf.pack(padx=12, pady=(12, 6))

        # Column headers
        tk.Label(gf, text='', width=2, bg='#2C3E50').grid(row=0, column=0)
        for c in range(BOARD_N):
            tk.Label(gf, text=str(c), width=4, bg='#2C3E50', fg='#AAB7B8',
                     font=('Courier', 10)).grid(row=0, column=c+1)

        for r in range(BOARD_N):
            tk.Label(gf, text=str(r), bg='#2C3E50', fg='#AAB7B8',
                     font=('Courier', 10), width=2).grid(row=r+1, column=0)
            for c in range(BOARD_N):
                stack = board[Coord(r, c)]
                if stack is None:
                    style = COLORS['empty_a'] if (r+c)%2==0 else COLORS['empty_b']
                    text = ''
                else:
                    pc, height = stack
                    style = COLORS['RED'] if pc==PlayerColor.RED else COLORS['BLUE']
                    text = f"{'R' if pc==PlayerColor.RED else 'B'}{height}"

                tk.Label(
                    gf, text=text, width=4, height=2,
                    bg=style['bg'], fg=style['fg'],
                    font=('Courier', 13, 'bold'),
                    relief='flat'
                ).grid(row=r+1, column=c+1, padx=1, pady=1)

        # ── Hint ────────────────────────────────────────────────
        if placement_phase:
            hint = "PLACE r c          e.g.  PLACE 3 4"
        else:
            hint = "MOVE/EAT/CASCADE r c U/D/L/R          e.g.  MOVE 3 4 U"

        tk.Label(self, text=hint, font=('Courier', 10), fg='#555',
                 bg=self['bg']).pack(pady=(0, 4))

        # ── Input row ───────────────────────────────────────────
        ef = tk.Frame(self)
        ef.pack(padx=12, pady=(0, 12), fill='x')

        self._entry = tk.Entry(ef, font=('Courier', 13), width=28)
        self._entry.pack(side='left', padx=(0, 6))
        self._entry.focus_set()
        self._entry.bind('<Return>', lambda e: self._submit())

        self._err = tk.Label(ef, text='', fg='red', font=('Courier', 10))
        self._err.pack(side='left')

        tk.Button(ef, text='OK', command=self._submit,
                  font=('Courier', 11), width=5).pack(side='right')

    def _submit(self):
        raw = self._entry.get().strip().upper().split()
        try:
            match raw[0]:
                case 'PLACE':
                    self.result = PlaceAction(Coord(int(raw[1]), int(raw[2])))
                case 'MOVE':
                    self.result = MoveAction(Coord(int(raw[1]), int(raw[2])), DIR_MAP[raw[3]])
                case 'EAT':
                    self.result = EatAction(Coord(int(raw[1]), int(raw[2])), DIR_MAP[raw[3]])
                case 'CASCADE':
                    self.result = CascadeAction(Coord(int(raw[1]), int(raw[2])), DIR_MAP[raw[3]])
                case _:
                    raise ValueError("unknown action")
            self.destroy()
        except Exception as e:
            self._err.config(text=f'  bad input: {e}')
            self._entry.select_range(0, 'end')


class Agent:

    def __init__(self, color: PlayerColor, **referee: dict):
        self._color = color
        self._board = {Coord(r, c): None for r in range(BOARD_N) for c in range(BOARD_N)}
        self._placements_made = {PlayerColor.RED: 0, PlayerColor.BLUE: 0}
        self._root = tk.Tk()
        self._root.withdraw()

    def action(self, **referee: dict) -> Action:
        placement_phase = self._placements_made[self._color] < 4
        while True:
            dlg = BoardDialog(self._root, self._board, self._color, placement_phase)
            self._root.wait_window(dlg)
            if dlg.result is not None:
                return dlg.result

    def update(self, color: PlayerColor, action: Action, **referee: dict):
        match action:
            case PlaceAction(coord):
                self._board[coord] = (color, 3)
                self._placements_made[color] += 1
            case MoveAction(coord, direction):
                src = self._board[coord]
                self._board[coord] = None
                dest = coord + direction
                self._board[dest] = src if self._board[dest] is None \
                    else (src[0], src[1] + self._board[dest][1])
            case EatAction(coord, direction):
                src = self._board[coord]
                self._board[coord] = None
                self._board[coord + direction] = src
            case CascadeAction(coord, direction):
                src = self._board[coord]
                self._board[coord] = None
                for i in range(1, src[1] + 1):
                    pos_r = coord.r + direction.r * i   # ← compute raw first
                    pos_c = coord.c + direction.c * i
                    if not (0 <= pos_r < BOARD_N and 0 <= pos_c < BOARD_N):
                        break
                    pos = Coord(pos_r, pos_c)           # ← then construct
                    if self._board[pos] is not None:
                        self._push(pos, direction)
                    self._board[pos] = (src[0], 1)

    def _push(self, coord: Coord, direction: Direction):
        dest_r = coord.r + direction.r
        dest_c = coord.c + direction.c
        if not (0 <= dest_r < BOARD_N and 0 <= dest_c < BOARD_N):  # ← check first
            self._board[coord] = None
            return
        dest = Coord(dest_r, dest_c)                                # ← then construct
        if self._board[dest] is not None:
            self._push(dest, direction)
        self._board[dest] = self._board[coord]
        self._board[coord] = None