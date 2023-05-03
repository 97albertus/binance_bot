#!/usr/bin/env python
import logging
import asyncio
from binance.client import Client
from binance.um_futures import UMFutures
from binance.lib.utils import config_logging
from binance.error import ClientError
from binance.websocket.um_futures.websocket_client import UMFuturesWebsocketClient
import tracemalloc
import configparser
import os
import threading
import tkinter as tk
from tkinter import ttk
import tkentrycomplete

tracemalloc.start()

config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), 'config.ini'))

key = config.get('API_KEYS', 'api_key')
secret = config.get('API_KEYS', 'api_secret')
mode = float(config.get('API_KEYS', 'mode'))

mainnet='https://fapi.binance.com'
testnet='https://testnet.binancefuture.com'
baseurl=testnet if mode == 0 else mainnet

um_futures_client = UMFutures(key=key, secret=secret, base_url=baseurl)

exchange_info=um_futures_client.exchange_info()
trading_pairs = [symbol['symbol'] for symbol in exchange_info['symbols']]

symbol = "BTCUSDT"
side = "BUY"
quantity = 0.001
stopPrice = 27000
stopLossPrice = 26900
orderMode = 0
recvWindow = 7000
stop_monitor = False

root = tk.Tk()
root.title("Binance Бот")

box_value = tk.StringVar()
def update_symbol():
    global symbol
    symbol = box_value.get()

combo_label = ttk.Label(root, text="Торговая пара:")
combo_label.pack()
combo = tkentrycomplete.AutocompleteCombobox(textvariable=box_value)
combo.set_completion_list(trading_pairs)
combo.bind("<<ComboboxSelected>>", update_symbol)
combo.pack()

price_label = ttk.Label(root, text="Цена:")
price_entry = ttk.Entry(root)
stop_loss_label = ttk.Label(root, text="Стоп-лосс:")
stop_loss_entry = ttk.Entry(root)
quantity_label = ttk.Label(root, text="Количество:")
quantity_entry = ttk.Entry(root)
start_stop_button = ttk.Button(root, text="Start")
side_label = ttk.Label(root, text="Сторона:")
side_combo = ttk.Combobox(root, values=["BUY", "SELL"])
side_combo.config(state="readonly")

price_label.pack()
price_entry.pack()
stop_loss_label.pack()
stop_loss_entry.pack()
quantity_label.pack()
quantity_entry.pack()
side_label.pack()
side_combo.pack()
start_stop_button.pack()

async def sm_order(symbol, side, quantity, price, tick_size):
    tick_size *= 10
    priceTick = round(price / tick_size) * tick_size
    # print('EXECUTING 1')
    try:
        response = um_futures_client.new_order(
            symbol=symbol,
            side=side,
            type="STOP_MARKET",
            quantity=quantity,
            timeInForce="GTC",
            stopPrice=priceTick,
            recvWindow=recvWindow,
        )
        # logging.info(response)
    except ClientError as error:
        logging.error(
            "Found error. status: {}, error code: {}, error message: {}".format(
                error.status_code, error.error_code, error.error_message
            )
        )

async def tpm_order(symbol, side, quantity, price, tick_size):
    tick_size *= 10
    priceTick = round(price / tick_size) * tick_size
    # print('EXECUTING 2')
    try:
        response = um_futures_client.new_order(
            symbol=symbol,
            side=side,
            type="TAKE_PROFIT_MARKET",
            quantity=quantity,
            timeInForce="GTC",
            stopPrice=priceTick,
            recvWindow=recvWindow,
        )
        # logging.info(response)
    except ClientError as error:
        logging.error(
            "Found error. status: {}, error code: {}, error message: {}".format(
                error.status_code, error.error_code, error.error_message
            )
        )

async def sm_order_sl(symbol, side, quantity, price, tick_size):
    tick_size *= 10
    priceTick = round(price / tick_size) * tick_size
    side="SELL" if side=="BUY" else "BUY"
    # print('EXECUTING 3')
    try:
        response = um_futures_client.new_order(
            symbol=symbol,
            side=side,
            type="STOP_MARKET",
            quantity=quantity,
            timeInForce="GTC",
            stopPrice=priceTick,
            closeposition=True,
            recvWindow=recvWindow,
        )
        # logging.info(response)
    except ClientError as error:
        logging.error(
            "Found error. status: {}, error code: {}, error message: {}".format(
                error.status_code, error.error_code, error.error_message
            )
        )

async def tpm_order_sl(symbol, side, quantity, price, tick_size):
    tick_size *= 10
    priceTick = round(price / tick_size) * tick_size
    side="SELL" if side=="BUY" else "BUY"
    # print('EXECUTING 4')
    try:
        response = um_futures_client.new_order(
            symbol=symbol,
            side=side,
            type="TAKE_PROFIT_MARKET",
            quantity=quantity,
            timeInForce="GTC",
            stopPrice=priceTick,
            closeposition=True,
            recvWindow=recvWindow,
        )
        # logging.info(response)
    except ClientError as error:
        logging.error(
            "Found error. status: {}, error code: {}, error message: {}".format(
                error.status_code, error.error_code, error.error_message
            )
        )

async def selector_entry(side, stopPrice, symbol, quantity, tick, current):
    price = current
    ticksize = tick
    if side=='BUY':
        if stopPrice > price:
            orderMode=1
            print(f'Executing {orderMode}')
            await sm_order(symbol, side, quantity, stopPrice, ticksize)
        elif stopPrice < price:
            orderMode=2
            print(f'Executing {orderMode}')
            await tpm_order(symbol, side, quantity, stopPrice, ticksize)

    elif side=='SELL':
        if stopPrice > price:
            orderMode=3
            print(f'Executing {orderMode}')
            await tpm_order(symbol, side, quantity, stopPrice, ticksize)
        elif stopPrice < price:
            orderMode=4
            print(f'Executing {orderMode}')
            await sm_order(symbol, side, quantity, stopPrice, ticksize)

async def selector_sl(side, stopLossPrice, symbol, quantity, tick, current):
    price = current
    ticksize = tick
    if side=='BUY':
        if stopLossPrice > price:
            orderMode=1
            print(f'Executing SL {orderMode}')
            await tpm_order_sl(symbol, side, quantity, stopLossPrice, ticksize)
        elif stopPrice < price:
            orderMode=2
            print(f'Executing SL {orderMode}')
            await sm_order_sl(symbol, side, quantity, stopLossPrice, ticksize)

    elif side=='SELL':
        if stopPrice > price:
            orderMode=3
            print(f'Executing SL {orderMode}')
            await sm_order_sl(symbol, side, quantity, stopLossPrice, ticksize)
        elif stopPrice < price:
            orderMode=4
            print(f'Executing SL {orderMode}')
            await tpm_order_sl(symbol, side, quantity, stopLossPrice, ticksize)

async def monitor(side, stopPrice, stopLossPrice, symbol, quantity):
    all_open_orders = um_futures_client.get_all_orders(symbol=symbol)
    all_open_positions = um_futures_client.get_position_risk(symbol=symbol,recvWindow=6000)
    isPositions = 0
    isOrders = 0
    isOrderType = 0

    symbol_name = symbol
    exchange_info = um_futures_client.exchange_info()
    symbol_info = next((symbol for symbol in exchange_info['symbols'] if symbol['symbol'] == symbol_name), None)
    tick = float(symbol_info['filters'][0]['tickSize'])

    current = float(um_futures_client.ticker_price(symbol_name)['price'])
    
    # print(all_open_orders)
    # print('\n\n\n')
    # print(all_open_positions)

    amt = float(all_open_positions[0]['positionAmt'])
    if amt == 0:
        isPositions = 1 # no open position
    else:
        isPositions = 2 # found open position

    new_orders = [order for order in all_open_orders if order['status'] == 'NEW']
    openAmount = len(new_orders)
    if not new_orders:
        isOrders = 1 # no open orders
    elif 0 < openAmount < 2:
        isOrders = 2 # found 1 open order
        for order in new_orders:
            if order['closePosition'] == 'True':
                isOrderType = 1 # order closePosition is TRUE
    elif openAmount >= 2:
        isOrders = 3 # found two orders, assumed normalcy

    print(f'isOrders={isOrders}')
    print(f'isPositions={isPositions}')

    if (isPositions==2 and isOrders==1) or (isOrders==2 and isOrderType==0):
        print('EXECUTING SL')
        await selector_sl(side, stopLossPrice, symbol, quantity, tick, current)
    
    if isPositions==1 and isOrders==1:
        print('EXECUTING ENTRY')
        await selector_entry(side, stopPrice, symbol, quantity, tick, current)
        await selector_sl(side, stopLossPrice, symbol, quantity, tick, current)

async def monitor_loop(side, stopPrice, stopLossPrice, symbol, quantity):
    side=side_combo.get()
    stopPrice=float(price_entry.get())
    stopLossPrice=float(stop_loss_entry.get())
    symbol=combo.get()
    quantity=float(quantity_entry.get())
    while not stop_monitor:
        await monitor(side, stopPrice, stopLossPrice, symbol, quantity)

def start_monitor_thread(side, stopPrice, stopLossPrice, symbol, quantity):
    # Create a new event loop for the thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Start the monitor loop in a new task
    task = loop.create_task(monitor_loop(side, stopPrice, stopLossPrice, symbol, quantity))

    # Run the event loop until the task is complete
    loop.run_until_complete(task)

def stop_monitor_thread():
    # Set the stop flag to True
    global stop_monitor
    stop_monitor = True

def start_stop():
    global stop_monitor
    if start_stop_button["text"] == "Start":
        start_stop_button["text"] = "Stop"
        # side = update_side()
        # stopPrice = update_price()
        # stopLossPrice = update_stop_loss()
        # symbol = update_symbol()
        # quantity = update_quantity()
        start_monitor_thread(side, stopPrice, stopLossPrice, symbol, quantity)
    else:
        start_stop_button["text"] = "Start"
        stop_monitor_thread()

start_stop_button["command"] = start_stop

root.mainloop()
