# Piouhpiou  


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
