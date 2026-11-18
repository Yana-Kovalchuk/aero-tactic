import ulog_parser

print("Starting direct test of the C++ module...")
try:
    voltage_res = ulog_parser.parse_battery_csv("temp_csv/crash_battery_status_0.csv")
    print("Voltage result:\n", voltage_res)

    motors_res = ulog_parser.analyze_motors_csv("temp_csv/crash_actuator_outputs_0.csv")
    print("Motors result:\n", motors_res)
except Exception as e:
    print("An error occurred:", e)
