import streamlit as st
import uuid
from tempfile import NamedTemporaryFile
from tecla_cleaner import read_file, create_noisy_curve, clean_curve
from plot_utils import plot_noisy_curve_interactive
from streamlit_plotly_events import plotly_events
import os

os.environ["KALIEDO_SCOPE"] = "/tmp/kaleido"


st.set_page_config(page_title="TECLA Photon Cleaner")
st.title("🔭 TECLA Photon Cleaner")
st.write("Upload a `.fits` file to clean noisy photon bins and download the cleaned result.")


uploaded_file = st.file_uploader("📂 Upload a FITS file", type=["fits"], key=st.session_state.get("uploader_key", "default_uploader"))

if "uploaded_filename" not in st.session_state and not uploaded_file:
    st.info("Please upload a `.fits` file to start.")
    st.stop()


st.sidebar.header("⚙️ Settings")
bin_options = [2**i for i in range(7, 17)]
nt = st.sidebar.selectbox("Select number of bins (power of 2)", bin_options)

if uploaded_file:
    st.success(f"✅ File `{uploaded_file.name}` uploaded successfully.")
    st.warning("⚠️ Please select the number of bins from the sidebar **before clicking 'Create Curve'**.")
    st.info(f"📊 Number of bins selected: **{nt}**")

    if (
        "uploaded_filename" not in st.session_state or
        st.session_state.uploaded_filename != uploaded_file.name or
        "nt" not in st.session_state or
        st.session_state.nt != nt
    ):
        
        with NamedTemporaryFile(delete=False, suffix=".fits") as tmp:
            tmp.write(uploaded_file.read())
            tmp_fits_path = tmp.name

        glowcurvenoise = read_file(tmp_fits_path)

        st.session_state.uploaded_filename = uploaded_file.name
        st.session_state.nt = nt
        st.session_state.tmp_fits_path = tmp_fits_path
        st.session_state.glowcurvenoise = glowcurvenoise
        st.session_state.curve_data = None
        st.session_state.selected_points = []
        st.session_state.curve_created = False


if "uploaded_filename" in st.session_state:
    if not st.session_state.curve_created:
        if st.button("🎨 Create Curve"):
            with st.spinner("Generating curve..."):
                realcount, realgrid, arrbin, enbin, posXbin, posYbin, intertbin, num = create_noisy_curve(
                    st.session_state.glowcurvenoise,
                    st.session_state.nt
                )
                st.session_state.curve_data = {
                    "realcount": realcount,
                    "realgrid": realgrid,
                    "arrbin": arrbin,
                    "enbin": enbin,
                    "posXbin": posXbin,
                    "posYbin": posYbin,
                    "intertbin": intertbin,
                    "num": num,
                }
                st.session_state.curve_created = True
                st.success("📈 Curve created! Now select two bins.")

    if st.session_state.curve_created:
        data = st.session_state.curve_data
        realcount = data["realcount"]
        realgrid = data["realgrid"]
        num = data["num"]
        nt = st.session_state.nt

        st.write("Select exactly TWO bins from the curve below")
        st.markdown("🟢 Click once for the **start** and again for the **end** of the segment to be used.")

        fig = plot_noisy_curve_interactive(st.session_state.uploaded_filename, realcount, realgrid, num, nt)
        clicked_points = plotly_events(fig, click_event=True, override_height=500)

        if st.button("🔄 Reset"):
            st.session_state.selected_points = []

        if clicked_points:
            for pt in clicked_points:
                if len(st.session_state.selected_points) < 2:
                    st.session_state.selected_points.append(pt)
                else:
                    st.warning("⚠️ You already selected two points. Click 'Reset' to start over.")


        if len(st.session_state.selected_points) == 2:
            x1 = st.session_state.selected_points[0]['x']
            x2 = st.session_state.selected_points[1]['x']

            if x1 > x2:
                x1, x2 = x2, x1

            startG = next((k for k, v in realgrid.items() if v == x1), None)
            endG = next((k for k, v in realgrid.items() if v == x2), None)

            st.success(f"✅ Selected bins: from bin `{startG}` to bin `{endG}`")

            if st.button("🚀 Run TECLA Cleaning"):
                with st.spinner("Running cleaning..."):
                    glowcurvenoise = st.session_state.glowcurvenoise
                    realcount = st.session_state.curve_data["realcount"]
                    realgrid = st.session_state.curve_data["realgrid"]
                    num = st.session_state.curve_data["num"]
                    arrbin = st.session_state.curve_data["arrbin"]
                    enbin = st.session_state.curve_data["enbin"]
                    posXbin = st.session_state.curve_data["posXbin"]
                    posYbin = st.session_state.curve_data["posYbin"]
                    clean_curve_path, fig = clean_curve(st.session_state.uploaded_filename, glowcurvenoise, nt, realcount, realgrid, arrbin, enbin, posXbin, posYbin, num, startG, endG)
                    st.success("🧹 Cleaning completed!")
                    st.session_state["cleaned_path"] = clean_curve_path
                    st.session_state["plot"] = fig

            if "cleaned_path" in st.session_state and "plot" in st.session_state:
                name = st.session_state.uploaded_filename.split(".fits")[0]
                clean_curve_path = st.session_state["cleaned_path"]
                fig = st.session_state["plot"]
                st.plotly_chart(fig)
                st.download_button(
                    label="🖼️ Download coomparison plot",
                    data=fig.to_image(format="png"),
                    file_name=f"{name}_{nt}_TECLA.png",
                    mime="image/png",
                )
                
                with open(st.session_state["cleaned_path"], "rb") as f:
                    st.download_button(
                        label="⬇️ Download Cleaned FITS File",
                        data=f.read(),
                        file_name=os.path.basename(st.session_state["cleaned_path"]),
                        mime="application/fits",
                    )

                

            if st.sidebar.button("🔄 Reset ALL"):
                keys_to_clear = [
                    "uploaded_filename", "glowcurvenoise", "tmp_fits_path", "curve_data",
                    "selected_points", "curve_created", "cleaned_path", "plot", "nt", "uploader_key"
                ]
                for key in keys_to_clear:
                    if key in st.session_state:
                        del st.session_state[key]
                st.session_state["uploader_key"] = str(uuid.uuid4())

        else:
            st.info("ℹ️ Please select exactly TWO bins to proceed.")