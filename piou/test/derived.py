from piou import Cli, Option, Derived

cli = Cli(description='A CLI tool')


def get_pg_url(
        pg_user: str = Option('postgres', '--pg-user'),
        pg_pwd: str = Option('postgres', '--pg-pwd'),
        pg_host: str = Option('localhost', '--pg-host'),
        pg_port: int = Option(5432, '--pg-port'),
        pg_db: str = Option('postgres', '--pg-db')

):
    return f'postgresql://{pg_user}:{pg_pwd}@{pg_host}:{pg_port}/{pg_db}'


@cli.command(help='Run foo command')
def foo(pg_url: str = Derived(get_pg_url)):
    print(pg_url)


if __name__ == '__main__':
    cli.run()
