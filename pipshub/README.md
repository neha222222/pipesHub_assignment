# Order Management System (OMS) for PipesHub Assignment

## Overview
This project implements a robust, portable Order Management System (OMS) in Python, as per the PipesHub assignment requirements. The OMS handles order intake, time window enforcement, per-second throttling, queue management (with modify/cancel), and persistent logging of order responses and latencies.

## Features
- **Configurable Trading Window:** Only sends orders to exchange within a specified time window (logon/logout automatic).
- **Order Throttling:** Limits the number of orders sent to the exchange per second; excess orders are queued.
- **Queue Management:** Supports modify and cancel requests for orders in the queue.
- **Persistent Logging:** Logs all order responses and round-trip latencies to a file (`responses.log`).
- **Thread-Safe:** Uses Python threading and locks for safe concurrent operation.
- **No Third-Party Libraries:** Only Python standard library is used.
- **Test Harness Included:** Demonstrates all features and edge cases.

## Configuration
All key parameters are set at the top of `order_management.py` in the `if __name__ == "__main__":` block:
- `USERNAME`, `PASSWORD`: Credentials for logon/logout simulation.
- `START_TIME`, `END_TIME`: Trading window (as `datetime.time`).
- `MAX_ORDERS_PER_SEC`: Throttle rate.
- `LOG_FILENAME`: Output log file.

## Usage
1. **Clone the repository:**
   ```bash
   git clone https://github.com/neha222222/pipesHub_assignment.git
   cd pipesHub_assignment/pipshub
   ```
2. **Run the OMS:**
   ```bash
   python order_management.py
   ```
3. **Check the log:**
   - See `responses.log` for persistent output of order responses and latencies.

## Design Decisions & Architecture
- **Time Window Management:**
  - Uses a dedicated thread to monitor the time window and trigger logon/logout events.
  - Orders outside the window are rejected immediately.
- **Order Throttling:**
  - Per-second counter resets every second; excess orders are queued.
- **Queue Modify/Cancel:**
  - Modify requests update price/qty of queued orders.
  - Cancel requests remove queued orders.
- **Threading:**
  - Separate threads for time window management and order sending ensure responsiveness.
- **Persistence:**
  - All responses and latencies are logged with timestamps for auditability.

## Assumptions
- Persistent storage is a simple log file (`responses.log`).
- No third-party libraries are used.
- The OMS is designed for clarity, extensibility, and easy testing.

## Test Instructions
The test harness in `order_management.py` demonstrates:
- Orders being accepted, queued, modified, cancelled, and rejected outside the window.
- Throttling in action (more orders than allowed per second).
- How to change all key parameters.

To run the tests:
```bash
python order_management.py
```

## Example Output
```
Waiting for logon window...
[LOGON] testuser at 12:34:56.789123
Sending orders...
Order 1000 sent to exchange.
Order 1001 sent to exchange.
Order 1002 sent to exchange.
Order 1003 queued due to throttle.
Order 1004 queued due to throttle.
Order 1001 modified in queue.
Order 1002 cancelled from queue.
...
[LOGOUT] testuser at 12:35:06.789123
Order 2000 rejected: Not in allowed time window.
Test complete. Check responses.log for output.
```

## How to Extend
- Add more sophisticated persistence (e.g., database) by replacing `PersistentLogger`.
- Integrate with real upstream/exchange systems by replacing the `send` and `onData_response` simulation.
- Add more test cases in the test harness as needed.

## License
This project is for assignment/demo purposes only. 