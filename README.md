# AERO-TACTIC: UAV Diagnostic Terminal

A post-flight crash diagnostics tool for UAVs running the PX4 flight controller. Upload a flight log and the system shows power and motor metrics within seconds and generates a structured expert conclusion about the cause of the incident.

## Problem

Investigating a drone crash by hand means digging through binary ULog files: finding the voltage sag, spotting ESC desync or a motor failure, and correlating them in time. This is slow and requires an experienced engineer. AERO-TACTIC automates the first stage of that analysis.

## Features

- Upload logs in `.ulg` and `.csv` formats
- Automatic ULog to CSV conversion (`battery_status` and `actuator_outputs` topics)
- Fast C++ extractor for battery voltage metrics and motor control signals
- Detection of voltage sag and anomalies in actuator behavior
- Expert report from Gemini with a fixed structure: key conclusion, power assessment, actuator assessment, technical recommendations
- Battery voltage plot over flight time
- In-session analysis history and Markdown report export

## Architecture

```
Streamlit UI (app.py)
   |  .ulg -> CSV (pyulog)
   v
MCP client --stdio--> MCP server (server.py)
                          |
                          v
                   C++ module ulog_parser (pybind11)
                          |
                          v
               voltage and motor metrics
   |
   v
Gemini API -> expert report -> UI + .md export
```

The `check_px4_voltage` and `check_px4_motors` tools are exposed through the Model Context Protocol, so they can be plugged into any MCP-compatible AI client, not only this UI.

## Tech Stack

Python, C++, pybind11, Streamlit, Model Context Protocol (MCP), Google Gemini API, pyulog, pandas

## Project Structure

| File | Purpose |
|---|---|
| `app.py` | Streamlit interface, `.ulg` conversion, Gemini call |
| `server.py` | MCP server with the analysis tools |
| `ulog_parser.*.pyd` | Compiled C++ module (Windows, Python 3.12) |
| `test_run.py` | Direct test of the C++ module |
| `requirements.txt` | Python dependencies |

## Getting Started

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
set GEMINI_API_KEY=your_key
streamlit run app.py
```

Optional: the `GEMINI_MODEL` environment variable (defaults to `gemini-2.5-flash`).

Open the app in your browser, upload a log through the sidebar and click the analysis button.

## Limitations

- The `ulog_parser` module is built for Windows x64 and Python 3.12 only. Other platforms require recompiling it from the C++ source.
- The AI conclusion is an aid and does not replace review by an engineer.
