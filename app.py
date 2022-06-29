import streamlit as st
import altair as alt
import requests
import pandas as pd
import os
import io
import datetime

# Get API key from environment variable
APIKEY = os.environ.get('AlphaVantageKey')

# Input box for stock ticker symbol
st.text_input("Symbol", key="symbol")
symbol = st.session_state.symbol

# Side bar contains selection boxes for the starting year and end year,
# as well as a radio buttom for the chart type.
thisYear = datetime.datetime.today().year
startYear = st.sidebar.selectbox(
    'Start Year',
    range(thisYear, thisYear -20 - 1, -1)
)
endYear = st.sidebar.selectbox(
    'End Year',
    range(thisYear, thisYear -20 - 1, -1)
)
plotType = st.sidebar.radio(
    "Type of Chart",
    ('Line', 'Candlestick')
)

# For line plots, select which of Open/High/Low/Close will be plotted.
if plotType == 'Line':
    ohlc = st.multiselect(
        'Open, High, Low, Close',
        ['Open', 'High', 'Low', 'Close']
    )
else:
    ohlc = ['Open', 'High', 'Low', 'Close']

URL = f'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&outputsize=full&datatype=csv&apikey={APIKEY}'

# Function for getting the data from the URL, unless the stock symbol is unknown or if too many API calls have been made.
@st.cache(suppress_st_warning=True)
def getDataFrame(URL):
    req = requests.get(URL)
    text = req.content.decode()
    if '{\n    "Error Message": "Invalid API call' == text[:40]:
        st.write('Invalid symbol')
        st.stop()
    if text[:125] == '{\n    "Note": "Thank you for using Alpha Vantage! Our standard API call frequency is 5 calls per minute and 500 calls per day':
        st.write('Sorry, too many API calls to Alpha Vantage have been made. Try again later...')
        st.stop()
    with io.StringIO(text) as f:
        df = pd.read_csv(f)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.rename(columns = {
        'timestamp' : 'Date',
        'open' : 'Open',
        'low' : 'Low',
        'high' : 'High',
        'close' : 'Close',
        'volume' : 'Volume'
    })
    return df

# Validate inputs
if symbol == '':
    st.write('Input a symbol.')
    st.stop()
if startYear > endYear:
    st.write('"Start Year" must be less than or equal to "End Year".')
    st.stop()
if len(ohlc) == 0:
    st.write('Please Open, High, Low, and/or Close.')
    st.stop()

# Get the data and filter according to start year and end year
df = getDataFrame(URL)
df = df[(df['Date'] >= pd.to_datetime(str(startYear))) & (df['Date'] < pd.to_datetime(str(endYear + 1)))]
df = df[['Date'] + ohlc]

# Mouseover vertical line selection object
selection = alt.selection_single(
    fields = ['Date'],
    nearest = True,
    on = 'mouseover',
    empty = 'none',
    clear = 'mouseout'
)

base = alt.Chart(df).encode(x = alt.X('Date:T', title = 'Date'))

if plotType == 'Line':
    lines = base.mark_line().transform_fold(
        ohlc, as_ = ['metric', 'price']
    ).encode(
        y = alt.Y('price:Q', scale = alt.Scale(zero = False), title = 'Price ($)'),
        color = alt.Color('metric:N', legend = alt.Legend(title = None))
    )
    graphic = lines
elif plotType == 'Candlestick':
    base = base.encode(
        color = alt.condition("datum.Open < datum.Close", alt.value('green'), alt.value('red'))
    )
    bars = base.mark_bar().encode(
        y = alt.Y('Open:Q'),
        y2 = alt.Y2('Close:Q')
    )
    wicks = base.mark_rule().encode(
        y = alt.Y('Low:Q', title = 'Price ($)', scale = alt.Scale(zero = False)),
        y2 = alt.Y2('High:Q')
    )
    graphic = bars + wicks

# Define the mouseover vertical line
rule = base.mark_rule().encode(
    opacity = alt.condition(selection, alt.value(0.25), alt.value(0)),
    tooltip = (
        [alt.Tooltip('Date', type = 'temporal')] +
        [alt.Tooltip(o, type = 'quantitative') for o in ohlc]
    )
).add_selection(selection)

chart = (graphic + rule).interactive()

st.altair_chart(chart, use_container_width = True)