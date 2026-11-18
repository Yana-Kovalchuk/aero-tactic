import asyncio
import os
import sys

import pandas as pd
import streamlit as st
from google import genai
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

st.set_page_config(page_title="AERO-TACTIC HUD", layout="wide")

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
LOGS_DIR = "logs"
CSV_DIR = "temp_csv"

os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(CSV_DIR, exist_ok=True)

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    st.error("The GEMINI_API_KEY environment variable is not set.")
    st.stop()

client = genai.Client(api_key=api_key)

if "history" not in st.session_state:
    st.session_state["history"] = []


def convert_ulog_to_csv(ulg_path):
    from pyulog import ULog

    stem = os.path.splitext(os.path.basename(ulg_path))[0]
    ulog = ULog(ulg_path)
    result = {}
    for topic, key in (("battery_status", "battery"), ("actuator_outputs", "motors")):
        datasets = [d for d in ulog.data_list if d.name == topic]
        if not datasets:
            raise ValueError(f"The log has no '{topic}' topic.")
        csv_path = os.path.join(CSV_DIR, f"{stem}_{topic}_0.csv")
        pd.DataFrame(datasets[0].data).to_csv(csv_path, index=False)
        result[key] = csv_path
    return result


async def run_mcp_investigation(battery_path, motors_path):
    server_params = StdioServerParameters(command=sys.executable, args=["server.py"])

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            voltage_res = await session.call_tool(
                "check_px4_voltage", arguments={"log_path": battery_path}
            )
            motors_res = await session.call_tool(
                "check_px4_motors", arguments={"log_path": motors_path}
            )

            return voltage_res.content[0].text, motors_res.content[0].text


def generate_expert_report(voltage_data, motors_data):
    prompt = f"""You are the lead analyst engineer for unmanned aerial systems (UAS). Your task is to perform an expert post-flight diagnosis of a drone incident (crash) on a PX4 flight controller.

Analyze the telemetry data provided (extracted from ULog logs) and produce a structured tactical report.

TELEMETRY INPUT:
1. Power system (battery voltage): {voltage_data}
2. Control system (motor status and PWM signals): {motors_data}

ANALYSIS ALGORITHM:
1. Assess the power state: check for deep voltage sag under load. Compare the minimum voltage against acceptable thresholds. If the record count is 0, report an instantaneous critical power loss (blackout/brownout).
2. Assess the actuators: identify anomalies in control signals, signs of ESC desync, or a complete failure of one of the motors.
3. Find the correlation: determine whether the voltage sag could have caused the motors to stop, or whether a motor jam/overload caused the voltage drop.

OUTPUT FORMAT (follow this structure strictly):
* KEY CONCLUSION: [One sentence: the main cause of the incident (power failure, ESC/motor hardware fault, external factor)].
* POWER ASSESSMENT: [Analysis of the supplied voltage metrics].
* ACTUATOR ASSESSMENT: [Analysis of motor behavior].
* TECHNICAL RECOMMENDATIONS: [Short list of actions for the repair crew, e.g. "Inspect the XT60 power connector"].

Response style: strict, military-technical, concise. Write strictly to the point, with no greetings or filler phrases."""

    response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
    return response.text


st.title("AERO-TACTIC: UAV Diagnostic Terminal")
st.markdown("---")

with st.sidebar:
    st.header("DATA CONTROL")
    uploaded_file = st.file_uploader("Upload a log (.csv / .ulg)", type=["csv", "ulg"])

    st.markdown("---")
    st.header("ANALYSIS HISTORY")
    if not st.session_state["history"]:
        st.write("History is empty.")
    else:
        for idx, report in enumerate(st.session_state["history"]):
            with st.expander(f"Report #{idx + 1}: {report['filename']}"):
                st.write(report["ai_conclusion"])

if uploaded_file is not None:
    safe_name = os.path.basename(uploaded_file.name)
    file_path = os.path.join(LOGS_DIR, safe_name)

    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    st.success(f"File {safe_name} uploaded successfully.")

    if st.button("▶ START TACTICAL ANALYSIS"):
        with st.spinner("Running the C++ extractor and generating the AI conclusion..."):
            try:
                if safe_name.lower().endswith(".ulg"):
                    csv_paths = convert_ulog_to_csv(file_path)
                    battery_path = csv_paths["battery"]
                    motors_path = csv_paths["motors"]
                else:
                    battery_path = file_path
                    motors_path = file_path

                voltage_data, motors_data = asyncio.run(
                    run_mcp_investigation(battery_path, motors_path)
                )

                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("Power metrics (C++)")
                    st.text(voltage_data)
                with col2:
                    st.subheader("Motor metrics (C++)")
                    st.text(motors_data)

                st.subheader("EXPERT CONCLUSION (AI)")
                ai_report = generate_expert_report(voltage_data, motors_data)
                st.write(ai_report)

                st.subheader("VOLTAGE DROP DYNAMICS")
                try:
                    df = pd.read_csv(battery_path)

                    if "timestamp" in df.columns and "voltage_v" in df.columns:
                        df["time_sec"] = (df["timestamp"] - df["timestamp"].iloc[0]) / 1e6
                        st.line_chart(data=df, x="time_sec", y="voltage_v", height=350)
                    else:
                        st.warning("The uploaded file has no 'voltage_v' data to plot.")
                except Exception as e:
                    st.error(f"Plot error: {e}")

                st.session_state["history"].append(
                    {
                        "filename": safe_name,
                        "voltage": voltage_data,
                        "motors": motors_data,
                        "ai_conclusion": ai_report,
                    }
                )

                md_content = f"# TACTICAL REPORT ({safe_name})\n\n"
                md_content += f"## RAW METRICS\n**Power:**\n{voltage_data}\n\n**Motors:**\n{motors_data}\n\n"
                md_content += f"## EXPERT CONCLUSION\n{ai_report}"

                st.download_button(
                    label="⬇ DOWNLOAD REPORT (.md)",
                    data=md_content,
                    file_name=f"tactic_report_{safe_name}.md",
                    mime="text/markdown",
                )

            except Exception as e:
                st.error(f"Critical failure during analysis: {str(e)}")
else:
    st.info("Waiting for telemetry input. Upload a file in the sidebar to begin.")
