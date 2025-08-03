import numpy as np
import streamlit as st
import pandas as pd
from astropy.io import fits
from astropy.table import Table
from plot_utils import plot_or_vs_opt
from random import randint, sample
import os
import socket



def running_on_cloud():
    hostname = socket.gethostname()
    return "streamlit" in hostname.lower() or "cloud" in hostname.lower() or "app" in os.environ.get("HOME", "")


def convert_endian(df):
    for col in df.columns:
        dtype = df[col].dtype
        if dtype.byteorder == ">" and np.issubdtype(dtype, np.number):
            swapped = df[col].values.byteswap()
            df[col] = swapped.view(swapped.dtype.newbyteorder()).copy()
    return df


def read_file(path):
    data = fits.getdata(path, ext=1)
    df = pd.DataFrame(data)
    df = convert_endian(df)
    return df


def create_noisy_curve(df, nt):
    times = df["TIME"].sort_values().values
    step = (np.max(times) - np.min(times)) / nt
    grid = np.array([np.min(times) + step * i for i in range(nt + 1)])

    occurrenceel = {t: 0 for t in range(nt + 3)}
    arrivalel = {t: [] for t in range(nt + 3)}
    energyel = {t: [] for t in range(nt + 3)}
    posXel = {t: [] for t in range(nt + 3)}
    posYel = {t: [] for t in range(nt + 3)}

    st.write("Creating curve...")
    progress_bar = st.progress(0)
    status_text = st.empty()
    for i, (_, row) in enumerate(df.iterrows()):
        t = int((row["TIME"] - np.min(times)) / step)
        occurrenceel[t] += 1
        arrivalel[t].append(row["TIME"])
        posXel[t].append(row["RAWX"])
        posYel[t].append(row["RAWY"])
        energyel[t].append(row["PI"])
        progress_bar.progress((i + 1) / len(df))

    count = {t: occurrenceel[t] for t in range(0, nt)}
    realgrid = {}
    realcount = {}
    arrbin = {}
    enbin = {}
    posXbin = {}
    posYbin = {}
    intertbin = {}
    num = 0

    for t in range(0, nt):
        if count[t] > 2:
            realgrid[num] = grid[t]
            realcount[num] = count[t]
            arrbin[num] = arrivalel[t]
            enbin[num] = energyel[t]
            posXbin[num] = posXel[t]
            posYbin[num] = posYel[t]
            intertimes = np.diff(sorted(arrbin[num]))
            padded = np.pad(intertimes, (realcount[num] - len(intertimes), 0))
            intertbin[num] = padded
            num += 1

    status_text.text("✅ Curve created!")
    return realcount, realgrid, arrbin, enbin, posXbin, posYbin, intertbin, num


def clean_curve(
        filename,
        df,
        nt,
        realcount,
        realgrid,
        arrbin,
        enbin,
        posXbin,
        posYbin,
        num,
        startG,
        endG,
    ):
    
    if running_on_cloud():
        n_iterations = 1000
    else:
        n_iterations = 10000
    good = [time for t in range(startG, endG + 1) for time in arrbin.get(t, [])]

    intertbinG = np.diff(good)
    goodtM = np.median(
        [realcount[t] for t in range(startG, endG + 1) if t in realcount]
    )
    goodtSD = np.std([realcount[t] for t in range(startG, endG + 1) if t in realcount])
    interval = [np.floor(goodtM - goodtSD), np.floor(goodtM + 2 * goodtSD)]

    goodE = np.array([e for t in range(startG, endG + 1) for e in enbin.get(t, [])])
    goodElow = goodE[(500 < goodE) & (goodE < 2000)]
    goodEhigh = goodE[(2000 < goodE) & (goodE < 10000)]

    target = np.median(intertbinG)
    targetElow = np.median(goodElow)
    targetEhigh = np.median(goodEhigh)

    newrealcount, newarrbin, newenbin, newposXbin, newposYbin = {}, {}, {}, {}, {}

    st.write(f"🧹 Cleaning photon bins, N. Iterations = {n_iterations})")
    progress_bar = st.progress(0)
    status_text = st.empty()

    for t in range(0, num):
        status_text.text(f"Cleaning bin {t + 1} of {num}")
        newrealcount[t] = realcount[t]
        newarrbin[t] = arrbin[t]
        newenbin[t] = enbin[t]
        newposXbin[t] = posXbin[t]
        newposYbin[t] = posYbin[t]

        if realcount[t] > goodtM + 2 * goodtSD:
            best_score = float("inf")
            best_sample = None

            for _ in range(n_iterations):
                low = max(1, int(interval[0]))
                high = min(realcount[t], int(interval[1]))
                if high < low:
                    break
                nG = randint(low, high)
                posj = sample(range(realcount[t]), nG)

                arr_sample = [arrbin[t][j] for j in posj]
                en_sample = [enbin[t][j] for j in posj]
                arr_sorted = sorted(arr_sample)
                intert = np.diff(arr_sorted)
                intert = np.pad(intert, (nG - len(intert), 0))
                metric = np.mean(intert)

                en_low = [e for e in en_sample if 500 < e <= 2000]
                en_high = [e for e in en_sample if 2000 < e <= 10000]
                metricElow = np.median(en_low) if en_low else 999999
                metricEhigh = np.median(en_high) if en_high else 999999

                glowcurvetemp = [newrealcount[i] for i in range(t)] + [nG]
                metrictime = np.mean(glowcurvetemp)
                targettime = np.var(glowcurvetemp) if len(glowcurvetemp) > 1 else 0

                score = np.sqrt(
                    (abs(metric - target)) ** 2
                    + (abs(metricElow - targetElow)) ** 2
                    + (abs(metricEhigh - targetEhigh)) ** 2
                    + (abs(metrictime - targettime)) ** 2
                )
                if score < best_score:
                    best_score = score
                    best_sample = {
                        "count": nG,
                        "arr": arr_sample,
                        "en": en_sample,
                        "posX": [posXbin[t][j] for j in posj],
                        "posY": [posYbin[t][j] for j in posj],
                    }

            if best_sample:
                newrealcount[t] = best_sample["count"]
                newarrbin[t] = best_sample["arr"]
                newenbin[t] = best_sample["en"]
                newposXbin[t] = best_sample["posX"]
                newposYbin[t] = best_sample["posY"]
        progress_bar.progress(min((t + 1) / num, 1.0))

    status_text.text("✅ Cleaning complete.")

    kept_times = set()
    for t in range(num):
        kept_times.update(newarrbin[t])

    df["IS_NOISY"] = df["TIME"].apply(lambda x: 0 if x in kept_times else 1)

    t = Table.from_pandas(df)
    name = filename.replace(".fits", "")
    cleaned_path = f"{name}_TECLA.fits"
    t.write(cleaned_path, overwrite=True)
    fig = plot_or_vs_opt(filename, realcount, realgrid, num, newarrbin, nt)
    return cleaned_path, fig
