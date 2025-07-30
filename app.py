import streamlit as st
import os
import pandas as pd
import numpy as np
import random
from tempfile import NamedTemporaryFile
from astropy.io import fits
from astropy.table import Table
import matplotlib.pyplot as plt

dpi = 1000
n_iterations = 10**4


def convert_endian(df):
    for col in df.columns:
        dtype = df[col].dtype
        if dtype.byteorder == ">" and np.issubdtype(dtype, np.number):
            swapped = df[col].values.byteswap()
            df[col] = swapped.view(swapped.dtype.newbyteorder()).copy()
    return df


def plot_noisy_curve(filename, realcount, realgrid, num,nt):
    name = filename.split(".fits")[0]
    path = f"{name}_NOISY.png"
    y_original = [realcount[t] for t in range(0, num)]
    x_vals = [realgrid[t] for t in range(0, num)]

    plt.figure(figsize=(10, 6))
    plt.plot(x_vals, y_original, color="red", label="Original Count")
    plt.xlabel("Time (realgrid)")
    plt.ylabel("Number of Photons")
    plt.title(f"{filename} - N. Bins {nt}")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=dpi)
    plt.close()
    return path


def plot_or_vs_opt(filename, realcount, realgrid, num, newarrbin):
    name = filename.split(".fits")[0]
    path = f"{name}_TECLA.png"
    y_original = [realcount[t] for t in range(0, num)]
    y_new = [len(newarrbin[t]) for t in range(0, num)]
    x_vals = [realgrid[t] for t in range(0, num)]

    plt.figure(figsize=(10, 6))
    plt.plot(x_vals, y_original, color="red", label="Original Count")
    plt.plot(x_vals, y_new, color="blue", label="Optimized Count")
    plt.xlabel("Time (realgrid)")
    plt.ylabel("Number of Photons")
    plt.title(f"Comparison of Original vs Optimized Bin Counts – {filename}")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=dpi)
    plt.close()
    return path


def process_file(filename, df,nt):    
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

    noisy_path_img = plot_noisy_curve(filename, realcount, realgrid, num,nt)
    st.session_state["plot_path"] = noisy_path_img
    st.image(
        st.session_state["plot_path"],
        caption=f"Original curve - N. Bins {nt}",
        use_container_width=True,
    )

    startG, endG = (
        1,
        2000,
    )  # TODO pernmetetre all'utenet di selezionare la parte buona e non.
    startB, endB = 5300, 5800
    good = [time for t in range(startG, endG + 1) for time in arrbin.get(t, [])]
    bad = [time for t in range(startB, endB + 1) for time in arrbin.get(t, [])]

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

    st.write("🧹 Cleaning photon bins...")
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
                nG = random.randint(low, high)
                posj = random.sample(range(realcount[t]), nG)

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

        progress_bar.progress((t + 1) / num)

    status_text.text("✅ Cleaning complete.")

    bad = [time for t in range(startB, endB + 1) for time in newarrbin.get(t, [])]
    bad_set = set(bad)
    df["IS_NOISY"] = df["TIME"].apply(lambda t: 1 if t in bad_set else 0)

    t = Table.from_pandas(df)
    name = filename.replace(".fits", "")
    cleaned_path = f"{name}_TECLA.fits"
    t.write(cleaned_path, overwrite=True)

    plot_path = plot_or_vs_opt(filename, realcount, realgrid, num, newarrbin)
    return cleaned_path, plot_path


# === Streamlit UI ===
st.set_page_config(page_title="TECLA Photon Cleaner")
st.title("🔭 TECLA Photon Cleaner")
st.write(
    "Upload a `.fits` file to clean noisy photon bins and download the cleaned result."
)

uploaded_file = st.file_uploader("📂 Upload a FITS file", type=["fits"])

if uploaded_file:
    with NamedTemporaryFile(delete=False, suffix=".fits") as tmp_fits:
        tmp_fits.write(uploaded_file.read())
        tmp_fits_path = tmp_fits.name

    try:
        data = fits.getdata(tmp_fits_path, ext=1)
        df = pd.DataFrame(data)
        filename = os.path.basename(uploaded_file.name)
        df = convert_endian(df)

        st.success(f"✅ File `{filename}` uploaded successfully.")
        
        st.sidebar.header("⚙️ Settings")
        bin_options = [2**i for i in range(7, 17)]  # [128, 256, ..., 65536]
        nt = st.sidebar.selectbox("Select number of bins (power of 2)", bin_options)
        st.info(f"📊 Number of bins selected: **{nt}**")

        if st.button("🚀 Run TECLA Cleaning"):
            with st.spinner("Cleaning in progress..."):
                cleaned_path, plot_path = process_file(filename=filename, df=df, nt=nt)
                st.session_state["cleaned_path"] = cleaned_path
                st.session_state["plot_path"] = plot_path

    except Exception as e:
        st.error(f"❌ Error: {e}")

# Show results and download buttons
if "cleaned_path" in st.session_state and "plot_path" in st.session_state:
    st.success("✅ Cleaning complete!")

    with open(st.session_state["cleaned_path"], "rb") as f:
        st.download_button(
            label="⬇️ Download Cleaned FITS File",
            data=f.read(),
            file_name=os.path.basename(st.session_state["cleaned_path"]),
            mime="application/fits",
        )

    st.image(
        st.session_state["plot_path"],
        caption="Original vs Optimized Bin Counts",
        use_container_width=True,
    )

    with open(st.session_state["plot_path"], "rb") as f:
        st.download_button(
            label="⬇️ Download Comparison Plot",
            data=f.read(),
            file_name=os.path.basename(st.session_state["plot_path"]),
            mime="image/png",
        )

# Optional reset
if st.button("🔄 Reset"):
    st.session_state.pop("cleaned_path", None)
    st.session_state.pop("plot_path", None)
    st.rerun()
