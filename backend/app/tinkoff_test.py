from tinkoff_service import get_full_portfolio

data = get_full_portfolio('t.b7cVknEoyjXW6FG39o4woo12yzoCAKsTwYgT0LqYFvNEH0hC5IGSMtLxVEwGfwXOv048FR5kGmxMeFpEM-GCRQ')

for i in data['positions']:
    print(i)