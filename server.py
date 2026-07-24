from flask import Flask, jsonify, request
from flask_cors import CORS
import yfinance as yf
from groq import Groq
import json
import os
import concurrent.futures # Για παράλληλη εκτέλεση (Ταχύτητα!)
import time 
from dotenv import load_dotenv # Χρειάζεται: pip install python-dotenv

# IMPORT ΤΗ ΔΙΚΗ ΣΟΥ ΛΙΣΤΑ (Βεβαιώσου ότι το αρχείο market_symbols.py υπάρχει)
from market_symbols import TOP_100

# Φόρτωση περιβάλλοντος από το .env αρχείο
load_dotenv()

app = Flask(__name__)
CORS(app)

def calculate_quarterly_growth(symbol):
    try:
        stock = yf.Ticker(symbol)
        # Αντλούμε τον πίνακα με τα τρίμηνα
        q_financials = stock.quarterly_financials
        
        if q_financials.empty:
             return "N/A", "N/A"

        rev_growth = "N/A"
        earn_growth = "N/A"

        # --- 1. Υπολογισμός Revenue Growth (Έσοδα) ---
        if "Total Revenue" in q_financials.index:
            revenues = q_financials.loc["Total Revenue"].dropna()
            # Το yfinance επιστρέφει τα τρίμηνα από το πιο πρόσφατο (index 0) στο παλαιότερο
            if len(revenues) >= 2:
                current_rev = revenues.iloc[0]
                prev_rev = revenues.iloc[1]
                
                if prev_rev != 0:
                    growth = ((current_rev - prev_rev) / abs(prev_rev)) * 100
                    # Προσθέτουμε + αν είναι θετικό, για να φαίνεται ωραίο στο AI
                    rev_growth = f"+{growth:.2f}%" if growth > 0 else f"{growth:.2f}%"

        # --- 2. Υπολογισμός Earnings Growth (Καθαρά Κέρδη) ---
        if "Net Income" in q_financials.index:
            incomes = q_financials.loc["Net Income"].dropna()
            if len(incomes) >= 2:
                current_inc = incomes.iloc[0]
                prev_inc = incomes.iloc[1]
                
                if prev_inc != 0:
                    growth = ((current_inc - prev_inc) / abs(prev_inc)) * 100
                    earn_growth = f"+{growth:.2f}%" if growth > 0 else f"{growth:.2f}%"

        return rev_growth, earn_growth

    except Exception as e:
        print(f"Error calculating growth for {symbol}: {e}")
        return "N/A", "N/A"

# --- 1. ΡΥΘΜΙΣΗ GROQ ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = None

if not GROQ_API_KEY:
    print("--> ⚠️ WARNING: Δεν βρέθηκε GROQ_API_KEY στο .env file!")
else:
    try:
        groq_client = Groq(api_key=GROQ_API_KEY)
        print("--> Groq AI Configured Successfully!")
    except Exception as e:
        print(f"--> Warning: Groq AI setup failed: {e}")

# --- ΒΟΗΘΗΤΙΚΗ ΣΥΝΑΡΤΗΣΗ ΓΙΑ THREADING ---
# Αυτή η συνάρτηση τρέχει παράλληλα για κάθε μετοχή
def fetch_stock_data(symbol):
    try:
        clean_symbol = symbol.strip().upper()
        # Χρησιμοποιούμε Ticker για μεμονωμένη κλήση (μέσα στο thread)
        stock = yf.Ticker(clean_symbol)
        
        # Το fast_info είναι πολύ πιο γρήγορο από το .info
        price = stock.fast_info.last_price
        prev_close = stock.fast_info.previous_close
        market_cap = stock.fast_info.market_cap
        
        # Αν η yahoo δεν δώσει τιμή, αγνοούμε τη μετοχή
        if price is None or prev_close is None:
            return None
            
        change = ((price - prev_close) / prev_close) * 100
        
        return {
            "symbol": clean_symbol, 
            "name": clean_symbol, # Το fast_info δεν έχει πάντα το longName, κρατάμε το σύμβολο για ταχύτητα
            "price": price, 
            "changesPercentage": change, 
            "marketCap": market_cap
        }
    except Exception:
        # Αν αποτύχει μία μετοχή, δεν "σκάει" η εφαρμογή, απλά επιστρέφει None
        return None

# --- ENDPOINT 1: ΤΙΜΕΣ (Parallel Optimized) ---
@app.route('/api/quote', methods=['GET'])
def get_quote():
    start_time = time.time()
    symbols_arg = request.args.get('symbols', '')
    
    if symbols_arg:
        # Search: Ο χρήστης ψάχνει κάτι συγκεκριμένο
        symbols_list = symbols_arg.split(',')
    else:
        # Homepage: Παίρνουμε τις πρώτες 30 από τη λίστα
        symbols_list = TOP_100[:30]

    print(f"--> Ζητάω τιμές για {len(symbols_list)} μετοχές (Parallel)...")
    
    data = []
    
    # Χρήση ThreadPoolExecutor για ταυτόχρονη λήψη δεδομένων
    # max_workers=10 σημαίνει ότι ανοίγει 10 "κανάλια" ταυτόχρονα
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(fetch_stock_data, symbols_list))

    # Φιλτράρουμε τα αποτελέσματα για να βγάλουμε τα None (errors)
    data = [r for r in results if r is not None]
        
    # Ταξινόμηση με βάση το Market Cap
    data.sort(key=lambda x: x['marketCap'] or 0, reverse=True)
    
    print(f"--> Ολοκληρώθηκε σε {time.time() - start_time:.2f} seconds")
    return jsonify(data)

# --- ENDPOINT 2: DEEP ANALYSIS (AI) ---
@app.route('/api/analyze', methods=['POST'])
def analyze_stock():
    try:
        req_data = request.json
        symbol = req_data.get('symbol')
        print(f"--> Deep Analyzing {symbol} with Groq...")

        ticker = yf.Ticker(symbol)
        info = ticker.info
        hist = ticker.history(period="3mo")

        def get_safe(key, default="N/A"):
            val = info.get(key)
            return val if val is not None else default

        # ΝΕΑ βοηθητική συνάρτηση για τα ποσοστά
        def format_margin(val):
            if isinstance(val, (int, float)):
                return f"{round(val * 100, 2)}%"
            return "N/A"

        def format_market_cap(val):
            if isinstance(val, (int, float)):
                if val >= 1_000_000_000_000:
                    return f"${round(val / 1_000_000_000_000, 2)}T"
                elif val >= 1_000_000_000:
                    return f"${round(val / 1_000_000_000, 2)}B"
                elif val >= 1_000_000:
                    return f"${round(val / 1_000_000, 2)}M"
                else:
                    return f"${val:,.2f}"
            return "N/A"

        peg_ratio = get_safe('pegRatio', None)
        if peg_ratio is None or peg_ratio == "N/A":
            fwd_pe = info.get('forwardPE')
            growth = info.get('earningsGrowth')
            if fwd_pe and growth and growth > 0:
                peg_ratio = round(fwd_pe / (growth * 100), 2)
            else:
                peg_ratio = "N/A"

        officers = info.get('companyOfficers', [])
        ceo_name = "N/A"
        for officer in officers:
            title = officer.get('title', '').lower()
            if 'ceo' in title or 'chief executive' in title:
                ceo_name = officer.get('name', 'N/A')
                break

        raw_news = ticker.news
        latest_news = []
        for item in (raw_news or [])[:3]:
            news_title = item.get('title') or item.get('content', {}).get('title')
            if news_title:
                latest_news.append(news_title)
        if not latest_news:
            latest_news = ["No recent news found."]

        current_price = get_safe('currentPrice')
        raw_trend = hist['Close'].tail(5).tolist() if not hist.empty else []
        recent_trend = [float(round(x, 2)) for x in raw_trend]

        # Υπολογίζουμε τα δικά μας ποσοστά ανάπτυξης (QoQ)
        calculated_rev_growth, calculated_earn_growth = calculate_quarterly_growth(symbol)

        financial_data = {
            "Company Info": {
                "Symbol": symbol,
                "Name": get_safe('shortName', symbol),
                "Sector": get_safe('sector', 'Unknown'),
                "Industry": get_safe('industry', 'Unknown'),
                "Country": get_safe('country', 'Unknown'),
                "Employees": get_safe('fullTimeEmployees'),
                "CEO": ceo_name,
                "Description": get_safe('longBusinessSummary', '')[:800],
            },
            "Market Data": {
                "Price": current_price,
                "Market Cap": format_market_cap(get_safe('marketCap', None)),
            },
            "Recent News": latest_news,
            "Valuation": {
                "P/E (Trailing)": get_safe('trailingPE'),
                "F. P/E (Forward)": get_safe('forwardPE'),
                "PEG": peg_ratio,
                "P/S (Price to Sales)": get_safe('priceToSalesTrailing12Months'),
                "P/B (Price to Book)": get_safe('priceToBook'),
            },
            "Profitability & Margins": {
                "Gross Margin": get_safe('grossMargins'),
                "Operating Margin": get_safe('operatingMargins'),
                "Profit Margin": get_safe('profitMargins'),
            },
            "Cash Flow & Debt": {
                "Free Cash Flow": get_safe('freeCashflow'),
                "Total Cash": get_safe('totalCash'),
                "Total Debt": get_safe('totalDebt'),
            },
            "Growth & Quarterly Performance": {
                "Revenue Growth (Annual)": get_safe('revenueGrowth'),
                "Earnings Growth (Annual)": get_safe('earningsGrowth'),
                "Quarterly Revenue Growth (QoQ)": calculated_rev_growth,
                "Quarterly Earnings Growth (QoQ)": calculated_earn_growth,
            },
            "Analysts": {
                "Target Price": get_safe('targetMeanPrice'),
                "Recommendation": get_safe('recommendationKey'),
            },
            "Technical": {
                "200 Day MA": get_safe('twoHundredDayAverage'),
                "5-Day Trend": recent_trend,
            },
        }

        prompt = f"""
        Act as a Senior Investment Analyst. You are given the following comprehensive financial data for **{symbol}**.

        DATA (JSON):
        {json.dumps(financial_data, ensure_ascii=False, indent=2)}

        Write a professional investment report in English. 
        CRITICAL INSTRUCTIONS:
        1. You MUST include all 8 sections listed below. DO NOT skip any section.
        2. You MUST use Markdown headers (##) and bullet points (*) exactly as formatted below.
        3. Use the provided JSON data to answer the guiding questions. If a field is "N/A" or missing, explicitly state "Data not available" and move on. NEVER invent numbers.

        # Investment Analysis: {symbol}

        ## 1) Initial Overview
        * **Description:** What exactly does the company do? (Use Sector, Industry, Country, and Description).
        * **Key Stats:** Present Market Cap, Current Price, and Employee count.

        ## 2) Financial Presentation & Momentum
        * **Quarterly Performance:** Comment on Quarterly Revenue and Earnings Growth. Is there acceleration or deceleration?
        * **Liquidity & Debt:** Compare Total Cash vs Total Debt. Is Free Cash Flow positive? What does this mean for its financial safety?
        * **Recent Catalysts:** Based on recent news headlines, what is the current narrative around the company?
        * **Trend & Moving Average:** Where is the price relative to the 200-day MA, and how has it moved over the last 5 days?

        ## 3) Future Estimates by Analysts
        * **Target & Recommendation:** What is the mean price target, implied upside/downside, and overall analyst recommendation?

        ## 4) The 5-Year Estimates (Expected ROI)
        * **Growth Projections:** Based on historical growth rates and current valuation (PEG Ratio), estimate the stock's 3-5 year potential. Does it show strong future ROI capabilities?

        ## 5) Stock Valuation Metrics Check
        (For each metric below, state the number then explain "The Reality" - what it means in practice):
        * **P/E & Forward P/E:** Compare both. Is the stock getting cheaper on a forward basis?
        * **P/S & P/B:** Are these multiples reasonable for the industry?
        * **Profit Margins:** Present and comment on Gross Margin, Operating Margin, and Profit Margin. Are they healthy?

        ## 6) Value Comparison (Competition & Industry)
        * **Peers:** Identify the 2-3 main global competitors in its sector. What is this company's comparative advantage over them?

        ## 7) Management & Leadership
        * **Leadership:** Who is the CEO? Briefly comment on the importance of stable leadership for this company.

        ## 8) Economic Moat & Competitive Advantage
        * **Create & Capture Value:** How does the company create value in its industry?
        * **Moat Sources:** What competitive advantages might it have (e.g., Network Effects, Switching Costs, Scale)?

        ---
        **# 🎯 FINAL VERDICT & RECOMMENDATION: [BUY / HOLD / SELL]**
        Based on all of the above (Valuation, Cash Flows, Momentum, and Competitive Advantage), give a final, rigorous 3-4 sentence justification for your recommendation.
        """

        if not groq_client:
            return jsonify({"error": "Groq API key not configured"}), 500

        chat_completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a rigorous, professional Senior Investment Analyst. You must strictly output the requested Markdown structure. Never skip sections. Never fabricate financial data.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.2,
        )

        return jsonify({"analysis": chat_completion.choices[0].message.content})

    except Exception as e:
        print(f"AI Error: {e}")
        return jsonify({"error": str(e)}), 500

# --- ENDPOINT 3: ΛΕΠΤΟΜΕΡΕΙΕΣ ΜΕΤΟΧΗΣ ΓΙΑ SIDEBAR ---
@app.route('/api/details', methods=['GET'])
def get_details():
    symbol = request.args.get('symbol')
    if not symbol:
        return jsonify({"error": "No symbol provided"}), 400
        
    print(f"--> Φέρνω λεπτομέρειες για {symbol}...")
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        details = {
            "symbol": symbol,
            "name": info.get('longName', symbol),
            "sector": info.get('sector', 'N/A'),
            "industry": info.get('industry', 'N/A'),
            "description": info.get('longBusinessSummary', 'No description available.'),
            "price": info.get('currentPrice', 0),
            "currency": info.get('currency', 'USD'),
            "dayHigh": info.get('dayHigh', 0),
            "dayLow": info.get('dayLow', 0),
            "fiftyTwoWeekHigh": info.get('fiftyTwoWeekHigh', 0),
            "fiftyTwoWeekLow": info.get('fiftyTwoWeekLow', 0),
            "volume": info.get('volume', 0),
            "marketCap": info.get('marketCap', 0),
            "peRatio": info.get('trailingPE', 'N/A'),
            "dividendYield": info.get('dividendYield', 'N/A'),
            "beta": info.get('beta', 'N/A')
        }
        return jsonify(details)
    except Exception as e:
        print(f"Details Error: {e}")
        return jsonify({"error": str(e)}), 500
    
    # --- ENDPOINT 4: ΙΣΤΟΡΙΚΟ ΤΙΜΩΝ ΓΙΑ CHART ---
@app.route('/api/history', methods=['GET'])
def get_history():
    symbol = request.args.get('symbol')
    period = request.args.get('period', '1mo') # default 1 μήνας
    
    # Επιτρεπτά periods για το yfinance: 1d,5d,1mo,3mo,6mo,1y,2y,5y,10y,ytd,max
    valid_periods = ['1mo', '3mo', '6mo', '1y', 'max']
    if period not in valid_periods:
        period = '1mo'

    try:
        ticker = yf.Ticker(symbol)
        # Παίρνουμε ιστορικό (μόνο κλείσιμο μας νοιάζει για απλό chart)
        hist = ticker.history(period=period)
        
        # Μετατροπή σε λίστα
        data = []
        for date, row in hist.iterrows():
            data.append({
                # Μορφή ημερομηνίας: "Jan 05" ή "2023-01-05"
                "date": date.strftime('%d %b'), 
                "price": round(row['Close'], 2)
            })
            
        return jsonify(data)
    except Exception as e:
        print(f"History Error: {e}")
        return jsonify({"error": str(e)}), 500
    
@app.route('/api/financials', methods=['GET'])
def get_financials():
    symbol = request.args.get('symbol')
    if not symbol:
        return jsonify({"error": "No symbol provided"}), 400

    print(f"--> Fetching financials for {symbol}...")

    try:
        ticker = yf.Ticker(symbol)
        
        # 1. Παίρνουμε τα δεδομένα
        financials = ticker.financials
        
        # 2. ΑΝΤΙΜΕΤΩΠΙΣΗ ΤΟΥ ERROR "NaN": 
        # Λέμε στο Pandas να αντικαταστήσει όλα τα NaN με 0.
        # Αυτό λύνει το JSON error απευθείας.
        financials = financials.fillna(0)

        if financials.empty:
            return jsonify([])

        data = []
        cols = financials.columns

        for date in cols:
            try:
                year = date.strftime('%Y')
                
                # Helper για να βρούμε τη σωστή γραμμή (Revenue/Income)
                # Ψάχνουμε αν υπάρχει κάποιο από αυτά τα ονόματα στο index
                def get_row_value(df, possible_names, col_date):
                    for name in possible_names:
                        if name in df.index:
                            return df.loc[name, col_date]
                    return 0

                # Λίστες με πιθανά ονόματα (βάσει yfinance docs & common keys)
                revenue_keys = ['Total Revenue', 'Operating Revenue', 'Revenue', 'Total Net Sales']
                income_keys = ['Net Income', 'Net Income Common Stockholders', 'Net Income From Continuing Ops']

                # Παίρνουμε τις τιμές (τώρα είμαστε σίγουροι ότι δεν είναι NaN)
                revenue = get_row_value(financials, revenue_keys, date)
                income = get_row_value(financials, income_keys, date)

                data.append({
                    "year": year,
                    "revenue": float(revenue), # Το κάνουμε float για σιγουριά
                    "netIncome": float(income)
                })

            except Exception as e:
                print(f"Error parsing year {date}: {e}")
                continue
        
        # Ταξινόμηση ώστε να πηγαίνει από παλιά -> νέα (για το γράφημα)
        data.sort(key=lambda x: x['year'])
        
        return jsonify(data)

    except Exception as e:
        print(f"Financials Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)