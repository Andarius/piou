# Changelog

## [0.1.12] 27-12-2021

### NEW:

 - you can now use `Literal` for string validation.

```python
from typing import Literal


@cli.command(cmd='foo',
             help='Run foo command')
def foo_main(
        bar: Literal['foo', 'bar'] = Option(None, '--foo', help='Literal argument'),
):
    ...
```

### FIXED:

 - `list` type was not correctly parsed
