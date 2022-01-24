import asyncio

from piou import Cli, Option, Derived

cli = Cli(description='A CLI tool')


def get_pg_url(
        pg_user: str = Option('postgres', '--user'),
        pg_pwd: str = Option('postgres', '--pwd'),
        pg_host: str = Option('localhost', '--host'),
        pg_port: int = Option(5432, '--port'),
        pg_db: str = Option('postgres', '--db')

):
    return f'postgresql://{pg_user}:{pg_pwd}@{pg_host}:{pg_port}/{pg_db}'


async def get_sleep(
        duration: float = Option(0.01, '--duration'),
):
    await asyncio.sleep(duration)
    return True


@cli.command(help='Run foo command')
def foo(
        pg_url: str = Derived(get_pg_url),
        has_slept: bool = Derived(get_sleep)
):
    print(has_slept, pg_url)


if __name__ == '__main__':
    cli.run()
