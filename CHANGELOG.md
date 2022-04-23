# Changelog

## [0.9.6] 23-04-2022


### NEW

- You can now chain the `Derived` options. 
  For instance:
    ```python
    from piou import Cli, Option, Derived

    cli = Cli(description='A CLI tool')

    def processor_1(a: int = Option(1, '-a'),
                    b: int = Option(2, '-b')):
        return a + b

    def processor_2(c: int = Derived(processor_1)):
        return c + 2

    def processor_3(d: int = Derived(processor_2)):
        return d * 2

    @cli.command()
    def test(value: int = Derived(processor_3)):
        nonlocal called
        assert value == 10
    ```
