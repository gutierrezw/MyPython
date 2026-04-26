1#!/usr/bin/env python
import PySimpleGUI as sg
import operator


from pprint import pprint
from ibw.dashBoard import *

# Create a new session of the IB Web API.
ib_client = Dashboard(
    username="guti2004",
    account="U4214563",
    is_server_running=True
)

ib_dashBoard = Cartera(
    conid=0,        ticket=" ",
    position=0.00,  avgCost=0.00,
    mktPrice=0.00,  costobase=0.00,
    mktValue=0.00,  retStock=0.00,
    GyP=0.00
)


# create a new session
account_data = ib_client.portfolio_accounts()
print(account_data)
pprint(" ")

positions = ib_client.cartera_dashboard(account_id=ib_client.account, page_id=0)
pprint(positions[1])
i = 0
costo: float = 0.00
stock: float = 0.00
costoStock = 0.00
num_cols = 9
num_rows = len(positions)
tablaDatos = [[j for j in range(num_cols)] for i in range(num_rows)]
headings = ['conid',
            'Ticket',
            'position',
            'mktPrice',
            'avgCost',
            'costoStock',
            'mktValue',
            'retStock',
            'GyP'
                 ]
visible=[0, 1, 1, 1, 1, 1, 1, 1, 1]

for conid in positions:

    costoStock = positions[i]['position'] * positions[i]['avgCost']
    retStock = (positions[i]['mktValue'] - costoStock) / costoStock
    GyP = positions[i]['position'] * positions[i]['mktPrice'] - costoStock

    tablaDatos[i] = ['{: 10d}'.format(positions[i]['conid']),
                     '{: >10}'.format(positions[i]['contractDesc']),
                     '{:-.4f}'.format(positions[i]['position']),
                     '{:-.3f}'.format(positions[i]['mktPrice']),
                     '{:-.3f}'.format(positions[i]['avgCost']),
                     '{:-.3f}'.format(costoStock),
                     '{:-.3f}'.format(positions[i]['mktValue']),
                     '{:-.2%}'.format(retStock),
                     '{:-.3f}'.format(GyP)
                    ]
    costo = costo + costoStock
    i += 1



sg.theme('DarkGrey')


def sort_table(table, cols):
    """ sort a table by multiple columns
        table: a list of lists (or tuple of tuples) where each inner list
               represents a row
        cols:  a list (or tuple) specifying the column numbers to sort by
               e.g. (1,0) would sort by column 1, then by column 0
    """
    for col in reversed(cols):
        try:
            table = sorted(table, key=operator.itemgetter(col))
        except Exception as e:
            sg.popup_error('Error in sort_table', 'Exception in sort_table', e)
    return table

# ------ Window Layout ------
layout = [[sg.Table(values=tablaDatos[0:][:], headings=headings, max_col_width=10,
                    visible_column_map=visible,
                    auto_size_columns=False,
                    display_row_numbers=False,
                    justification='right',
                    num_rows=25,
                    alternating_row_color='grey',
                    key='-TABLE-',
                    selected_row_colors='black on while',
                    enable_events=True,
                    expand_x=True,
                    expand_y=True,
                    enable_click_events=True,           # Comment out to not enable header and other clicks
                    tooltip='detalle ticket' )],
          [sg.Button('OK'), sg.Button('Cancel')],
          ]

# ------ Create Window ------
sort_table(tablaDatos, (6,1))
window = sg.Window('Dash Board', layout,
                   default_element_size=(45,1),
                   ttk_theme='alt',
                   resizable=True)

# ------ Event Loop ------
while True:
    event, values = window.read()
    print(event, values)
    if event == sg.WIN_CLOSED:
        break
    if event == 'Double':
        for i in range(1, len(tablaDatos)):
            tablaDatos.append(tablaDatos[i])
        window['-TABLE-'].update(values=tablaDatos[1:][:])
    elif event == 'Change Colors':
        window['-TABLE-'].update(row_colors=((8, 'white', 'red'), (9, 'green')))
    if isinstance(event, tuple):
        # TABLE CLICKED Event has value in format ('-TABLE=', '+CLICKED+', (row,col))
        if event[0] == '-TABLE-':
            if event[2][0] == -1 and event[2][1] != -1:           # Header was clicked and wasn't the "row" column
                col_num_clicked = event[2][1]
                new_table = sort_table(tablaDatos[1:][:],(col_num_clicked, 0))
                window['-TABLE-'].update(new_table)
                tablaDatos = [tablaDatos[0]] + new_table
            window['-CLICKED-'].update(f'{event[2][0]},{event[2][1]}')
window.close()