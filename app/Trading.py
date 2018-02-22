# -*- coding: UTF-8 -*-
# @yasinkuyu

# Define Python imports
import os
import sys
import time
import datetime
import config

# Define Custom imports
from BinanceAPI import BinanceAPI
from Database import Database
from Orders import Orders
from Tools import Tools
from time import sleep
from time import sleep
from binance.client import Client
from sys import exit


class Trading():

    # Define trade vars
    order_id = 0

    # percent (When you drop x%, sell panic.)
    stop_loss = 0

    # Buy/Sell qty
    quantity = 0
    sym = None
    
    # Define Custom import vars
    

    original_qty = 0
    all_qty = 0
    err_qty = 0
    sell_qty = 0
    use_stopfile = False

    sym = None

    # float(step_size * math.floor(float(free)/step_size))
    step_size = 0
    tick_size = 0
    min_notional = 0

    # Check bot status
    bot_status = "scan"
    partial_status = None
  
    #sym = self.option.symbol
    

    # Define static vars
    WAIT_TIME_BUY_SELL = 2 # seconds
    WAIT_TIME_CHECK_BUY = 10 # seconds
    WAIT_TIME_CHECK_SELL = 10 # seconds
    WAIT_TIME_CHECK_HOLD = 20 # seconds
    WAIT_TIME_PAUSE_BUY = 60 # seconds
    WAIT_TIME_STOP_LOSS = 600 # seconds
    WAIT_TIME_SELL = 2 # seconds

    # Counter for events
    total_buy = 0
    total_sell = 0
    total_stoploss = 0

    def decimal_formatter(number):
            return format(number, '.8f')

    def find_quantity(total, price):
            quantity = float(total) / float(price)
            return quantity

    def calculate_price_target(initial, percentage=1.1):
            target = (percentage * float(initial) / 100 ) + float(initial) + 0.00000001
            return decimal_formatter(target)

    def calculate_profit_percentage(initial, final):
            percent = (float(final) - float(initial)) / float(initial) * 100
            return format(percent, '.2f')

    #Function to allow an external file stop the bot after the last sell/cancel
    def stop_bot( self ):
        try:
              stopfile = open("stopfile.txt", "r")
              filetext = stopfile.read()
              
              if (filetext == "stop"):
                 print self.log_wrap('STOP sign read in file. Stopping bot.')
                 quit()

        except Exception as e:
              print 'Stopfile couldn´t be opened.'

    #Function to build console output with proper timestamps, coin symbols and seperators  ... oh and juicy counters!
    def log_wrap( self, ttext ):
        ttime = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
        tsymbol = ' | ' + '[' + self.option.symbol + ']' + ' | '
        # Buy/Sell/stopLoss indicators + Ratio
        bsl = ' | B:' + str(self.total_buy) + '/S:' + str(self.total_sell) + '/L:' + str(self.total_stoploss) + '/R:'
        # Don't devide by 0 to not break the internet
        if self.total_stoploss == 0:
            ratio = self.total_sell
        else:
            ratio = (self.total_sell/self.total_stoploss)
        bsl = bsl + str(ratio)
        prefix = ttime + tsymbol + ttext + bsl
        return str(prefix)
    
    def __init__(self, option):

        # Get argument parse options
        self.option = option

        # Define parser vars
        self.order_id = self.option.orderid
        self.quantity = self.option.quantity
        self.wait_time = self.option.wait_time
        self.stop_loss = self.option.stop_loss
        self.max_amount = self.option.max_amount

        #BTC amount
        self.amount = self.option.amount
        self.increasing = self.option.increasing
        self.decreasing = self.option.decreasing
        self.sym = self.option.symbol
        self.original_qty = self.option.hodl_qty
        self.use_stopfile = self.option.stopfile
        
    def buy(self, symbol, quantity, buyPrice):

        # Check last order
        self.checkorder()
        
        try:

            # Create order
            orderId = Orders.buy_limit(symbol, quantity, buyPrice)

            # Database log
            Database.write([orderId, symbol, 0, buyPrice, 'BUY', quantity, self.option.profit])

            print self.log_wrap('Buy order created id:%d, q:%.8f, p:%.8f' % (orderId, quantity, float(buyPrice)))

            self.order_id = orderId

            self.bot_status = "buy"

            return orderId

        except Exception as e:
            print self.log_wrap('bl: %s' % (e))
           # time.sleep(self.WAIT_TIME_BUY_SELL)
            WAIT_TIME_STOP_LOSS = 600
            self.bot_status = "cancel"
            return None

        
    def sell(self, symbol, quantity, orderId, sell_price, last_price):

        '''
        The specified limit will try to sell until it reaches.
        If not successful, the order will be canceled.
        '''
        self.partial_status = None
        #time.sleep(self.WAIT_TIME_CHECK_BUY)
        confirm = False
        cancel_flag = True
        seconds = 0
        while not confirm:
                sleep(1)
                seconds += 1
                buy_order = Orders.get_order(symbol, orderId)

                if not buy_order:
                    print self.log_wrap("SERVER DELAY! Rechecking...")
                    return
                if buy_order['status'] == 'FILLED' and buy_order['side'] == "BUY":
                    print self.log_wrap("Buy order filled... Try sell...")
                    self.total_buy = self.total_buy + 1 #Count the buy
                    confirm = True
                elif buy_order['status'] == 'PARTIALLY_FILLED' and buy_order['side'] == "BUY":
                    print self.log_wrap("Buy order partially filled... Wait 1 more second...")
                    quantity = self.check_partial_order(symbol, orderId, sell_price)
                    self.total_buy = self.total_buy + 1 #Count partial buy also as buy
                    confirm = True
                else:
                    cancel_flag = False
                    
                if seconds == self.WAIT_TIME_CHECK_BUY:
                    confirm = True

        if not cancel_flag:
            flago = 0
            while (flago != 1):
                try:
                    orderId = (buy_order['orderId'])
                except KeyError:
                    print self.log_wrap("Keyerror")  
                else:
                    flago = 1
            self.cancel(symbol, orderId)
            print self.log_wrap("Buy order fail (Not filled) Cancel order...")
            sleep(5)
            
        print self.log_wrap("Checking..")
        order_status = None
        order_side = None
        check_order = Orders.get_order(symbol, orderId)

        flago = 0
        while (flago != 1):
            try:
                order_status = (check_order['status'])
            except KeyError:
                print self.log_wrap("Keyerror")
                check_order = Orders.get_order(symbol, orderId)
            else:
                flago = 1

        flago = 0
        while (flago != 1):
            try:
                order_side = (check_order['side'])
            except KeyError:
                print self.log_wrap("Keyerror")
                check_order = Orders.get_order(symbol, orderId)
            else:
                flago = 1        
                
        print self.log_wrap('Binance Order Status: %s, Binance Order Side: %s, Partial status: %s' % (order_status, order_side, self.partial_status))
        if order_status == "CANCELED":
            if self.partial_status == None:
                self.bot_status = "cancel"
                self.order_id = 0
                return
        
        sell_id = None

        try:
            self.all_qty = self.format_quantity(float(Orders.get_asset(symbol)['free']))
        except Exception, error:
            self.all_qty = 0
        
        try:
            self.sell_qty = self.format_quantity(float(self.all_qty - self.original_qty))
        except Exception, error:
            self.sell_qty = 0
            
        if quantity < self.sell_qty:
            quantity = self.format_quantity(float(self.sell_qty))
        print('Quantity: %s' % (quantity))
        print('Self Quantity: %s' % (self.sell_qty))
        flago = 0
        sub = quantity * 0.005
        while (flago != 1):
            sleep(1)
            try:
                sell_id = Orders.sell_limit(symbol, quantity, sell_price)['orderId']
                print('Quantity: %s' % (quantity))
            except Exception, error:
                quantity = self.format_quantity(float(quantity - sub))
                print('Quantity: %s' % (quantity))
            else:
                flago = 1
                print self.log_wrap("Order placed. Confirming...")
                sleep(1)

        print self.log_wrap("Sell order created" )

        if Orders.get_order(symbol, sell_id)['status'] == 'FILLED':

            print self.log_wrap('Sell order (Filled) id: %d' % sell_id)
            print self.log_wrap('LastPrice : %.8f' % last_price)
            print self.log_wrap('Profit: %%%s. Buy price: %.8f Sell price: %.8f' % (self.option.profit, float(buy_order['price']), sell_price))

            self.total_sell = self.total_sell + 1 #Count sell - not sure if that's the right spot tho

            self.order_id = 0
            self.bot_status = "sell"
            time.sleep(self.WAIT_TIME_CHECK_SELL)
            return
  
        '''
        If all sales trials fail,

        the grievance is stop-loss.
        '''
        if self.stop_loss > 0:
            flag = 0
            while (flag != 1):
                # If sell order failed after 5 seconds, 5 seconds more wait time before selling at loss
                time.sleep(self.WAIT_TIME_CHECK_HOLD)
                ticker = Orders.get_ticker(symbol)
                flag1 = 0
                while (flag1 != 1):
                    try:
                        lastPrice = float(ticker['lastPrice'])
                    except Exception, error:
                        ticker = Orders.get_ticker(symbol)
                    else:
                        flag1 = 1
                        break

                lossprice = sell_price - (sell_price * self.stop_loss / 100)
                print self.log_wrap('Hold...')   
                print self.log_wrap('LastPrice : %.8f' % last_price)
                print self.log_wrap('Stop-loss, sell limit, %s' % (lossprice))
                if Orders.get_order(symbol, sell_id)['status'] == 'FILLED':
                    self.order_id = 0
                    self.bot_status = "sell"
                    flag = 1
                if lastPrice <= lossprice:
                    flag = 1
                    print self.log_wrap('Waiting to stop loss...')
                    time.sleep(self.WAIT_TIME_CHECK_SELL)
                    self.stop(symbol, quantity, sell_id, sell_price)
                    self.total_stoploss = self.total_stoploss + 1 #Count stop loss
                    time.sleep(self.WAIT_TIME_STOP_LOSS)
            print self.log_wrap('Sold! Continue trading...')
            self.total_sell = self.total_sell + 1 #Count sell
            self.order_id = 0
            self.bot_status = "sell"
        else:
            sell_status = 'NEW'
   
            while (sell_status != "FILLED"):
                time.sleep(self.WAIT_TIME_CHECK_HOLD)
                sells = Orders.get_order(symbol, sell_id)
                while True:
                    try:
                        sell_status = sells['status']
                    except Exception, error:
                        sells = Orders.get_order(symbol, sell_id)  
                    else:
                        break 
                ticker = Orders.get_ticker(symbol)
                while True:
                    try:
                        lastPrice = float(ticker['lastPrice'])
                    except Exception, error:
                        ticker = Orders.get_ticker(symbol)
                    else:
                        print self.log_wrap('Status: %s Current price: %s Sell price: %s' % (sell_status, lastPrice, sell_price))
                        break
            print self.log_wrap('Sold! Continue trading...')
            self.total_sell = self.total_sell + 1 #Count sell
            order_id = 0
            self.order_id = 0
            self.bot_status = "sell"
            time.sleep(self.WAIT_TIME_CHECK_SELL)
            
    def stop(self, symbol, quantity, orderId, sell_price):
        # If the target is not reached, stop-loss.
        stop_order = Orders.get_order(symbol, orderId)
        old_qty = quantity
        if float(stop_order['executedQty']) > 0:
 
            quantity = self.format_quantity(float(stop_order['executedQty']))

        lossprice = sell_price - (sell_price * self.stop_loss / 100)
        status = stop_order['status']

        # Order status
        if status == 'NEW':
            if self.cancel(symbol, orderId):
                # Stop loss
                lastBid, lastAsk = Orders.get_order_book(symbol)
                print self.log_wrap('Stop-loss, sell market, %s' % (lastAsk))
                flago = 0
                sub = quantity * 0.005
                while (flago != 1):
                    stop_order = Orders.get_order(symbol, orderId)
                    status = stop_order['status']
                    if status == 'FILLED':
                        return True
                        flago = 1
                        break
                    try:
                        sell_id = Orders.sell_market(symbol, quantity)['orderId']
                    except Exception, error:
                        quantity = self.format_quantity(float(quantity - sub))      
                    else:
                        flago = 1
                    sleep(1)
                
                               
            else:
                print self.log_wrap('Cancel did not work... Might have been sold before stop loss...')
                self.total_sell = self.total_sell + 1 #Count sell
                return True

        elif status == 'PARTIALLY_FILLED':
            self.order_id = 0
            print self.log_wrap('Sell partially filled, hold sell position to prevent dust coin. Continue trading...')

            new_quantity = self.format_quantity(float(old_qty - quantity))
            sub = new_quantity * 0.005
            flago = 0
            while (flago != 1):
                sleep(1)
                stop_order = Orders.get_order(symbol, orderId)
                status = stop_order['status']
                if status == 'FILLED':
                    return True
                    flago = 1
                    break
                try:
                    sell_id = Orders.sell_market(symbol, new_quantity)['orderId']
                except Exception, error:
                    new_quantity = self.format_quantity(float(new_quantity - sub))
                else:
                    return True

        elif status == 'FILLED':
            self.order_id = 0
            print self.log_wrap('Order filled before sell at loss!')
            self.total_sell = self.total_sell + 1 #Count sell
            return True
        else:
            return False

    def cancel(self,symbol, orderId):
        # If order is not filled, cancel it.
        check_order = Orders.get_order(symbol, orderId)
        
        if not check_order:
            self.order_id = 0
            return True
            
        if check_order['status'] == 'NEW' or check_order['status'] != "CANCELLED" or check_order['status'] == 'PARTIALLY_FILLED':
            Orders.cancel_order(symbol, orderId)
            self.order_id = 0
            return True

    def calc(self, lastBid):
        try:

            return lastBid + (lastBid * self.option.profit / 100)

        except Exception as e:
            print self.log_wrap('c: %s' % (e))
            return

    def checkorder(self):
        # If there is an open order, exit.
        if self.order_id > 0:
            exit(1)

    def check_partial_order(self, symbol, orderId, price):
        #time.sleep(self.WAIT_TIME_BUY_SELL)
        self.partial_status = "hold"
        quantity = 0

        while (self.partial_status == "hold"):
            order = Orders.get_order(symbol, orderId)

            if order['status'] == 'PARTIALLY_FILLED':
                print self.log_wrap("Order still partially filled...")
                quantity = self.format_quantity(float(order['executedQty']))

                if self.min_notional > quantity * price:
                    print self.log_wrap("Can't sell below minimum allowable price. Hold for 10 seconds...")
                    time.sleep(self.WAIT_TIME_CHECK_HOLD)
                else:
                    self.cancel(symbol, orderId)
                    self.partial_status = "partial"

            else:
                self.partial_status = "sell"
                quantity = self.format_quantity(float(order['executedQty']))

        return quantity

    def action(self, symbol):

        # Order amount
        quantity = self.quantity

        # Fetches the ticker price
        ticker = Orders.get_ticker(symbol)
        
        while True:
            try:
                lastPrice = float(ticker['lastPrice'])
            except Exception, error:
                ticker = Orders.get_ticker(symbol)
            else:
                break
        while True:
            try:
                lastBid = float(ticker['bidPrice']) 
            except Exception, error:
                ticker = Orders.get_ticker(symbol)     
            else:
                break
        while True:
            try:
                lastAsk = float(ticker['askPrice']) 
            except Exception, error:
                ticker = Orders.get_ticker(symbol)     
            else:
                break
    #    lastPrice = float(ticker['lastPrice'])
    #    lastBid = float(ticker['bidPrice'])
    #    lastAsk = float(ticker['askPrice'])

        # Target buy price, add little increase #87
        buyPrice = lastBid + (lastBid * self.increasing / 100)
    #   buyPrice = lastBid + (lastBid * 0.01)
        # Target sell price, decrease little 
        sellPrice = lastAsk - (lastAsk * self.decreasing / 100)
    #    sellPrice = lastAsk - (lastAsk * 0.01)

        # Spread ( profit )
        profitableSellingPrice = self.calc(lastBid)

        # Format Buy /Sell price according to Binance restriction
        buyPrice = round(buyPrice, self.tick_size)
        sellPrice = round(sellPrice, self.tick_size)

        # Order amount
        if self.quantity > 0:
            quantity = self.quantity
        else:
            if self.max_amount:
                self.amount = float(Orders.get_balance("BTC"))
            quantity = self.format_quantity(self.amount / buyPrice)

        # Check working mode
        if self.option.mode == 'range':

            buyPrice = float(self.option.buyprice)
            sellPrice = float(self.option.sellprice)
            profitableSellingPrice = sellPrice

        # Screen log
        if self.option.prints and self.order_id == 0:
            print self.log_wrap('price:%.8f buyp:%.8f sellp:%.8f-bid:%.8f ask:%.8f' % (lastPrice, buyPrice, profitableSellingPrice, lastBid, lastAsk))

        '''
        Did profit get caught
        if ask price is greater than profit price,
        buy with my buy price,
        '''

        if (lastAsk >= profitableSellingPrice and self.option.mode == 'profit') or \
           (lastPrice <= float(self.option.buyprice) and self.option.mode == 'range'):

            if self.order_id == 0:

                while (self.bot_status != "buy"):

                    if self.bot_status == "cancel":
                        self.bot_status = "scan"
                        return
                    self.buy(symbol, quantity, buyPrice)

        if self.order_id > 0:

            # range mode
            if self.option.mode == 'range':
                profitableSellingPrice = self.option.sellprice

            # Sell price with proper sat count
            profitableSellingPrice = round((profitableSellingPrice - (profitableSellingPrice * self.option.decreasing / 100)), self.tick_size)

            while (self.bot_status != "sell"):

                if self.bot_status == "cancel":
                    self.bot_status = "scan"
                    return

                self.sell(symbol, quantity, self.order_id, profitableSellingPrice, lastPrice)

        self.bot_status = "scan"

    def filters(self):

        symbol = self.option.symbol

        # Get symbol exchance info
        symbol_info = Orders.get_info(symbol)

        if not symbol_info:
            print self.log_wrap("Invalid symbol, please try again...")
            exit(1)

        symbol_info['filters'] = {item['filterType']: item for item in symbol_info['filters']}

        return symbol_info

    def get_satoshi_count(self, num):
        return int(str(Tools.e2f(num))[::-1].find('.'))

    # Adjust quantity with proper step_size
    def format_quantity(self, quantity):

        if self.step_size == 1:
            quantity = int(round(quantity))
        else:
            quantity = round(quantity, self.step_size)

        return quantity

    def validate(self):

        valid = True
        symbol = self.option.symbol

        filters = self.filters()['filters']

        minQty = float(filters['LOT_SIZE']['minQty'])
        minPrice = float(filters['PRICE_FILTER']['minPrice'])
        minNotional = float(filters['MIN_NOTIONAL']['minNotional'])
        quantity = float(self.option.quantity)

        lastPrice = float(Orders.get_ticker(symbol)['lastPrice'])

        # minNotional defines minimum amount a coin can be bought
        self.min_notional = minNotional

        # stepSize defines the intervals that a quantity/icebergQty can be increased/decreased by.
        self.step_size = self.get_satoshi_count(float(filters['LOT_SIZE']['stepSize']))

        # tickSize defines the intervals that a price/stopPrice can be increased/decreased by.
        # -1 because it doesn't return decimal point, pure exponential form
        self.tick_size = self.get_satoshi_count(float(filters['PRICE_FILTER']['tickSize'])) - 1

        if self.quantity > 0:
            quantity = float(self.quantity)
        else:
            if self.max_amount:
                self.amount = float(Orders.get_balance("BTC"))

            lastBid, lastAsk = Orders.get_order_book(symbol)
            quantity = self.format_quantity(self.amount / lastBid)

        # Just for validation
        price = lastPrice
        notional = lastPrice * quantity

        # minQty = minimum order quantity
        if quantity < minQty:
            print self.log_wrap("Invalid quantity, minQty: %.8f (u: %.8f)" % (minQty, quantity))
            valid = False

        if price < minPrice:
            print self.log_wrap("Invalid price, minPrice: %.8f (u: %.8f)" % (minPrice, price))
            valid = False

        # minNotional = minimum order value (price * quantity)
        if notional < minNotional:
            print self.log_wrap("Invalid notional, minNotional: %.8f (u: %.8f)" % (minNotional, notional))
            valid = False

        if not valid:
            exit(1)

    def run(self):

        cycle = 0
        actions = []

        symbol = self.option.symbol

        print self.log_wrap("Original code: yasinkuyu - Fork by aguilardmarkanthony & FitzZZ")
        print self.log_wrap('Auto Trading for Binance.com. --symbol: %s\n' % symbol)

        # Validate symbol
        self.validate()

        if self.option.mode == 'range':

           if self.option.buyprice == 0 or self.option.sellprice == 0:
               print self.log_wrap('Plese enter --buyprice / --sellprice\n')
               quit()

           print self.log_wrap('Wait buyprice:%.8f sellprice:%.8f' % (self.option.buyprice, self.option.sellprice))

        else:
           print self.log_wrap('%s%% profit scanning for %s\n' % (self.option.profit, symbol))

        print self.log_wrap('... \n')

        while (cycle <= self.option.loop):

            startTime = time.time()
            
            #Check for stopfile if active, if so, check if stop sign exists
            if (self.use_stopfile == True):
                self.stop_bot()
    
            self.action(symbol)
            
            endTime = time.time()

            if endTime - startTime < self.wait_time:

               time.sleep(self.wait_time - (endTime - startTime))
              #sleep(5)
               # 0 = Unlimited loop
               if self.option.loop > 0:
                   cycle = cycle + 1
