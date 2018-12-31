# Data science imports
from multiprocessing import Pool
import requests
import re
from bs4 import BeautifulSoup
from itertools import chain
from collections import Counter, defaultdict
from timeit import default_timer as timer
import pandas as pd
import numpy as np
import statsmodels.api as sm


from scipy import stats

# Interactive plotting
import plotly.plotly as py
import plotly.graph_objs as go
from plotly.offline import iplot
import cufflinks

cufflinks.go_offline()


def make_update_menu(base_title, article_annotations=None, response_annotations=None):
    """
    Make an updatemenu for interative plot

    :param base_title: string for title of plot

    :return updatemenus: a updatemenus object for adding to a layout
    """
    updatemenus = list(
        [
            dict(
                buttons=list(
                    [
                        dict(
                            label="both",
                            method="update",
                            args=[
                                dict(visible=[True, True]),
                                dict(
                                    title=base_title,
                                    annotations=[
                                        article_annotations,
                                        response_annotations,
                                    ],
                                ),
                            ],
                        ),
                        dict(
                            label="articles",
                            method="update",
                            args=[
                                dict(visible=[True, False]),
                                dict(
                                    title="Article " + base_title,
                                    annotations=[article_annotations],
                                ),
                            ],
                        ),
                        dict(
                            label="responses",
                            method="update",
                            args=[
                                dict(visible=[False, True]),
                                dict(
                                    title="Response " + base_title,
                                    annotations=[response_annotations],
                                ),
                            ],
                        ),
                    ]
                )
            )
        ]
    )
    return updatemenus


def make_hist(df, x, category=None):
    """
    Make an interactive histogram, optionally segmented by `category`

    :param df: dataframe of data
    :param x: string of column to use for plotting
    :param category: string representing column to segment by

    :return figure: a plotly histogram to show with iplot or plot
    """
    if category is not None:
        data = []
        for name, group in df.groupby(category):
            data.append(go.Histogram(dict(x=group[x], name=name)))
    else:
        data = [go.Histogram(dict(x=df[x]))]

    layout = go.Layout(
        yaxis=dict(title="Count"),
        xaxis=dict(title=x.replace('_', ' ').title()),
        title=f"{x.replace('_', ' ').title()} Distribution by {category.replace('_', ' ').title()}"
        if category
        else f"{x.replace('_', ' ').title()} Distribution",
    )

    figure = go.Figure(data=data, layout=layout)
    return figure


def make_cum_plot(df, y, category=None):
    """
    Make an interactive cumulative plot, optionally segmented by `category`

    :param df: dataframe of data, must have a `published_date` column
    :param y: string of column to use for plotting or list of two strings for double y axis
    :param category: string representing column to segment by

    :return figure: a plotly plot to show with iplot or plot
    """
    if category is not None:
        data = []
        for i, (name, group) in enumerate(df.groupby(category)):
            group.sort_values("published_date", inplace=True)
            data.append(
                go.Scatter(
                    x=group["published_date"],
                    y=group[y].cumsum(),
                    mode="lines+markers",
                    text=group["title"],
                    name=name,
                    marker=dict(size=10, opacity=0.8,
                                symbol=i + 2),
                )
            )
    else:
        df.sort_values("published_date", inplace=True)
        if len(y) == 2:
            data = [
                go.Scatter(
                    x=df["published_date"],
                    y=df[y[0]].cumsum(),
                    name=y[0].title(),
                    mode="lines+markers",
                    text=df["title"],
                    marker=dict(size=10, color='blue', opacity=0.6, line=dict(color='black'),
                                )),
                go.Scatter(
                    x=df["published_date"],
                    y=df[y[1]].cumsum(),
                    yaxis='y2',
                    name=y[1].title(),
                    mode="lines+markers",
                    text=df["title"],
                    marker=dict(size=10, color='red', opacity=0.6, line=dict(color='black'),
                                )),
            ]
        else:
            data = [
                go.Scatter(
                    x=df["published_date"],
                    y=df[y].cumsum(),
                    mode="lines+markers",
                    text=df["title"],
                    marker=dict(size=12, color='blue', opacity=0.6, line=dict(color='black'),
                                ),
                )
            ]
    if len(y) == 2:
        layout = go.Layout(
            xaxis=dict(title="Published Date", type="date"),
            yaxis=dict(title=y[0].title(), color='blue'),
            yaxis2=dict(title=y[1].title(), color='red',
                        overlaying='y', side='right'),
            font=dict(size=14),
            title=f"Cumulative {y[0].title()} and {y[1].title()}",
        )
    else:
        layout = go.Layout(
            xaxis=dict(title="Published Date", type="date"),
            yaxis=dict(title=y.replace('_', ' ').title()),
            font=dict(size=14),
            title=f"Cumulative {y.replace('_', ' ').title()} by {category.replace('_', ' ').title()}"
            if category is not None
            else f"Cumulative {y.replace('_', ' ').title()}",
        )

    figure = go.Figure(data=data, layout=layout)
    return figure


def make_scatter_plot(df, x, y, fits=None, xlog=False, ylog=False, category=None, scale=None, sizeref=2, annotations=None):
    """
    Make an interactive scatterplot, optionally segmented by `category`

    :param df: dataframe of data
    :param x: string of column to use for xaxis
    :param y: string of column to use for yaxis
    :param fits: list of strings of fits
    :param xlog: boolean for making a log xaxis
    :param ylog boolean for making a log yaxis
    :param category: string representing categorical column to segment by, this must be a categorical
    :param scale: string representing numerical column to size and color markers by, this must be numerical data
    :param sizeref: float or integer for setting the size of markers according to the scale, only used if scale is set
    :param annotations: text to display on the plot (dictionary)

    :return figure: a plotly plot to show with iplot or plot
    """
    if category is not None:
        title = f"{y.replace('_', ' ').title()} vs {x.replace('_', ' ').title()} by {category.replace('_', ' ').title()}"
        data = []
        for i, (name, group) in enumerate(df.groupby(category)):
            data.append(go.Scatter(x=group[x],
                                   y=group[y],
                                   mode='markers',
                                   text=group['title'],
                                   name=name,
                                   marker=dict(size=8, symbol=i + 2)))

    else:
        if scale is not None:
            title = f"{y.replace('_', ' ').title()} vs {x.replace('_', ' ').title()} Scaled by {scale.title()}"
            data = [go.Scatter(x=df[x],
                               y=df[y],
                               mode='markers',
                               text=df['title'], marker=dict(size=df[scale],
                                                             line=dict(color='black', width=0.5), sizemode='area', sizeref=sizeref, opacity=0.8,
                                                             colorscale='Viridis', color=df[scale], showscale=True, sizemin=2))]
        else:

            df.sort_values(x, inplace=True)
            title = f"{y.replace('_', ' ').title()} vs {x.replace('_', ' ').title()}"
            data = [go.Scatter(x=df[x],
                               y=df[y],
                               mode='markers',
                               text=df['title'], marker=dict(
                size=12, color='blue', opacity=0.8, line=dict(color='black')),
                name='observations')]
            if fits is not None:
                for fit in fits:
                    data.append(go.Scatter(x=df[x], y=df[fit],
                                           mode='lines+markers', marker=dict(size=8, opacity=0.6),
                                           line=dict(dash='dash'), name=fit))

                title += ' with Fit'
    layout = go.Layout(annotations=annotations,
                       xaxis=dict(title=x.replace('_', ' ').title() + (' (log scale)' if xlog else ''),
                                  type='log' if xlog else None),
                       yaxis=dict(title=y.replace('_', ' ').title() + (' (log scale)' if ylog else ''),
                                  type='log' if ylog else None),
                       font=dict(size=14),
                       title=title,
                       )

    figure = go.Figure(data=data, layout=layout)
    return figure


def make_poly_fits(df, x, y, degree=6):
    """
    Generate fits and make interactive plot with fits

    :param df: dataframe with data
    :param x: string representing x data column
    :param y: string representing y data column
    :param degree: integer degree of fits to go up to

    :return fit_stats: dataframe with information about fits
    :return figure: interactive plotly figure that can be shown with iplot or plot
    """

    # Don't want to alter original data frame
    df = df.copy()
    fit_list = []
    rmse = []
    fit_params = []

    # Make each fit
    for i in range(1, degree + 1):
        fit_name = f'fit degree = {i}'
        fit_list.append(fit_name)
        z, res, *rest = np.polyfit(df[x], df[y], i, full=True)
        fit_params.append(z)
        df.loc[:, fit_name] = np.poly1d(z)(df[x])
        rmse.append(np.sqrt(res[0]))

    fit_stats = pd.DataFrame(
        {'fit': fit_list, 'rmse': rmse, 'params': fit_params})
    figure = make_scatter_plot(df, x=x, y=y, fits=fit_list)
    return fit_stats, figure


def make_linear_regression(df, x, y, intercept_0):
    """
    Create a linear regression, either with the intercept set to 0 or
    the intercept allowed to be fitted

    :param df: dataframe with data
    :param x: string for the name of the column with x data
    :param y: string for the name of the column with y data
    :param intercept_0: boolean indicating whether to set the intercept to 0
    """

    if intercept_0:
        lin_reg = sm.OLS(df[y], df[x]).fit()
        df['fit_values'] = lin_reg.fittedvalues
        summary = lin_reg.summary()
        slope = float(lin_reg.params)
        equation = f"${y} = {slope:.2f} * {x.replace('_', ' ')}$"

    else:
        lin_reg = stats.linregress(df[x], df[y])
        intercept, slope = lin_reg.intercept, lin_reg.slope
        params = ['pvalue', 'rvalue', 'slope', 'intercept']
        values = []
        for p in params:
            values.append(getattr(lin_reg, p))
        summary = pd.DataFrame({'param': params, 'value': values})
        df['fit_values'] = df[x] * slope + intercept
        equation = f"${y} = {slope:.2f} * {x.replace('_', ' ')} + {intercept:.2f}$"

    annotations = [dict(x=0.75 * df[x].max(), y=0.9 * df[y].max(), showarrow=False,
                        text=equation,
                        font=dict(size=32))]
    figure = make_scatter_plot(
        df, x=x, y=y, fits=['fit_values'], annotations=annotations)
    return figure, summary


def make_iplot(data, x, y, base_title, time=False, eq_pos=(0.75, 0.25)):
    """
    Make an interactive plot. Adds a dropdown to separate articles from responses
    if there are responses in the data. If there is only articles (or only responses)
    adds a linear regression line.

    :param data: dataframe of entry data
    :param x: string for xaxis of plot
    :param y: sring for yaxis of plot
    :param base_title: string for title of plot
    :param time: boolean for whether the xaxis is a plot
    :param eq_pos: position of equation for linear regression

    :return figure: an interactive plotly object for display

    """

    # Extract the relevant data
    responses = data[data["response"] == "response"].copy()
    articles = data[data["response"] == "article"].copy()

    if not responses.empty:
        # Create scatterplot data, articles must be first for menu selection
        plot_data = [
            go.Scatter(
                x=articles[x],
                y=articles[y],
                mode="markers",
                name="articles",
                text=articles["title"],
                marker=dict(color="blue", size=12),
            ),
            go.Scatter(
                x=responses[x],
                y=responses[y],
                mode="markers",
                name="responses",
                marker=dict(color="green", size=12),
            ),
        ]

        if not time:
            annotations = {}
            for df, name in zip([articles, responses], ["articles", "responses"]):

                regression = stats.linregress(x=df[x], y=df[y])
                slope = regression.slope
                intercept = regression.intercept
                rvalue = regression.rvalue

                xi = np.array(range(int(df[x].min()), int(df[x].max())))

                line = xi * slope + intercept
                trace = go.Scatter(
                    x=xi,
                    y=line,
                    mode="lines",
                    marker=dict(color="blue" if name ==
                                "articles" else "green"),
                    line=dict(width=4, dash="longdash"),
                    name=f"{name} linear fit",
                )

                annotations[name] = dict(
                    x=max(xi) * eq_pos[0],
                    y=df[y].max() * eq_pos[1],
                    showarrow=False,
                    text=f"$R^2 = {rvalue:.2f}; Y = {slope:.2f}X + {intercept:.2f}$",
                    font=dict(size=16, color="blue" if name ==
                              "articles" else "green"),
                )

                plot_data.append(trace)

        # Make a layout with update menus
        layout = go.Layout(
            annotations=list(annotations.values()),
            height=600,
            width=900,
            title=base_title,
            xaxis=dict(
                title=x.replace('_', ' ').title(), tickfont=dict(size=14), titlefont=dict(size=16)
            ),
            yaxis=dict(
                title=y.replace('_', ' ').title(), tickfont=dict(size=14), titlefont=dict(size=16)
            ),
            updatemenus=make_update_menu(
                base_title, annotations["articles"], annotations["responses"]
            ),
        )

    # If there are only articles
    else:
        plot_data = [
            go.Scatter(
                x=data[x],
                y=data[y],
                mode="markers",
                name="observations",
                text=data["title"],
                marker=dict(color="blue", size=12),
            )
        ]

        regression = stats.linregress(x=data[x], y=data[y])
        slope = regression.slope
        intercept = regression.intercept
        rvalue = regression.rvalue

        xi = np.array(range(int(data[x].min()), int(data[x].max())))
        line = xi * slope + intercept
        trace = go.Scatter(
            x=xi,
            y=line,
            mode="lines",
            marker=dict(color="red"),
            line=dict(width=4, dash="longdash"),
            name="linear fit",
        )

        annotations = [
            dict(
                x=max(xi) * eq_pos[0],
                y=data[y].max() * eq_pos[1],
                showarrow=False,
                text=f"$R^2 = {rvalue:.2f}; Y = {slope:.2f}X + {intercept:.2f}$",
                font=dict(size=16),
            )
        ]

        plot_data.append(trace)

        layout = go.Layout(
            annotations=annotations,
            height=600,
            width=900,
            title=base_title,
            xaxis=dict(
                title=x.replace('_', ' ').title(), tickfont=dict(size=14), titlefont=dict(size=16)
            ),
            yaxis=dict(
                title=y.replace('_', ' ').title(), tickfont=dict(size=14), titlefont=dict(size=16)
            ),
        )

    # Add a rangeselector and rangeslider for a data xaxis
    if time:
        rangeselector = dict(
            buttons=list(
                [
                    dict(count=1, label="1m", step="month", stepmode="backward"),
                    dict(count=6, label="6m", step="month", stepmode="backward"),
                    dict(count=1, label="YTD", step="year", stepmode="todate"),
                    dict(count=1, label="1y", step="year", stepmode="backward"),
                    dict(step="all"),
                ]
            )
        )
        rangeslider = dict(visible=True)
        layout["xaxis"]["rangeselector"] = rangeselector
        layout["xaxis"]["rangeslider"] = rangeslider

        figure = go.Figure(data=plot_data, layout=layout)

        return figure

    # Return the figure
    figure = go.Figure(data=plot_data, layout=layout)

    return figure
