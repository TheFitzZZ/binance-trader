
# -*- coding: UTF-8 -*-
# @yasinkuyu
import config 

from BinanceAPI import BinanceAPI
from binance.client import Client
from Messages import Messages

# Define Custom import vars
client = BinanceAPI(config.api_key, config.api_secret)
client2 = Client(config.api_key, config.api_secret)
class Orders():
     
    @staticmethod
    def buy_limit(symbol, quantity, buyPrice):
        order = client.buy_limit(symbol, quantity, buyPrice) 
	while (order is None ):
            try:
                order = client.sell_limit(symbol, quantity, buyPrice) 
	    except ValueError:
		order = None
            else:
                break
#        order = client.buy_limit(symbol, quantity, buyPrice)

        if 'msg' in order:
            Messages.get(order['msg'])

        # Buy order created.
        return order['orderId']
    
    @staticmethod
    def get_asset(symbol):
        asset = symbol[:-3]
        orig_quantity = client2.get_asset_balance(asset=asset)  

        return orig_quantity
    
    @staticmethod
    def sell_limit(symbol, quantity, sell_price):
        order = client.sell_limit(symbol, quantity, sell_price) 
        while (order is None):
            try:
                order = client.sell_limit(symbol, quantity, sell_price) 
            except ValueError:
                order = None
            else:
                break	 
#        order = client.sell_limit(symbol, quantity, sell_price)  

        if 'msg' in order:
            Messages.get(order['msg'])

        return order

    @staticmethod
    def buy_market(symbol, quantity):

        order = client.buy_market(symbol, quantity)  

        if 'msg' in order:
            Messages.get(order['msg'])

        return order

    @staticmethod
    def sell_market(symbol, quantity):

        order = client.sell_market(symbol, quantity)  

        if 'msg' in order:
            Messages.get(order['msg'])

        return order

    @staticmethod
    def cancel_order(symbol, orderId):
        
        try:
            
            order = client.cancel(symbol, orderId)
            if 'msg' in order:
                Messages.get(order['msg'])
            
            print ('Profit loss, called order, %s' % (orderId))
        
            return True
        
        except Exception as e:
            print ('co: %s' % (e))
            return False

    @staticmethod
    def get_order_book(symbol):
        try:

            orders = client.get_orderbooks(symbol, 5)
            lastBid = float(orders['bids'][0][0]) #last buy price (bid)
            lastAsk = float(orders['asks'][0][0]) #last sell price (ask)
     
            return lastBid, lastAsk
    
        except Exception as e:
            print ('ob: %s' % (e))
            return 0, 0

    @staticmethod
    def get_order(symbol, orderId):
        try:

            order = client.query_order(symbol, orderId)

            if 'msg' in order:
                Messages.get(order['msg']) # TODO
                return False

            return order

        except Exception as e:
            print ('go: %s' % (e))
            return False

    @staticmethod
    def get_order_status(symbol, orderId):
        try:

            order = client.query_order(symbol, orderId)
    
            if 'msg' in order:
                Messages.get(order['msg'])
        
            return order['status']
 
        except Exception as e:
            print ('gos: %s' % (e))
            return None
    
    @staticmethod
    def get_ticker(symbol):
        try:        
    
            ticker = client.get_ticker(symbol)
 
            return ticker
        except Exception as e:
            print ('gt: %s' % (e))
    
    @staticmethod
    def get_info(symbol):
        try:        
    
            info = client.get_exchance_info()
            
            if symbol != "":
                return [market for market in info['symbols'] if market['symbol'] == symbol][0]
 
            return info
            
        except Exception as e:
            return

    @staticmethod
    def get_balance(symbol="BTC"):
        try:

            balances = client.get_account()
            balances['balances'] = {item['asset']: item for item in balances['balances']}

            return balances['balances'][symbol]['free']

        except Exception as e:
            print ('gb: %s' % (e))
