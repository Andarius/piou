# Changelog

## [0.1.13] 29-12-2021

### NEW:

 - you can now write async function commands.

```python
@cli.command(cmd='bar', help='Run bar command')
async def bar_main():
    ...
```
