import websocket
import json
import threading
import schedule
from _datetime import *
import time
from pprint import *
from decimal import *
import logging
import requests
import tkinter as tk
from tkinter import ttk
from Spot_binance import *
from binance.error import *
from binance.lib.utils import check_required_parameters
from binance.lib.utils import config_logging
from binance.error import ClientError
from api_binance import client_spot
import globales
from bd_conect import *


class TreeviewApp:
    def __init__(self, win, cartera):
        self.root = win
        self.style = style_all(main=win)
        self.heading = ['Ticket', 'dGyP', 'Posición', 'mktPrice', 'costo_base', 'ValueMkt', 'GyP', '%ROI',
                        'GyP_proy', '%V_(Prc)(Gan)']
        self.fields = ['ticket', 'dgyp', 'position', 'mrkprice', 'costobase', 'vmarket', 'unrealizedpnl',
                       'retorno', 'GyP_proy', 'vprecio', 'vgyp']
        self.ncolumns = len(self.heading)
        self.height = 9
        self.m_tree = self.create_treeviews(self.ncolumns)
        self.inicio_dash_treeview(cartera)
        self.positions = cartera

        # ubica las columnas TreeviewApp
        for i, tree in enumerate(self.m_tree):
            # tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            tree.grid(row=0, column=i, sticky='w')

        # Vincular los eventos de selección y desplazamiento
        for tree in self.m_tree:
            tree.bind("<<TreeviewSelect>>", self.on_treeview_select)
            tree.bind("<MouseWheel>", self.on_mouse_wheel)


    def create_treeviews(self, count):
        treeviews = []
        for i in range(count):
            tree = ttk.Treeview(self.root, show="headings", height=self.height, style='TFrame')
            tree["columns"] = (self.heading[i],)
            titulo = self.heading[i].replace("_", "")
            tree.heading(self.heading[i], text=titulo)
            tree.column(self.heading[i], width=80, minwidth=80)
            tree.tag_configure("even", background="black", foreground='white')
            tree.tag_configure("even_green", foreground="White", background="dark green")
            tree.tag_configure("even_red", foreground="White", background="firebrick4")
            tree.tag_configure("odd", background="Silver", foreground='black')
            tree.tag_configure("odd_green", foreground="black", background="green2")
            tree.tag_configure("odd_red", foreground="black", background="red3")

            treeviews.append(tree)

        return treeviews

    @staticmethod
    def display_format(tipo='rows', data=None) -> list:
        if tipo == 'total':
            datos = [' ',
                     '{:>10.2f}'.format(data[1]),
                     ' ',
                     ' ',
                     '{:>10.2f}'.format(data[4]),
                     '{:>10.2f}'.format(data[5]),
                     '{:>10.2f}'.format(data[6]),
                     '{:>+11.2%}'.format(data[7]),
                     ' ',
                     ' '
                     ]
        if tipo == 'rows':
            datos = ['{:>11}'.format(data[0]),
                     '{:>10.2f}'.format(data[1]),
                     '{:>11.4f}'.format(data[2]),
                     '{:>11.4f}'.format(data[3]),
                     '{:>10.2f}'.format(data[4]),
                     '{:>10.2f}'.format(data[5]),
                     '{:>10.2f}'.format(data[6]),
                     '{:>+11.2%}'.format(data[7]),
                     '{:>10.2f}'.format(0),
                     '{:>10.2f}'.format(0)
                     ]

        return datos

    @staticmethod
    def total_positions(positions) -> list:
        dgyp, costobase, vmarket, gyp = .0, .0, .0, .0
        if positions:
            for position in positions:
                costobase += position['costobase']
                vmarket += position['vmarket']
                dgyp += position['dgyp']
                gyp += position['unrealizedpnl']
                roi = gyp / costobase

        # --------0------1----2---3-----------4--------5----6----7---8----9
        datos = [" ", dgyp, " ", " ", costobase, vmarket, gyp, roi, " ", " "]
        return datos

    def create_styles(self, i, idx, row):
        # rows (even)
        if i % 2 == 0:
            style = 'even'
            if self.heading[idx] in ('dGyP', 'GyP', '%ROI'):
                style = 'even_green' if row[idx] > 0 else 'even_red'

        # rows (odd)
        if i % 2 != 0:
            style = 'odd'
            if self.heading[idx] in ('dGyP', 'GyP', '%ROI'):
                style = 'odd_green' if row[idx] > 0 else 'odd_red'

        return style

    @staticmethod
    def struct_datos(position):
        data = list()
        data.append(position['ticket'])
        data.append(position['dgyp'])
        data.append(position['position'])
        data.append(position['mrkprice'])
        data.append(position['costobase'])
        data.append(position['vmarket'])
        data.append(position['unrealizedpnl'])
        data.append(position['retorno'])
        data.append(.0)
        data.append(.0)

        return data

    def inicio_dash_treeview(self, cartera):

         if cartera:
            #
            # totaliza cartera y mueve totales a cada columna treeview row=0
            total, i = self.total_positions(cartera), 1
            for idx, tree in enumerate(self.m_tree):
                sty = self.create_styles(0, idx, total)
                data_string = self.display_format(tipo='total', data=total)
                tree.insert(parent="", index=0, iid=0, text='', values=(data_string[idx],), tags=(sty,))
            #
            # recorre cartera y mueve detalle a cada columna treeview row > 0
            for position in cartera:
                data = self.struct_datos(position)
                for idx, tree in enumerate(self.m_tree):
                    sty = self.create_styles(i, idx, data)
                    data_string = self.display_format(tipo='rows', data=data)
                    tree.insert(parent="", index=tk.END, iid=i,  text='', values=(data_string[idx],), tags=(sty,))
                i += 1

    def update_dash_treeview(self, symbol=None, position=None):
        """
        @param symbol: simbolo a ser actualizado
        @param position: position que hay que tomar para update
        @return: actualiza columnas de tree, como son mostradas en dash portafolio
        """

        def update_items_dash(position, ticket, child, i):
            #
            # totaliza cartera y mueve totales a cada columna treeview row=0
            total = self.total_positions(self.positions)
            for idx, tree in enumerate(self.m_tree):
                sty = self.create_styles(0, idx, total)
                data_string = self.display_format(tipo='total', data=total)
                tree.item(0, values=(data_string[idx],), tags=(sty,))
            #
            # recorre position y mueve detalle a cada columna treeview row > 0
            data = self.struct_datos(position)
            for idx, tree in enumerate(self.m_tree):
                sty = self.create_styles(i, idx, data)
                data_string = self.display_format(tipo='rows', data=data)
                tree.item(child, values=(data_string[idx],), tags=(sty,))

        #
        # recorre treeview[0] para ubicar el symbol y actualizar
        i = 0
        for child in self.m_tree[0].get_children():

            item = self.m_tree[0].item(child)
            ticket = item['values'][0].strip()
            if ticket == symbol:
                update_items_dash(position, ticket, child, i)
                break
            i += 1

    def on_treeview_select(self, event):
        source_tree = event.widget
        selected_id = source_tree.selection()
        for tree in self.m_tree:
            if tree != source_tree:
                tree.selection_set(selected_id)
                tree.see(selected_id)

    def on_mouse_wheel(self, event):
        for tree in self.m_tree:
            tree.yview_scroll(int(-1 * (event.delta / 120)), "units")


class Positions(TreeviewApp):
    def __init__(self, account, vehiculo, master=None):
        self.account = account
        self.vehiculo = vehiculo
        self.win = ttk.Frame(master)
        self.dpn = ttk.Frame(master)
        self.win.grid(row=0, column=0, sticky='w', pady=40)
        self.dpn.grid(row=2, column=0, sticky='w', pady=20)
        self.positions = []
        self.dash = TreeviewApp(self.win, self.positions)

    def carga_inversion_en_positions(self) -> list:
        try:
            self.positions = []

            positions = select_inversion(tipoin=self.vehiculo)
            for position in positions:

                self.add_position(position['ticket'], position['useraccount'], position['estrategia'],
                                  position['empresa'], position['peso'], position['mrkprice'],
                                  position['costobase'], position['position'], position['unrealizedpnl'],
                                  position['dividendo'], position['objetivo'], position['deuda'],
                                  position['retorno'], position['fealta'], position['febaja'],
                                  position['iactiva'], position['tipoinv'], position['sector'])

            self.dash = TreeviewApp(self.win, self.positions)

        except EncodingWarning as error:
            print('carga_inversion() :: {}'.format(error))

    def add_position(self, ticket, useraccount, estrategia, empresa, peso, mrkprice, costobase, position,
                              unrealizedpnl, dividendo, objetivo, deuda, retorno, fealta, febaja, iactiva,
                              tipoinv, sector):
        position = {'ticket': ticket,
                    'useraccount': useraccount,
                    'estrategia': estrategia,
                    'empresa': empresa,
                    'peso': float(peso),
                    'mrkprice': float(mrkprice),
                    'costobase': float(costobase),
                    'position': float(position),
                    'unrealizedpnl': float(unrealizedpnl),
                    'dividendo': float(dividendo),
                    'objetivo': float(objetivo),
                    'deuda': float(deuda),
                    'retorno': float(retorno),
                    'fealta': fealta,
                    'febaja': febaja,
                    'iactiva': iactiva,
                    'tipoinv': tipoinv,
                    'sector': sector,
                    'dgyp': .0,
                    'vmarket': .0
                    }
        self.positions.append(position)

    def update_symbol_en_positions(self, struct):

        symbol = struct['ticket']
        for ix, position in enumerate(self.positions):
            if position['ticket'] == symbol:
                position['unrealizedpnl'] = struct['unrealizedpnl']
                position['dividendo'] = struct['dividendo']
                position['costobase'] = struct['costobase']
                position['mrkprice'] = struct['mrkprice']
                position['position'] = struct['position']
                position['vmarket'] = struct['vmarket']
                position['retorno'] = struct['retorno']
                position['deuda'] = struct['deuda']
                position['dgyp'] = struct['dgyp']

                #
                # enlaza con TreeviewApp
                self.dash.positions = self.positions
                self.dash.update_dash_treeview(symbol=symbol, position=position)

                return ix
        return -1

    def run(self):
        self.carga_inversion_en_positions()


class BinanceWebSocket:
    def __init__(self, assets, cryptos):
        self.assets = assets
        self.cryptos = cryptos
        self.url = "wss://stream.binance.com:9443/ws"
        self.ws = None
        self.lock = threading.Lock()

    def on_open(self, ws):
        print("WebSocket connection opened.")
        self.subscribe_to_cryptos()

    @staticmethod
    def on_error(self, error):
        print('BinanceWebSocket.on_error():: {}'.format(error))

    @staticmethod
    def on_close(self, ws, close_status_code):
        try:
            pass
        except EncodingWarning as error:
            print('BinanceWebSocket.on_close() :: {}'.format(error))
            time.sleep(5)

    def close(self):
        try:
            if self.ws:
                self.ws.close()
        except EncodingWarning as error:
            print('BinanceWebSocket.close() :: {}'.format(error))
            time.sleep(5)

    def on_message_binance(self, ws, message):
        try:
            data = json.loads(message)
            self.on_message(data)

        except EncodingWarning as error:
            print('BinanceWebSocket.on_message_wrapper() :: {}'.format(error))
            time.sleep(5)

    def subscribe_to_cryptos(self):
        try:
            with self.lock:
                params = [f"{crypto.lower()}@miniTicker" for crypto in self.cryptos]
                self.ws.send(json.dumps({
                    "method": "SUBSCRIBE",
                    "params": params,
                    "id": 1
                }))
        except EncodingWarning as error:
            print('BinanceWebSocket.subscribe_to_cryptos() :: {}'.format(error))
            time.sleep(5)

    def update_subscribe(self, new_cryptos):
        try:
            with self.lock:
                unsubscribe_params = [f"{crypto.lower()}@miniTicker" for crypto in self.cryptos]
                self.ws.send(json.dumps({
                    "method": "UNSUBSCRIBE",
                    "params": unsubscribe_params,
                    "id": 2
                }))
                print("Unsubscribed from cryptos:", self.cryptos)
                self.cryptos = new_cryptos
                self.subscribe_to_cryptos()

        except EncodingWarning as error:
            print('BinanceWebSocket.update_subscribe() :: {}'.format(error))
            time.sleep(5)

    def run(self):
        try:
            self.ws = websocket.WebSocketApp(
                url=self.url,
                on_open=self.on_open,
                on_message=self.on_message_binance,
                on_error=self.on_error,
                on_close=self.on_close
            )
            thread = threading.Thread(target=self.ws.run_forever)
            thread.start()

        except EncodingWarning as error:
            print('BinanceWebSocket.run() :: {}'.format(error))


class DashCrypto:
    def __init__(self, bina_client,  bina_websocket, my_positions):
        self.bina_client = bina_client
        self.bina_websocket = bina_websocket
        self.my_positions = my_positions
        self.cryptos = []
        self.assets = {}
        self.trama = []
        self.t_inicio = time.time()
        self.cn = 0
        self.ti = 30

    def fetch_api_binance(self):
        """
        @return: estructura diccionario,  con información de las siguientes wallet's
        # SPOT: account_snapshot(type='SPOT')
        # EARN: get_flexible_product_position()
        # LOANS: flexible_loan_ongoing_orders(loanCoin="USDT", collateralCoin=ticket)
        """

        try:
            assets = {}
            cryptos = []

            # obtiene activos de wallet spot
            response = self.bina_client.account_snapshot(type='SPOT', limit=1, recvWindow=5000)
            if response:
                for keys in response['snapshotVos'][0]['data']['balances']:
                    if float(keys['free']) > 0 and not keys['asset'].startswith('LD') and keys['asset'] != 'USDT':
                        symbol = keys['asset'] + 'USDT' if keys['asset'] != 'USDT' else keys['asset']
                        assets.update({symbol: {'sopt': {'borrowed': 0, 'free': keys['free'], 'locked': 0,
                                                                'netAsset': 0, 'rewards': 0}}})
            # obtiene activos de wallet earn
            response = self.bina_client.get_flexible_product_position(current=1, size=100, window=5000)
            if response:
                for keys in response['rows']:

                    if keys['asset'] != 'USDT':
                        if float(keys['collateralAmount']) != 0 or float(keys['totalAmount']) != 0:
                            free = float(keys['totalAmount'])
                            symbol = keys['asset'] + 'USDT' if keys['asset'] != 'USDT' else keys['asset']
                            if symbol in list(assets.keys()):
                                free += float(assets[keys['asset']]['spot']['free'])

                            assets.update({symbol: {'position': {'borrowed': float(keys['collateralAmount']),
                                                                 'free': free, 'locked': 0,
                                                                 'netAsset': float(keys['totalAmount']),
                                                                 'rewards': float(keys['cumulativeTotalRewards']),
                                                                 'debit USDT': .0
                                                                 }}})

                            cryptos.append(symbol)
            #
            #
            for keys in cryptos:
                coin = keys.replace("USDT", "")
                response = self.bina_client.flexible_loan_ongoing_orders(loanCoin="USDT", collateralCoin=coin,
                                                                         current=1, limit=5, recvWindow=5000)
                if response:
                    if response['total'] > 0:
                        field = response['rows'][0]
                        assets[keys]['position']['debit USDT'] = field['totalDebt']
            #
            #  deja solo los que tiene position en wallet earn
            self.assets = {}
            self.cryptos = []
            for keys, value in assets.items():

                if 'position' in value.keys():
                    self.assets.update({keys: value})
                    self.cryptos.append(keys)

            bina_websocket.cryptos = self.cryptos
            bina_websocket.assets = self.assets
            print('fetch_api_binance()',  datetime.now())

        except EncodingWarning as error:
            print('fetch_api_binance() :: {}'.format(error))
            self.ti += 0.5
            time.sleep(5)

    def websocket_message_handler(self, message):
        try:
            t_ahora = time.time()
            #
            self.cn += 1
            self.update_list_positions(message)

            if len(self.cryptos) - len(self.trama) < 3:
                    tiempo = t_ahora - self.t_inicio
                    if tiempo > self.ti:
                        self.fetch_api_binance()
                        self.t_inicio = time.time()
                    self.trama = []


        except EncodingWarning as error:
            print('websocket_message_handler() :: {}'.format(error))
            time.sleep(5)

    def update_list_positions(self, message):

        def trata_message(message):
            symbol, d_precio = None, {}
            if 'e' in list(message.keys()):
                symbol = message['s']
                last = float(message['c'])
                d_precio = {symbol: {'last': last, 'open': float(message['o'])}}
            return symbol, d_precio

        def struct_position():
            struct = dict()
            struct['unrealizedpnl'] = gyp
            struct['dividendo'] = dividendo
            struct['costobase'] = costo_base
            struct['mrkprice'] = last
            struct['position'] = stock
            struct['vmarket'] = vmarket
            struct['retorno'] = retorno
            struct['ticket'] = symbol
            struct['deuda'] = debit
            struct['dgyp'] = dgyp
            return struct

        symbol, d_precio = trata_message(message)
        if d_precio and ('position' in self.assets[symbol].keys()):

            self.cn += 1
            crypto, found = insert_crypto(symbol=symbol)

            wallet = self.assets[symbol]['position']

            debit = wallet['debit USDT']
            stock = wallet['netAsset'] + wallet['borrowed']
            last = d_precio[symbol]['last']
            market = d_precio[symbol]['last'] * stock
            costo_base = float(crypto[0]['avgcost']) * stock
            dividendo = wallet['rewards'] * last
            vmarket = last * stock
            dgyp = (last - d_precio[symbol]['open']) * stock

            gyp = vmarket - costo_base

            retorno = gyp / costo_base if costo_base > 0 else 0
            #
            # actualiza estructura positions y luego treeview para el symbol en cuestión
            struct = struct_position()

            ix = self.my_positions.update_symbol_en_positions(struct)
            print('================= cont', self.cn, ix, symbol)
            if ix > 0:
                self.trama.append(symbol)

    def run(self):
        try:

            self.fetch_api_binance()
            self.bina_websocket.run()
            self.my_positions.run()

        except EncodingWarning as error:
            print('CarteraCrypto.run() :: {}'.format(error))
            time.sleep(5)



if __name__ == "__main__":

    dw = 1295
    dh = 780
    df = 1295
    win = tk.Tk()
    dimension = "%dx%d+0+0" % (dw, dh)
    win.geometry(dimension)
    win.config(bg="black")

    style = style_app(main=win)
    itrue = threading.Event()

    dpn = ttk.Frame(win, style="TFrame", width=df, height=700)
    dpn.grid(pady=10, padx=5)

    # Crear instancias de api binance, websocket y dash_manager
    bina_client = client_spot()
    my_positions = Positions(account='B0000001', vehiculo='Crypto', master=dpn)

    websocket.enableTrace(False)
    bina_websocket = BinanceWebSocket(assets=None, cryptos=None)
    dash_manager = DashCrypto(bina_client, bina_websocket, my_positions)

    # Reemplazar el manejador de mensajes del WebSocket con el de CarteraCrypto
    bina_websocket.on_message = dash_manager.websocket_message_handler
    dash_manager.run()

    win.mainloop()


