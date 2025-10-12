from tinkoff.invest import Client, InstrumentIdType


def get_portfolio_assets(token):
    with Client(token) as client:
        accounts = client.users.get_accounts()

        if not accounts.accounts:
            return []

        account_id = accounts.accounts[0].id
        portfolio = client.operations.get_portfolio(account_id=account_id)

        result = []
        for position in portfolio.positions:
            figi = position.figi
            quantity = position.quantity.units

            instrument = client.instruments.get_instrument_by(
                id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_FIGI,
                id=figi
            ).instrument
            result.append({
                "ticker": instrument.ticker,
                "name": instrument.name,
                "quantity": quantity
            })

        return result

print(get_portfolio_assets('t.Wwc9-ETWh-SiWqphi_F3TQ-U7TZNsuhUryWHiDWu1vqvq19ypX7I9il3E9PlfZgKyt4gPiHrXD4RjyNiVUHzzA'))
