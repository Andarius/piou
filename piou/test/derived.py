import asyncio
import os
from typing import Literal
from piou import Cli, Option, Derived

try:
    import asyncpg
except ImportError as e:
    asyncpg = None

cli = Cli(description='A CLI tool')


def get_pg_url(
        pg_user: str = Option('postgres', '--user'),
        pg_pwd: str = Option('postgres', '--pwd'),
        pg_host: str = Option('localhost', '--host'),
        pg_port: int = Option(5432, '--port'),
        pg_db: str = Option('postgres', '--db')

) -> str:
    return f'postgresql://{pg_user}:{pg_pwd}@{pg_host}:{pg_port}/{pg_db}'


if asyncpg is not None:
    async def get_pg_conn(
            pg_url: str = Derived(get_pg_url)
    ) -> asyncpg.Connection:
        return await asyncpg.connect(pg_url)

    @cli.command(help='Run bar command')
    async def bar(
            pg_conn=Derived(get_pg_conn),
            query: str = Option('SELECT 1 FROM pg_namespace', '-q', help='Query to execute')
    ):
        res = await pg_conn.fetchval(query)
        print(res)


async def get_sleep(
        duration: float = Option(0.01, '--duration'),
) -> bool:
    await asyncio.sleep(duration)
    return True


@cli.command(help='Run foo command')
def foo(
        pg_url: str = Derived(get_pg_url),
        has_slept: bool = Derived(get_sleep)
):
    print(has_slept, pg_url)




def get_pg_url_dynamic(source: Literal['db1', 'db2']):
    _source_upper = source.upper()
    _host_arg = f'--host-{source}'
    _db_arg = f'--{source}'

    def _derived(
            pg_host: str = Option(os.getenv(f'PG_HOST_{_source_upper}', 'localhost'),
                                  _host_arg, arg_name=_host_arg),
            pg_db: str = Option(os.getenv(f'PG_DB_{_source_upper}', source),
                                _db_arg, arg_name=_db_arg),
    ):
        return f'postgresql://postgres:postgres@{pg_host}:5432/{pg_db}'

    return _derived


@cli.command(help='Run dynamic command')
def dynamic(url_1: str = Derived(get_pg_url_dynamic('db1')),
            url_2: str = Derived(get_pg_url_dynamic('db2'))):
    print(url_1, url_2)


if __name__ == '__main__':
    cli.run()
