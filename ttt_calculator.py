import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading
import time

class ToolTip(object):
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.widget.bind("<ButtonPress>", self.leave)
        self.id = None
        self.tw = None

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hide()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(500, self.show)

    def unschedule(self):
        id_ = self.id
        self.id = None
        if id_:
            self.widget.after_cancel(id_)

    def show(self):
        def tip_pos_calculator(widget, label,
                    tip_delta=(10, 5), pad=(5, 3, 5, 3)):
            w = widget

            s_width, s_height = w.winfo_screenwidth(), w.winfo_screenheight()
            width, height = (pad[0] + label.winfo_reqwidth() + pad[2],
                           pad[1] + label.winfo_reqheight() + pad[3])

            mouse_x, mouse_y = w.winfo_pointerxy()

            x1, y1 = mouse_x + tip_delta[0], mouse_y + tip_delta[1]
            x2, y2 = x1 + width, y1 + height

            x_delta = x2 - s_width
            if x_delta < 0:
                x_delta = 0
            y_delta = y2 - s_height
            if y_delta < 0:
                y_delta = 0

            offscreen = (x_delta, y_delta) != (0, 0)

            if offscreen:
                if x_delta:
                    x1 = mouse_x - tip_delta[0] - width

                if y_delta:
                    y1 = mouse_y - tip_delta[1] - height

            return x1, y1

        # hide previous tooltip
        self.hide()  
        
        # creates a toplevel window
        self.tw = tk.Toplevel(self.widget)
        
        # Leaves only the label and removes the app window
        self.tw.wm_overrideredirect(True)

        win = tk.Frame(self.tw,
                    background="#ffffe0",
                    borderwidth=0)
        label = tk.Label(win,
                        text=self.text,
                        justify=tk.LEFT,
                        background="#ffffe0",
                        relief=tk.SOLID,
                        borderwidth=0,
                        wraplength=180)

        label.grid(padx=1, pady=1)
        win.grid()

        x, y = tip_pos_calculator(self.widget, label)

        self.tw.wm_geometry("+%d+%d" % (x, y))

    def hide(self):
        tw = self.tw
        if tw:
            tw.destroy()
        self.tw = None

class TTTCalculator:
    def __init__(self, root):
        self.root = root
        self.root.title("Taylor Trading Technique Calculator")
        
        # Define common futures contracts
        self.futures_contracts = {
            "ES (S&P 500 E-mini)": "ES=F",
            "NQ (Nasdaq E-mini)": "NQ=F",
            "YM (Dow E-mini)": "YM=F",
            "RTY (Russell E-mini)": "RTY=F",
            "CL (Crude Oil)": "CL=F",
            "GC (Gold)": "GC=F",
            "SI (Silver)": "SI=F",
            "ZB (30Y T-Bond)": "ZB=F",
            "ZN (10Y T-Note)": "ZN=F",
            "6E (Euro FX)": "6E=F",
            "6J (Japanese Yen)": "6J=F",
            "6B (British Pound)": "6B=F"
        }
        
        # Define day ranges
        self.day_ranges = ["30 Days", "60 Days", "90 Days", "120 Days", "250 Days"]
        
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Input frame
        input_frame = ttk.LabelFrame(main_frame, text="Input Parameters", padding="10")
        input_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        # Futures Contract Dropdown
        ttk.Label(input_frame, text="Select Futures:").grid(row=0, column=0, padx=5)
        self.contract_var = tk.StringVar()
        self.contract_dropdown = ttk.Combobox(input_frame, 
                                            textvariable=self.contract_var,
                                            values=list(self.futures_contracts.keys()),
                                            width=25,
                                            state="readonly")
        self.contract_dropdown.grid(row=0, column=1, padx=5)
        self.contract_dropdown.set("ES (S&P 500 E-mini)")  # Default value
        
        # Days Range Dropdown
        ttk.Label(input_frame, text="Analysis Period:").grid(row=0, column=2, padx=5)
        self.days_var = tk.StringVar()
        self.days_dropdown = ttk.Combobox(input_frame, 
                                        textvariable=self.days_var,
                                        values=self.day_ranges,
                                        width=15,
                                        state="readonly")
        self.days_dropdown.grid(row=0, column=3, padx=5)
        self.days_dropdown.set("60 Days")  # Default value
        
        # Calculate Button
        self.calc_button = ttk.Button(input_frame, text="Calculate", command=self.calculate)
        self.calc_button.grid(row=0, column=4, padx=10)
        
        # Create tooltips for dropdowns and labels
        self.tooltips = {}
        self.create_tooltip(self.contract_dropdown, 
            "Select the futures contract to analyze.\nThe LSS system works best with volatile contracts.")
        self.create_tooltip(self.days_dropdown,
            "Select the number of days to analyze.\nMore data helps identify cycles but may slow calculations.")
            
        # Add tooltips for buy envelope
        self.decline_label = ttk.Label(main_frame, text="Decline Level: N/A")
        self.decline_label.grid(row=1, column=0, padx=5)
        self.create_tooltip(self.decline_label,
            "The expected decline level based on previous day's trading range.\nUseful for identifying potential support levels.")
        self.buy_under_label = ttk.Label(main_frame, text="Buy Under Level: N/A")
        self.buy_under_label.grid(row=1, column=1, padx=5)
        self.create_tooltip(self.buy_under_label,
            "The recommended maximum price for buying.\nEntering positions below this level increases probability of success.")
        self.todays_low_label = ttk.Label(main_frame, text="Today's Low: N/A")
        self.todays_low_label.grid(row=1, column=2, padx=5)
        self.create_tooltip(self.todays_low_label,
            "Today's lowest price.\nCompare with Decline Level to gauge market strength.")
            
        # Add tooltips for sell envelope
        self.rally_label = ttk.Label(main_frame, text="Rally Level: N/A")
        self.rally_label.grid(row=1, column=3, padx=5)
        self.create_tooltip(self.rally_label,
            "The expected rally level based on previous day's trading range.\nUseful for identifying potential resistance levels.")
        self.buy_high_label = ttk.Label(main_frame, text="Buy High Level: N/A")
        self.buy_high_label.grid(row=1, column=4, padx=5)
        self.create_tooltip(self.buy_high_label,
            "The maximum recommended price for holding long positions.\nConsider taking profits when price reaches this level.")
        self.todays_high_label = ttk.Label(main_frame, text="Today's High: N/A")
        self.todays_high_label.grid(row=1, column=5, padx=5)
        self.create_tooltip(self.todays_high_label,
            "Today's highest price.\nCompare with Rally Level to gauge market strength.")
            
        # Table
        table_frame = ttk.LabelFrame(main_frame, text="Historical Data", padding="10")
        table_frame.grid(row=2, column=0, sticky="nsew")
        
        # Create treeview
        columns = ('Date', 'Open', 'High', 'Low', 'Close', 'Rally Number', 
                  'Decline Number', 'Buy High', 'Buy Under', 'Pivot Buy', 'Pivot Sell', 'Day Type', 'OB/OS', 'Level1_Buy', 'Level1_Sell')
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings')
        
        # Configure headings
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Grid the treeview and scrollbar
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Add tooltip for table columns
        table_tooltip_text = """
Date: Trading date
Open: Opening price for the session
High: Highest price reached during the session
Low: Lowest price reached during the session
Close: Closing price for the session
Rally Number: Calculated rally target based on TTT
Decline Number: Calculated decline target based on TTT
Buy High: Maximum recommended buying level
Buy Under: Recommended entry level for long positions
Pivot Buy: Key support level for the session
Pivot Sell: Key resistance level for the session
Day Type: Buy day, Sell day, or SS day classification
OB/OS: Overbought/Oversold indicator
Level1_Buy: First support level
Level1_Sell: First resistance level"""
        self.create_tooltip(self.tree, table_tooltip_text)
        
        # Configure grid weights
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        
        # Initialize data storage
        self.price_data = pd.DataFrame()
        
        # Add Next Day Plan frame
        plan_frame = ttk.LabelFrame(main_frame, text="Next Day Plan", padding="10")
        plan_frame.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        
        self.plan_label = ttk.Label(plan_frame, text="Plan: Waiting for calculation...", wraplength=600)
        self.plan_label.grid(row=0, column=0, sticky="w")
        
        # Create tooltip for plan
        self.create_tooltip(self.plan_label, 
            "Shows the trading plan for the next day based on current day type and market behavior")

    def create_tooltip(self, widget, text):
        tooltip = ToolTip(widget, text)
        self.tooltips[widget] = tooltip

    def calculate(self):
        # Disable calculate button during calculation
        self.calc_button.configure(state="disabled")
        self.calc_button["text"] = "Fetching data..."
        
        # Create and start calculation thread
        thread = threading.Thread(target=self._calculate_thread)
        thread.daemon = True
        thread.start()
    
    def _calculate_thread(self):
        try:
            # Show status in button
            self.root.after(0, lambda: self.calc_button.configure(text="Connecting..."))
            
            contract_name = self.contract_var.get()
            symbol = self.futures_contracts[contract_name]
            days_str = self.days_var.get()
            days = int(days_str.split()[0])  # Extract number from "XX Days"
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Format dates for yfinance
            start_date = start_date.strftime('%Y-%m-%d')
            end_date = end_date.strftime('%Y-%m-%d')

            # Try to download data with retries
            max_retries = 3
            retry_count = 0
            data = None
            
            while retry_count < max_retries and data is None:
                try:
                    # Update status
                    self.root.after(0, lambda: self.calc_button.configure(
                        text=f"Downloading... ({retry_count + 1}/{max_retries})"))
                    
                    # Download data with a timeout
                    data = yf.download(symbol, 
                                     start=start_date, 
                                     end=end_date, 
                                     progress=False,
                                     timeout=10)
                    
                    if data is None or data.empty:
                        raise ValueError(f"No data returned for {symbol}")
                    
                except Exception as download_error:
                    retry_count += 1
                    if retry_count == max_retries:
                        raise Exception(f"Failed to download data after {max_retries} attempts: {str(download_error)}")
                    self.root.after(0, lambda: self.calc_button.configure(
                        text=f"Retrying... ({retry_count}/{max_retries})"))
                    time.sleep(1)  # Wait 1 second before retrying
            
            if data.empty:
                self.root.after(0, lambda: messagebox.showerror("Error", 
                    f"No data found for {symbol}. Please try a different symbol or time period."))
                return
            
            # Verify required columns exist
            required_columns = ['Open', 'High', 'Low', 'Close']
            missing_columns = [col for col in required_columns if col not in data.columns]
            if missing_columns:
                raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
            
            # Show processing status
            self.root.after(0, lambda: self.calc_button.configure(text="Processing..."))
            
            self.price_data = data
            
            # Run original functions on main thread
            self.root.after(0, self.calculate_envelopes)
            self.root.after(0, self.update_table)
            
        except Exception as e:
            error_message = f"Failed to fetch data: {str(e)}\nPlease check your internet connection and try again."
            self.root.after(0, lambda: messagebox.showerror("Error", error_message))
        finally:
            # Reset button state and text
            self.root.after(0, lambda: self.calc_button.configure(state="normal", text="Calculate"))

    def calculate_envelopes(self):
        if self.price_data.empty:
            return
            
        # Initialize envelope data
        self.envelope_data = self.price_data.copy()
        
        # Initialize Day_Type column with 'Undefined'
        self.envelope_data['Day_Type'] = 'Undefined'
        
        # Calculate Taylor's numbers and overbought/oversold indicator
        for i in range(1, len(self.envelope_data)):
            today = self.envelope_data.iloc[i]
            
            # Calculate overbought/oversold indicator
            # Formula: (High - Open + Close - Low) / (2 * Range)
            daily_range = today['High'] - today['Low']
            if daily_range > 0:  # Avoid division by zero
                ob_os = ((today['High'] - today['Open']) + (today['Close'] - today['Low'])) / (2 * daily_range)
                self.envelope_data.loc[self.envelope_data.index[i], 'OB_OS'] = ob_os * 100  # Convert to percentage
            else:
                self.envelope_data.loc[self.envelope_data.index[i], 'OB_OS'] = 50  # Neutral if no range
            
            # Rally Number = Today's High - Yesterday's Low
            self.envelope_data.loc[self.envelope_data.index[i], 'Rally_Number'] = \
                self.envelope_data.iloc[i]['High'] - self.envelope_data.iloc[i-1]['Low']
            
            # Decline Number = Yesterday's High - Today's Low
            self.envelope_data.loc[self.envelope_data.index[i], 'Decline_Number'] = \
                self.envelope_data.iloc[i-1]['High'] - self.envelope_data.iloc[i]['Low']
            
            # Buy High Number = Today's High - Yesterday's High
            self.envelope_data.loc[self.envelope_data.index[i], 'Buy_High'] = \
                self.envelope_data.iloc[i]['High'] - self.envelope_data.iloc[i-1]['High']
            
            # Buy Under Number = Yesterday's Low - Today's Low
            self.envelope_data.loc[self.envelope_data.index[i], 'Buy_Under'] = \
                self.envelope_data.iloc[i-1]['Low'] - self.envelope_data.iloc[i]['Low']
            
            # Pivot Breakout Numbers
            pivot = (self.envelope_data.iloc[i]['High'] + self.envelope_data.iloc[i]['Low'] + self.envelope_data.iloc[i]['Close']) / 3
            self.envelope_data.loc[self.envelope_data.index[i], 'Pivot_Buy'] = \
                (2 * pivot) - self.envelope_data.iloc[i]['Low']
            self.envelope_data.loc[self.envelope_data.index[i], 'Pivot_Sell'] = \
                (2 * pivot) - self.envelope_data.iloc[i]['High']
            
            # Calculate Level 1 trade points
            level1_buy = today['Open'] - 0.30  # Buy 0.30 points below open
            level1_sell = today['Open'] + 0.30  # Sell 0.30 points above open
            
            self.envelope_data.loc[self.envelope_data.index[i], 'Level1_Buy'] = level1_buy
            self.envelope_data.loc[self.envelope_data.index[i], 'Level1_Sell'] = level1_sell
            
            # Identify Day Type
            if i >= 2:  # Need at least 3 days of data
                today = self.envelope_data.iloc[i]
                yesterday = self.envelope_data.iloc[i-1]
                day_before = self.envelope_data.iloc[i-2]
                
                # Modern adaptation of Taylor's cycle:
                # Look for the patterns but allow for more flexibility
                
                # Buy Day: Look for selling exhaustion and potential reversal
                if (yesterday['Low'] < day_before['Low'] or                    # Lower low OR
                    (yesterday['Close'] < day_before['Close'] and              # Lower close AND
                     abs(yesterday['Close'] - yesterday['Low']) <              # Close near lows
                     abs(yesterday['High'] - yesterday['Low']) * 0.3)):       # Bottom 30% of range
                    self.envelope_data.loc[self.envelope_data.index[i], 'Day_Type'] = 'Buy Day'
                
                # Sell Day: Look for strength after weakness
                elif ((yesterday['High'] > day_before['High'] or              # Higher high OR
                      yesterday['Close'] > yesterday['Open']) and             # Up close AND
                     yesterday['Close'] > yesterday['Low'] + 
                     (yesterday['High'] - yesterday['Low']) * 0.7):           # Close in upper 30%
                    self.envelope_data.loc[self.envelope_data.index[i], 'Day_Type'] = 'Sell Day'
                
                # Sell Short Day: Look for failed strength
                elif (yesterday['High'] > day_before['High'] and              # Made new high BUT
                      yesterday['Close'] < yesterday['High'] -                # Failed to hold it
                      (yesterday['High'] - yesterday['Low']) * 0.5):          # Closed in lower half
                    self.envelope_data.loc[self.envelope_data.index[i], 'Day_Type'] = 'Sell Short Day'
                
                else:
                    self.envelope_data.loc[self.envelope_data.index[i], 'Day_Type'] = 'Undefined'
        
        # Calculate next day's envelopes
        if len(self.envelope_data) >= 4:  # Need at least 4 days of data for 3-day averages
            last_row = self.envelope_data.iloc[-1]
            
            # Calculate 3-day averages
            decline_avg = self.envelope_data['Decline_Number'].tail(3).mean()  # Yesterday's high minus today's low
            buy_under_avg = self.envelope_data['Buy_Under'].tail(3).mean()    # Yesterday's low minus today's low
            rally_avg = self.envelope_data['Rally_Number'].tail(3).mean()     # Today's high minus yesterday's low
            buy_high_avg = self.envelope_data['Buy_High'].tail(3).mean()      # Today's high minus yesterday's high
            
            # Buy Envelope (Support)
            # 1. Decline level: Today's high minus average decline
            decline_level = last_row['High'] - decline_avg
            # 2. Buy Under level: Today's low minus average buy under
            buy_under_level = last_row['Low'] - buy_under_avg
            # 3. Today's low
            todays_low = last_row['Low']
            # 4. Pivot Sell (resistance becomes support if broken)
            pivot_sell = last_row['Pivot_Sell']
            
            # Sell Envelope (Resistance)
            # 1. Rally level: Today's low plus average rally
            rally_level = last_row['Low'] + rally_avg
            # 2. Buy High level: Today's high plus average buy high
            buy_high_level = last_row['High'] + buy_high_avg
            # 3. Today's high
            todays_high = last_row['High']
            # 4. Pivot Buy (support becomes resistance if broken)
            pivot_buy = last_row['Pivot_Buy']
            
            # Update labels with day type context
            day_type = last_row.get('Day_Type', 'Undefined')
            self.decline_label['text'] = f"Decline Level: {decline_level:.2f}"
            self.buy_under_label['text'] = f"Buy Under Level: {buy_under_level:.2f}"
            self.todays_low_label['text'] = f"Today's Low: {todays_low:.2f}"
            
            self.rally_label['text'] = f"Rally Level: {rally_level:.2f}"
            self.buy_high_label['text'] = f"Buy High Level: {buy_high_level:.2f}"
            self.todays_high_label['text'] = f"Today's High: {todays_high:.2f}"
            
            # Add day type to tooltips
            if day_type == 'Buy Day':
                self.create_tooltip(self.buy_under_label, 
                    f"Buy Under Level: {buy_under_level:.2f}\nToday is identified as a Buy Day - "
                    "Look for buying opportunities near the Buy Under Level")
                
                # Add overbought/oversold guidance
                ob_os = last_row.get('OB_OS', 50)
                if ob_os <= 30:
                    self.create_tooltip(self.buy_under_label,
                        f"Buy Under Level: {buy_under_level:.2f}\n"
                        f"Oversold ({ob_os:.1f}%) - Strong buy signal for tomorrow")
                elif ob_os >= 70:
                    self.create_tooltip(self.buy_under_label,
                        f"Buy Under Level: {buy_under_level:.2f}\n"
                        f"Overbought ({ob_os:.1f}%) - Consider waiting or selling")
                
            elif day_type == 'Sell Day':
                self.create_tooltip(self.rally_label,
                    f"Rally Level: {rally_level:.2f}\nToday is identified as a Sell Day - "
                    "Look for selling opportunities near the Rally Level")
                
                # Add overbought/oversold guidance
                ob_os = last_row.get('OB_OS', 50)
                if ob_os >= 70:
                    self.create_tooltip(self.rally_label,
                        f"Rally Level: {rally_level:.2f}\n"
                        f"Overbought ({ob_os:.1f}%) - Strong sell signal for tomorrow")
                elif ob_os <= 30:
                    self.create_tooltip(self.rally_label,
                        f"Rally Level: {rally_level:.2f}\n"
                        f"Oversold ({ob_os:.1f}%) - Consider waiting or buying")
            
            # Update next day plan
            self.update_next_day_plan(day_type, last_row)

    def update_next_day_plan(self, day_type, last_row):
        """Generate trade plan based on the LSS mechanical day-trading system"""
        
        # Calculate key reference levels
        daily_range = last_row['High'] - last_row['Low']
        
        # Calculate envelope levels (Rule #4)
        buy_envelope_top = last_row['High'] + daily_range * 0.2
        buy_envelope_bottom = last_row['Low'] - daily_range * 0.2
        sell_envelope_top = last_row['High'] + daily_range * 0.2
        sell_envelope_bottom = last_row['Low'] - daily_range * 0.2
        
        if day_type == 'Buy Day':
            plan = (
                f"LSS MECHANICAL SYSTEM - DAY 1 (LOW DAY)\n\n"
                f"CYCLE POSITION: First day of 3-day cycle\n"
                f"MECHANICAL ENTRY RULES:\n"
                f"• Place buy orders at or slightly below {last_row['Low']:.2f}\n"
                f"• Do not chase market if level is missed\n"
                f"• Must enter in first 2 hours of trading\n\n"
                
                f"ENVELOPE LEVELS (Rule #4):\n"
                f"• Buy Envelope Top: {buy_envelope_top:.2f}\n"
                f"• Buy Envelope Bottom: {buy_envelope_bottom:.2f}\n"
                f"• Key Support Zone: {last_row['Low'] - daily_range*0.1:.2f} to {last_row['Low']:.2f}\n\n"
                
                f"MECHANICAL EXIT RULES:\n"
                f"• Initial Stop: Exactly at {last_row['Low'] - daily_range*0.15:.2f}\n"
                f"• Exit ALL positions by close (Rule #5)\n"
                f"• Move to breakeven when price hits {last_row['Low'] + daily_range*0.3:.2f}\n\n"
                
                f"REVERSAL RULES (Rule #7):\n"
                f"• If pattern fails (high made first), prepare for sell setup tomorrow\n"
                f"• If stopped out early, watch for reversal entry\n"
                f"• Do not add to losing trades after first 2 hours\n\n"
                
                f"CRITICAL REMINDERS:\n"
                f"• Place orders before price hits levels (Rule #3)\n"
                f"• Take losses quickly - good trades work immediately (Rule #5)\n"
                f"• Never hold losing positions overnight (Rule #5)\n"
            )
            
        elif day_type == 'Sell Day':
            plan = (
                f"LSS MECHANICAL SYSTEM - DAY 2 (SELL DAY)\n\n"
                f"CYCLE POSITION: Second day of 3-day cycle\n"
                f"MECHANICAL ENTRY RULES:\n"
                f"• Place sell orders at or slightly above {last_row['High']:.2f}\n"
                f"• Must enter in first 2 hours after open\n"
                f"• Do not chase market if level is missed\n\n"
                
                f"ENVELOPE LEVELS (Rule #4):\n"
                f"• Sell Envelope Top: {sell_envelope_top:.2f}\n"
                f"• Sell Envelope Bottom: {sell_envelope_bottom:.2f}\n"
                f"• Key Resistance Zone: {last_row['High']:.2f} to {last_row['High'] + daily_range*0.1:.2f}\n\n"
                
                f"MECHANICAL EXIT RULES:\n"
                f"• Initial Stop: Exactly at {last_row['High'] + daily_range*0.15:.2f}\n"
                f"• Exit ALL positions by close (Rule #5)\n"
                f"• Move to breakeven when price hits {last_row['High'] - daily_range*0.3:.2f}\n\n"
                
                f"REVERSAL RULES (Rule #7):\n"
                f"• If pattern fails (low made first), prepare for buy setup tomorrow\n"
                f"• If stopped out early, watch for reversal entry\n"
                f"• Do not add to losing trades after first 2 hours\n\n"
                
                f"CRITICAL REMINDERS:\n"
                f"• Place orders before price hits levels (Rule #3)\n"
                f"• Take losses quickly - good trades work immediately (Rule #5)\n"
                f"• Never hold positions overnight when cycle unclear\n"
            )
            
        elif day_type == 'Sell Short Day':
            plan = (
                f"LSS MECHANICAL SYSTEM - DAY 3 (SELLSHORT DAY)\n\n"
                f"CYCLE POSITION: Third day of 3-day cycle\n"
                f"MECHANICAL ENTRY RULES:\n"
                f"• Place short orders at failed rally near {last_row['High']:.2f}\n"
                f"• Must enter in first 2 hours of trading\n"
                f"• Do not chase market if level is missed\n\n"
                
                f"ENVELOPE LEVELS (Rule #4):\n"
                f"• Sell Envelope Top: {sell_envelope_top:.2f}\n"
                f"• Sell Envelope Bottom: {sell_envelope_bottom:.2f}\n"
                f"• Key Resistance Zone: {last_row['High'] - daily_range*0.1:.2f} to {last_row['High']:.2f}\n\n"
                
                f"MECHANICAL EXIT RULES:\n"
                f"• Initial Stop: Exactly at {last_row['High'] + daily_range*0.15:.2f}\n"
                f"• Exit ALL positions by close (Rule #5)\n"
                f"• Move to breakeven when price hits {last_row['High'] - daily_range*0.3:.2f}\n\n"
                
                f"REVERSAL RULES (Rule #7):\n"
                f"• If pattern fails, push cycle ahead one day\n"
                f"• If stopped out early, watch for reversal entry\n"
                f"• Cover shorts near close to prepare for new cycle\n\n"
                
                f"CRITICAL REMINDERS:\n"
                f"• Place orders before price hits levels (Rule #3)\n"
                f"• Take losses quickly - good trades work immediately (Rule #5)\n"
                f"• Never hold losing positions overnight (Rule #5)\n"
            )
            
        else:
            plan = (
                f"LSS MECHANICAL SYSTEM - CYCLE IDENTIFICATION\n\n"
                f"CURRENT STATUS: Awaiting clear cycle start\n"
                f"MECHANICAL RULES FOR CYCLE IDENTIFICATION:\n\n"
                
                f"ENTRY CRITERIA:\n"
                f"• Wait for clear low day pattern\n"
                f"• Must see early weakness followed by strength\n"
                f"• Do not force trades when cycle unclear\n\n"
                
                f"KEY REFERENCE LEVELS:\n"
                f"• Previous High: {last_row['High']:.2f}\n"
                f"• Previous Low: {last_row['Low']:.2f}\n"
                f"• Daily Range: {daily_range:.2f}\n\n"
                
                f"ENVELOPE LEVELS (Rule #4):\n"
                f"• Buy Envelope: {buy_envelope_bottom:.2f} to {buy_envelope_top:.2f}\n"
                f"• Sell Envelope: {sell_envelope_bottom:.2f} to {sell_envelope_top:.2f}\n\n"
                
                f"CRITICAL REMINDERS:\n"
                f"• Track cycle every day (Rule #1)\n"
                f"• Focus on single market (Rule #6)\n"
                f"• Wait for clear mechanical entry signal\n"
                f"• Never hold positions overnight when cycle unclear\n"
            )
        
        # Add Level 1 trade guidance to next day plan
        ob_os = last_row.get('OB_OS', 50)
        level1_buy = last_row['Level1_Buy']
        level1_sell = last_row['Level1_Sell']
        
        if ob_os <= 30:  # Oversold - Look for buys
            plan += f"\n\nLevel 1 Buy Setup: Watch for early dip to {level1_buy:.2f} (0.30 below open)"
        elif ob_os >= 70:  # Overbought - Look for sells
            plan += f"\n\nLevel 1 Sell Setup: Watch for early rally to {level1_sell:.2f} (0.30 above open)"
        else:
            plan += f"\n\nLevel 1 Setups:\n- Buy below {level1_buy:.2f}\n- Sell above {level1_sell:.2f}"
        
        self.plan_label['text'] = plan

    def update_table(self):
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        if self.envelope_data.empty:
            return
        
        # Fill table with data
        for index, row in self.envelope_data.iterrows():
            values = [
                index.strftime('%Y-%m-%d'),
                f"{row['Open']:.2f}",
                f"{row['High']:.2f}",
                f"{row['Low']:.2f}",
                f"{row['Close']:.2f}",
                f"{row.get('Rally_Number', 0):.2f}",
                f"{row.get('Decline_Number', 0):.2f}",
                f"{row.get('Buy_High', 0):.2f}",
                f"{row.get('Buy_Under', 0):.2f}",
                f"{row.get('Pivot_Buy', 0):.2f}",
                f"{row.get('Pivot_Sell', 0):.2f}",
                row.get('Day_Type', 'Undefined'),
                f"{row.get('OB_OS', 0):.2f}",
                f"{row.get('Level1_Buy', 0):.2f}",
                f"{row.get('Level1_Sell', 0):.2f}"
            ]
            self.tree.insert('', 'end', values=values)

def main():
    try:
        root = tk.Tk()
        root.geometry("1200x800")  # Set a reasonable initial window size
        app = TTTCalculator(root)
        root.mainloop()
    except Exception as e:
        print(f"Error starting application: {str(e)}")
        raise

if __name__ == '__main__':
    main()
