import plotly.graph_objects as go
from plotly.graph_objects import Figure, Scatter


def plot_noisy_curve_interactive(filename, realcount, realgrid, num, nt):
    name = filename.split(".fits")[0]
    x = [realgrid[t] for t in range(num)]
    y = [realcount[t] for t in range(num)]

    fig = Figure()
    fig.add_trace(
        Scatter(
            x=x,
            y=y,
            mode="lines+markers",
            line=dict(color="red"),  
            marker=dict(color="red"), 
        )
    )
    fig.update_layout(
        title=f"{name} Noisy - N. Bins {nt}",
        xaxis_title="Time",
        yaxis_title="Photon Count",
    )
    return fig


def plot_or_vs_opt(filename, realcount, realgrid, num, newarrbin, nt):
    name = filename.split(".fits")[0]
    y_original = [realcount[t] for t in range(num)]
    y_new = [len(newarrbin[t]) for t in range(num)]
    x_vals = [realgrid[t] for t in range(num)]

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=x_vals,
            y=y_original,
            mode="lines+markers",
            name="Original Count",
            line=dict(color="red"),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=x_vals,
            y=y_new,
            mode="lines+markers",
            name="Optimized Count",
            line=dict(color="lightblue"),
        )
    )

    fig.update_layout(
        title=f"Comparison of Original vs Optimized Bin Counts – {name} N. Bins {nt}",
        xaxis_title="Time",
        yaxis_title="Number of Photons",
        legend=dict(x=0.01, y=0.99),
        margin=dict(l=40, r=40, t=60, b=40),
        template="simple_white",
    )

    return fig
