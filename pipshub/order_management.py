"""
Order Management System (OMS) for PipesHub Assignment
-----------------------------------------------------

Author: <Your Name>
Date: <Today's Date>

Description:
This Python module implements an order management system that receives orders, applies time window and throttling logic, supports modify/cancel in the queue, and logs responses with latency. No third-party libraries are used.

How to Run:
- Run this file directly with Python 3.8+.
- The test harness at the bottom demonstrates the system.

Assumptions:
- Orders and responses are simulated in the test harness.
- Persistent storage is a local file 'responses.log'.
- Time window and throttle values are hardcoded for demo but can be configured.

Design decisions and architecture are explained in comments and docstrings throughout the code.
"""

import threading
import time
import queue
import enum
from dataclasses import dataclass, field
from typing import Optional, Dict, List
import datetime

# --- Data Classes and Enums ---

@dataclass
class Logon:
    username: str
    password: str

@dataclass
class Logout:
    username: str

class RequestType(enum.Enum):
    Unknown = 0
    New = 1
    Modify = 2
    Cancel = 3

class ResponseType(enum.Enum):
    Unknown = 0
    Accept = 1
    Reject = 2

@dataclass
class OrderRequest:
    m_symbolId: int
    m_price: float
    m_qty: int
    m_side: str  # 'B' or 'S'
    m_orderId: int
    request_type: RequestType  # Added for Python version

@dataclass
class OrderResponse:
    m_orderId: int
    m_responseType: ResponseType

# --- Helper Classes ---

class TimeWindowManager:
    """
    Manages logon/logout and checks if current time is within allowed window.
    Customization: start_time and end_time are passed as datetime.time objects.
    """
    def __init__(self, start_time: datetime.time, end_time: datetime.time):
        self.start_time = start_time
        self.end_time = end_time
        self.logged_in = False
        self.lock = threading.Lock()

    def is_within_window(self) -> bool:
        now = datetime.datetime.now().time()
        # Handles window crossing midnight
        if self.start_time <= self.end_time:
            return self.start_time <= now < self.end_time
        else:
            return now >= self.start_time or now < self.end_time

    def check_and_update(self, logon_callback, logout_callback):
        """
        Call this periodically to handle logon/logout events.
        logon_callback and logout_callback are called when state changes.
        """
        with self.lock:
            in_window = self.is_within_window()
            if in_window and not self.logged_in:
                self.logged_in = True
                logon_callback()
            elif not in_window and self.logged_in:
                self.logged_in = False
                logout_callback()

    def is_logged_in(self) -> bool:
        with self.lock:
            return self.logged_in

class OrderThrottler:
    """
    Enforces per-second order sending limit.
    Customization: max_per_sec is passed in constructor.
    """
    def __init__(self, max_per_sec: int):
        self.max_per_sec = max_per_sec
        self.sent_this_sec = 0
        self.current_sec = int(time.time())
        self.lock = threading.Lock()

    def can_send(self) -> bool:
        with self.lock:
            now_sec = int(time.time())
            if now_sec != self.current_sec:
                self.current_sec = now_sec
                self.sent_this_sec = 0
            return self.sent_this_sec < self.max_per_sec

    def record_send(self):
        with self.lock:
            self.sent_this_sec += 1

    def time_until_next_sec(self) -> float:
        return 1.0 - (time.time() % 1.0)

class PersistentLogger:
    """
    Logs responses and latencies to a file.
    Customization: filename is passed in constructor.
    """
    def __init__(self, filename: str = 'responses.log'):
        self.filename = filename
        self.lock = threading.Lock()

    def log(self, order_id: int, response_type: ResponseType, latency_ms: float):
        with self.lock:
            with open(self.filename, 'a') as f:
                f.write(f"{datetime.datetime.now().isoformat()} | OrderID: {order_id} | Response: {response_type.name} | Latency(ms): {latency_ms:.2f}\n")

# --- Main Order Management Class ---

class OrderManagement:
    """
    Customization:
    - All parameters (username, password, time window, throttle, log file) are passed to constructor.
    - Thread-safe and portable. No external dependencies.
    """
    def __init__(self, username: str, password: str, start_time: datetime.time, end_time: datetime.time, max_orders_per_sec: int, log_filename: str = 'responses.log'):
        self.username = username
        self.password = password
        self.time_window = TimeWindowManager(start_time, end_time)
        self.throttler = OrderThrottler(max_orders_per_sec)
        self.logger = PersistentLogger(log_filename)
        self.order_queue = []  # List of (OrderRequest, enqueue_time)
        self.queue_lock = threading.Lock()
        self.sent_orders: Dict[int, float] = {}  # orderId -> send_time (epoch seconds)
        self.sent_lock = threading.Lock()
        self.stop_event = threading.Event()
        self.sender_thread = threading.Thread(target=self._send_loop, daemon=True)
        self.time_thread = threading.Thread(target=self._time_window_loop, daemon=True)
        self.sender_thread.start()
        self.time_thread.start()

    # --- Public API ---

    def onData(self, request: OrderRequest):
        """
        Receives order request from upstream system.
        Handles time window, throttling, and queue modify/cancel logic.
        """
        if not self.time_window.is_logged_in():
            print(f"Order {request.m_orderId} rejected: Not in allowed time window.")
            return
        with self.queue_lock:
            if request.request_type == RequestType.Modify:
                for idx, (queued_req, _) in enumerate(self.order_queue):
                    if queued_req.m_orderId == request.m_orderId:
                        # Copy price and qty from modify request
                        self.order_queue[idx][0].m_price = request.m_price
                        self.order_queue[idx][0].m_qty = request.m_qty
                        print(f"Order {request.m_orderId} modified in queue.")
                        return
                print(f"Modify request for {request.m_orderId} ignored: not in queue.")
                return
            elif request.request_type == RequestType.Cancel:
                for idx, (queued_req, _) in enumerate(self.order_queue):
                    if queued_req.m_orderId == request.m_orderId:
                        self.order_queue.pop(idx)
                        print(f"Order {request.m_orderId} cancelled from queue.")
                        return
                print(f"Cancel request for {request.m_orderId} ignored: not in queue.")
                return
            # New order: try to send or queue
            if self.throttler.can_send():
                self._send_order(request)
            else:
                self.order_queue.append([request, time.time()])
                print(f"Order {request.m_orderId} queued due to throttle.")

    def onData_response(self, response: OrderResponse):
        """
        Receives order response from exchange.
        Matches with sent order and logs latency.
        """
        with self.sent_lock:
            send_time = self.sent_orders.pop(response.m_orderId, None)
        if send_time is not None:
            latency_ms = (time.time() - send_time) * 1000.0
            self.logger.log(response.m_orderId, response.m_responseType, latency_ms)
            print(f"Response for {response.m_orderId}: {response.m_responseType.name}, Latency: {latency_ms:.2f} ms")
        else:
            print(f"Response for unknown order {response.m_orderId} received.")

    def send(self, request: OrderRequest):
        """
        Sends the request to exchange (simulated by sleeping and then calling onData_response).
        """
        # Simulate network/processing delay
        threading.Thread(target=self._simulate_exchange, args=(request,), daemon=True).start()

    def stop(self):
        self.stop_event.set()
        self.sender_thread.join(timeout=2)
        self.time_thread.join(timeout=2)

    # --- Internal Methods ---

    def _send_order(self, request: OrderRequest):
        self.throttler.record_send()
        with self.sent_lock:
            self.sent_orders[request.m_orderId] = time.time()
        self.send(request)
        print(f"Order {request.m_orderId} sent to exchange.")

    def _send_loop(self):
        while not self.stop_event.is_set():
            with self.queue_lock:
                while self.order_queue and self.throttler.can_send():
                    req, _ = self.order_queue.pop(0)
                    self._send_order(req)
            # Sleep until next second if throttled
            if not self.throttler.can_send():
                time.sleep(self.throttler.time_until_next_sec())
            else:
                time.sleep(0.01)

    def _time_window_loop(self):
        def logon():
            print(f"[LOGON] {self.username} at {datetime.datetime.now().time()}")
        def logout():
            print(f"[LOGOUT] {self.username} at {datetime.datetime.now().time()}")
        while not self.stop_event.is_set():
            self.time_window.check_and_update(logon, logout)
            time.sleep(0.5)

    def _simulate_exchange(self, request: OrderRequest):
        # Simulate exchange processing and response
        time.sleep(0.05)  # 50ms round-trip
        # For demo, accept all orders
        response = OrderResponse(m_orderId=request.m_orderId, m_responseType=ResponseType.Accept)
        self.onData_response(response)

# --- Test Harness ---

if __name__ == "__main__":
    # Customization: All parameters are easy to change here
    USERNAME = "testuser"
    PASSWORD = "testpass"
    START_TIME = (datetime.datetime.now() + datetime.timedelta(seconds=2)).time()  # Start 2s from now
    END_TIME = (datetime.datetime.now() + datetime.timedelta(seconds=12)).time()   # End 12s from now
    MAX_ORDERS_PER_SEC = 3
    LOG_FILENAME = "responses.log"

    oms = OrderManagement(USERNAME, PASSWORD, START_TIME, END_TIME, MAX_ORDERS_PER_SEC, LOG_FILENAME)

    def simulate_orders():
        # Wait for logon
        print("Waiting for logon window...")
        while not oms.time_window.is_logged_in():
            time.sleep(0.1)
        print("Sending orders...")
        # Send 5 new orders quickly (should throttle)
        for i in range(5):
            req = OrderRequest(
                m_symbolId=1,
                m_price=100.0 + i,
                m_qty=10 + i,
                m_side='B',
                m_orderId=1000 + i,
                request_type=RequestType.New
            )
            oms.onData(req)
            time.sleep(0.1)
        # Modify order 1001 in queue
        mod_req = OrderRequest(
            m_symbolId=1,
            m_price=105.5,
            m_qty=99,
            m_side='B',
            m_orderId=1001,
            request_type=RequestType.Modify
        )
        oms.onData(mod_req)
        # Cancel order 1002 in queue
        cancel_req = OrderRequest(
            m_symbolId=1,
            m_price=0,
            m_qty=0,
            m_side='B',
            m_orderId=1002,
            request_type=RequestType.Cancel
        )
        oms.onData(cancel_req)
        # Edge case: Modify an order not in queue
        mod_not_in_queue = OrderRequest(
            m_symbolId=1,
            m_price=111.1,
            m_qty=1,
            m_side='B',
            m_orderId=9999,
            request_type=RequestType.Modify
        )
        oms.onData(mod_not_in_queue)
        # Edge case: Cancel an order not in queue
        cancel_not_in_queue = OrderRequest(
            m_symbolId=1,
            m_price=0,
            m_qty=0,
            m_side='B',
            m_orderId=8888,
            request_type=RequestType.Cancel
        )
        oms.onData(cancel_not_in_queue)
        # Edge case: Multiple modifies before send
        mod1 = OrderRequest(
            m_symbolId=1,
            m_price=120.0,
            m_qty=50,
            m_side='B',
            m_orderId=1003,
            request_type=RequestType.Modify
        )
        mod2 = OrderRequest(
            m_symbolId=1,
            m_price=130.0,
            m_qty=60,
            m_side='B',
            m_orderId=1003,
            request_type=RequestType.Modify
        )
        oms.onData(mod1)
        oms.onData(mod2)
        # Edge case: Rapid burst of orders (should queue and throttle)
        for i in range(10):
            req = OrderRequest(
                m_symbolId=2,
                m_price=200.0 + i,
                m_qty=20 + i,
                m_side='S',
                m_orderId=2000 + i,
                request_type=RequestType.New
            )
            oms.onData(req)
        # Send an order outside the window (wait for logout)
        print("Waiting for logout window...")
        while oms.time_window.is_logged_in():
            time.sleep(0.1)
        late_req = OrderRequest(
            m_symbolId=1,
            m_price=300.0,
            m_qty=1,
            m_side='S',
            m_orderId=3000,
            request_type=RequestType.New
        )
        oms.onData(late_req)
        # --- Additional test scenarios ---
        print("\n--- Additional Test Scenarios ---")
        # 1. Order arriving exactly at the window boundary (should be accepted if within, rejected if after)
        print("Testing order at window boundary...")
        # Wait until just before logout
        while (datetime.datetime.now().time() < END_TIME and oms.time_window.is_logged_in()):
            time.sleep(0.05)
        # Try to send at the boundary
        boundary_order = OrderRequest(
            m_symbolId=3,
            m_price=123.45,
            m_qty=10,
            m_side='B',
            m_orderId=4000,
            request_type=RequestType.New
        )
        oms.onData(boundary_order)
        # 2. Multiple modify/cancel on the same order
        print("Testing multiple modify/cancel on same order...")
        test_order = OrderRequest(
            m_symbolId=4,
            m_price=50.0,
            m_qty=5,
            m_side='S',
            m_orderId=5000,
            request_type=RequestType.New
        )
        oms.onData(test_order)
        # Queue it by sending many at once
        for i in range(MAX_ORDERS_PER_SEC):
            oms.onData(OrderRequest(4, 51.0+i, 6+i, 'S', 5001+i, RequestType.New))
        # Modify it twice
        oms.onData(OrderRequest(4, 60.0, 7, 'S', 5000, RequestType.Modify))
        oms.onData(OrderRequest(4, 70.0, 8, 'S', 5000, RequestType.Modify))
        # Cancel it
        oms.onData(OrderRequest(4, 0, 0, 'S', 5000, RequestType.Cancel))
        # Try to modify after cancel
        oms.onData(OrderRequest(4, 80.0, 9, 'S', 5000, RequestType.Modify))
        # 3. Orders with duplicate IDs
        print("Testing duplicate order IDs...")
        dup_order1 = OrderRequest(5, 100.0, 10, 'B', 6000, RequestType.New)
        dup_order2 = OrderRequest(5, 200.0, 20, 'S', 6000, RequestType.New)
        oms.onData(dup_order1)
        oms.onData(dup_order2)
        # 4. Orders with invalid sides
        print("Testing invalid order sides...")
        invalid_side_order = OrderRequest(6, 100.0, 10, 'X', 7000, RequestType.New)
        oms.onData(invalid_side_order)
        # 5. Orders with zero/negative quantity or price
        print("Testing zero/negative quantity/price...")
        zero_qty_order = OrderRequest(7, 100.0, 0, 'B', 8000, RequestType.New)
        neg_qty_order = OrderRequest(7, 100.0, -5, 'B', 8001, RequestType.New)
        zero_price_order = OrderRequest(7, 0.0, 10, 'B', 8002, RequestType.New)
        neg_price_order = OrderRequest(7, -10.0, 10, 'B', 8003, RequestType.New)
        oms.onData(zero_qty_order)
        oms.onData(neg_qty_order)
        oms.onData(zero_price_order)
        oms.onData(neg_price_order)

    # Run simulation in a thread so OMS can process in background
    sim_thread = threading.Thread(target=simulate_orders)
    sim_thread.start()
    sim_thread.join()
    # Allow time for all responses
    time.sleep(2)
    oms.stop()
    print("Test complete. Check responses.log for output.") 