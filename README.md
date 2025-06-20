# Order Management System (OMS) 

## Introduction
Welcome! This is not just another assignment solution—this is a thoughtfully crafted, real-world-inspired Order Management System (OMS) in Python. Imagine you're running a busy trading desk: orders come in bursts, some need to be changed or cancelled, and you can only send so many per second. This OMS is your diligent assistant, handling all the chaos with calm, logic, and a dash of personality.

## What Does This OMS Do?
- **Keeps you honest:** Only sends orders during the allowed trading window (logon/logout is automatic).
- **Keeps you safe:** Never overloads the exchange—throttles order flow to a set rate.
- **Keeps you flexible:** Lets you change or cancel orders in the queue before they're sent.
- **Keeps you accountable:** Logs every response and round-trip latency for audit and analysis.
- **Keeps you sane:** Handles all the above with clear, thread-safe code and zero third-party dependencies.

## How It Works (Real-World Analogy)
Think of the OMS as a nightclub bouncer:
- The **time window** is the club's opening hours. If you show up too early or too late, you're not getting in.
- The **throttler** is the fire marshal: only so many people (orders) can go in per second.
- The **queue** is the line outside. If you want to change your mind (modify) or leave (cancel) before you get in, you can.
- The **logger** is the security camera, recording every entry and exit with a timestamp.

## Features 
- **Configurable Trading Window:** Set your own open/close times.
- **Order Throttling:** No more than X orders per second—no exceptions!
- **Queue Management:** Modify or cancel queued orders before they're sent.
- **Persistent Logging:** Every response and latency is written to `responses.log`.
- **Thread-Safe:** Handles multiple things at once, just like a good multitasker.
- **No Third-Party Libraries:** Pure Python, pure joy.
- **Test Harness:** Try out all the features with built-in tests.

## Configuration
Edit the top of `order_management.py` in the `if __name__ == "__main__":` block:
- `USERNAME`, `PASSWORD`: For logon/logout simulation.
- `START_TIME`, `END_TIME`: Trading window (as `datetime.time`).
- `MAX_ORDERS_PER_SEC`: Throttle rate.
- `LOG_FILENAME`: Output log file.

## Quickstart
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
   - See `responses.log` for output.

## Design Decisions & Trade-offs
- **Threading:** Separate threads for time window and order sending. This keeps the system responsive, but means you need to be careful with locks.
- **Queue as List:** Simple, easy to modify/cancel, but not the most efficient for huge queues. For real-world scale, a more advanced data structure could be used.
- **File Logging:** Simple and portable. For production, swap in a database or message queue.
- **No External Libraries:** Makes it easy to run anywhere, but means we hand-coded some things (like thread safety) that libraries might handle for us.

## FAQ
**Q: Can I use this in production?**
A: This is a demo/assignment, but the design is extensible for real-world use with a few tweaks (see below).

**Q: How do I change the trading window or throttle?**
A: Edit the variables at the top of `order_management.py`.

**Q: What if I want to use a database?**
A: Replace the `PersistentLogger` class with your own implementation.

**Q: How do I add more tests?**
A: Add more scenarios in the `simulate_orders()` function in `order_management.py`.

## How to Extend or Contribute
- **Add new order types** (e.g., market, limit, stop): Extend the `OrderRequest` and logic in `OrderManagement`.
- **Integrate with real systems:** Replace the `send` and `onData_response` simulation with real network calls.
- **Improve performance:** Use more advanced data structures or async IO for high-frequency trading.
- **Open a pull request:** Fork the repo, make your changes, and submit a PR!

## Author Notes
This code was written with care, clarity, and a bit of fun. If you spot a bug or have an idea, open an issue or reach out. Happy coding!

## Troubleshooting
- **Orders not being sent?** Check your time window and throttle settings.
- **Log file missing?** Make sure you have write permissions in the directory.
- **Weird threading issues?** Try running with fewer test orders or add more debug prints.

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
Modify request for 9999 ignored: not in queue.
Cancel request for 8888 ignored: not in queue.
Response for 1000: Accept, Latency: 50.12 ms
...
[LOGOUT] testuser at 12:35:06.789123
Order 3000 rejected: Not in allowed time window.
Test complete. Check responses.log for output.
```
