# Piou  


[![CircleCI](https://circleci.com/gh/Andarius/piou/tree/master.svg?style=shield)](https://app.circleci.com/pipelines/github/Andarius/piou?branch=master)
[![Latest PyPI version](https://img.shields.io/pypi/v/piou?logo=pypi)](https://pypi.python.org/pypi/piou)
[![Latest conda-forge version](https://img.shields.io/conda/vn/conda-forge/piou?logo=conda-forge)](https://anaconda.org/conda-forge/piou)  

A CLI tool to build beautiful command-line interfaces with type validation.

It is as simple as

```python
from piou import Cli, Option

cli = Cli(description='A CLI tool')


@cli.command(cmd='foo',
             help='Run foo command')
def foo_main(
        foo1: int = Option(..., help='Foo arguments'),
        foo2: str = Option(..., '-f', '--foo2', help='Foo2 arguments'),
        foo3: str = Option(None, '-g', '--foo3', help='Foo3 arguments'),
):
    pass

if __name__ == '__main__':
    cli.run()
```
The output will look like this: 

![example](https://github.com/Andarius/piou/blob/master/docs/example.png?raw=true)
