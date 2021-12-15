# Piou  


[![CircleCI](https://circleci.com/gh/Andarius/piou/tree/master.svg?style=shield)](https://app.circleci.com/pipelines/github/Andarius/piou?branch=master)
[![Latest PyPI version](https://img.shields.io/pypi/v/piou?logo=pypi)](https://pypi.python.org/pypi/piou)
[![Latest conda-forge version](https://img.shields.io/conda/vn/conda-forge/piou?logo=conda-forge)](https://anaconda.org/conda-forge/piou)  

A CLI tool to build beautiful command-line interfaces with type validation.

It is as simple as

```python
from piou import Parser, CmdArg

parser = Parser(description='A CLI tool')

parser.add_argument('-h', '--help', help='Display this help message')
parser.add_argument('-q', '--quiet', help='Do not output any message')
parser.add_argument('--verbose', help='Increase verbosity')


@parser.command(cmd='foo',
                help='Run foo command')
def foo_main(
    foo1: int = CmdArg(..., help='Foo arguments'),
    foo2: str = CmdArg('-f', '--foo2', help='Foo arguments')
):
    print('Ran foo main with ', foo1)
    print('foo2: ', foo2)


@parser.command(cmd='bar', help='Run bar command')
def bar_main():
    pass


if __name__ == '__main__':
    parser.print_help()
    parser.run()
```
The output will look like this: 

![example](https://github.com/Andarius/piou/blob/master/docs/example.png?raw=true)
