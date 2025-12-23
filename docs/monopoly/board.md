## Board

Standard Monopoly board with 40 spaces and color groups. Provides helpers to find spaces and nearest railroads/utilities.

Example:

```python
from core.game.board import Board

board = Board()
space = board.get_space(1)
print(space.name, space.space_type)

print(board.get_color_group("brown"))  # [1, 3]
```

### Reference

::: core.game.board.Board
