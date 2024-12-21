import pandas as pd
from datetime import datetime, timedelta
import yfinance as yf
import mplfinance as mpf


def chart(Tick):

    hoy = datetime.now()
    ini = hoy - timedelta(days=720)
    print('inicio ', ini)

    # Add MACD as subplot
    def MACD(df, window_slow, window_fast, window_signal):
        macd = pd.DataFrame()
        macd['ema_12'] = df['Close'].ewm(span=window_slow, adjust=False).mean()
        macd['ema_26'] = df['Close'].ewm(span=window_fast, adjust=False).mean()

        macd['scr2'] = macd['ema_12'] - macd['ema_26']
        macd['matr'] = macd['scr2'].ewm(span=window_signal, adjust=False).mean()
        macd['hist'] = macd['scr2'] - macd['matr']

        macd['bar_positive'] = macd['hist'].map(lambda x: x if x > 0 else 0)
        macd['bar_negative'] = macd['hist'].map(lambda x: x if x < 0 else 0)

       #macd['macd'] = macd['ema_12'] - macd['ema_26']
       #macd['signal'] = macd['macd'].ewm(span=window_signal).mean()
       #macd['bar_positive'] = macd['hist'].map(lambda x: x if x > 0 else 0)
       #macd['bar_negative'] = macd['hist'].map(lambda x: x if x < 0 else 0)
        return macd


    titl = ' '

    datos = yf.download(Tick, start=ini, progress=False, interval='1wk' )

    macd = MACD(datos, 12, 26, 9)
    macd_plot = [mpf.make_addplot((macd['bar_positive']), color='blue', panel=1, type='bar'),
                 mpf.make_addplot((macd['bar_negative']), color='red',  panel=1, type='bar')
                #mpf.make_addplot(macd, fill_between=['bar_negative', 'bar_positive'], color='k', linestyle='-.', width=0.25, panel=1)
    ]
    mc = mpf.make_marketcolors(base_mpf_style='charles', up='green', down='red', volume='grey')
    st = mpf.make_mpf_style(base_mpl_style='dark_background', marketcolors=mc, y_on_right=True, edgecolor='grey')
    print(st)


    fig, axes = mpf.plot(
                        datos,
                        type='candle',
                        style=st,
                        volume=True,
                        mav=(144, 55, 21, 9),
                        figscale=0.9,
                        figratio=(10, 7),
                        axisoff=False,
                        addplot=macd_plot,
                        main_panel=0,
                        volume_panel=1,
                        num_panels=2,
                        fill_between=dict(y1=65.53, y2=100, alpha=0.08, color='lime')
                    )

