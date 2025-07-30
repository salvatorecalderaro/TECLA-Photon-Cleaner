import streamlit as st
import os
from tempfile import NamedTemporaryFile
from tecla_cleaner import read_file, clean_curve




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
        filename = os.path.basename(uploaded_file.name)
        glowcurvenoise = read_file(tmp_fits_path)

        st.success(f"✅ File `{filename}` uploaded successfully.")

        st.sidebar.header("⚙️ Settings")
        bin_options = [2**i for i in range(7, 17)]  # [128, 256, ..., 65536]
        nt = st.sidebar.selectbox("Select number of bins (power of 2)", bin_options)
        st.info(f"📊 Number of bins selected: **{nt}**")

        if st.button("🚀 Run TECLA Cleaning"):
            with st.spinner("Cleaning in progress..."):
                cleaned_path, plot_path = clean_curve(filename=filename, df=glowcurvenoise, nt=nt)
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
