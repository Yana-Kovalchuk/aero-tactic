import os

import ulog_parser
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("PX4 Flight Analyzer")


@mcp.tool()
def check_px4_voltage(log_path: str) -> str:
    """Checks battery voltage and sag using the C++ parser."""
    if not os.path.exists(log_path):
        return f"Error: File '{log_path}' not found."

    try:
        result = ulog_parser.parse_battery_csv(log_path)
        return f"Voltage analysis result:\n{result}"
    except Exception as e:
        return f"Error running the C++ voltage parser: {str(e)}"


@mcp.tool()
def check_px4_motors(log_path: str) -> str:
    """Analyzes motor behavior and control signals."""
    if not os.path.exists(log_path):
        return f"Error: File '{log_path}' not found."

    try:
        result = ulog_parser.analyze_motors_csv(log_path)
        return f"Motor analysis result:\n{result}"
    except Exception as e:
        return f"Error running the C++ motor parser: {str(e)}"


if __name__ == "__main__":
    mcp.run()
