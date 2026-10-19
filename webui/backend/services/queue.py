"""Hàng đợi chấm bài, chống quá tải khi nhiều người gửi cùng lúc.

Một lượt đi qua ba trạng thái:
    reserve()  -> giữ chỗ TRƯỚC khi nhận dữ liệu tải lên; hàng đầy thì từ chối ngay
    enqueue()  -> tải lên xong, vào hàng chờ (FIFO)
    turns()    -> chờ tới lượt, mỗi lần hàng dịch chuyển báo vị trí và thời gian ước tính
    release()  -> xong, lỗi hoặc người dùng đóng tab: nhả chỗ cho người sau
Tối đa `workers` lượt chạy song song và `max_waiting` lượt đang tải lên / đang chờ, nên RAM và
số luồng dùng cho chấm bài luôn có giới hạn. Mỗi tài khoản chỉ có một lượt trong hàng.

Mọi hàm chạy trên event loop của asyncio (một luồng) nên không cần khoá.
"""
import asyncio
import math
import time
from collections import deque


class QueueRejected(Exception):
    """Không nhận lượt mới; thông điệp hiển thị thẳng cho người dùng."""

    def __init__(self, message, status, retry_after=None):
        super().__init__(message)
        self.status = status
        self.retry_after = retry_after


class Ticket:
    __slots__ = ("user_id", "ready", "started_at")

    def __init__(self, user_id):
        self.user_id = user_id
        self.ready = asyncio.Event()
        self.started_at = None


class AnalysisQueue:
    def __init__(self, workers, max_waiting, seconds_per_job=3.0):
        self.workers = max(1, int(workers))
        self.max_waiting = max(1, int(max_waiting))
        self.seconds_per_job = seconds_per_job  # trung bình trượt, cập nhật sau mỗi lượt
        self._reserved = set()     # đang tải lên
        self._waiting = deque()    # đã tải lên, chờ tới lượt
        self._running = 0
        self._users = set()
        self._moved = asyncio.Event()

    # ------------------------------------------------------------------
    def stats(self):
        return {
            "workers": self.workers,
            "running": self._running,
            "waiting": len(self._waiting) + len(self._reserved),
            "max_waiting": self.max_waiting,
            "seconds_per_job": round(self.seconds_per_job, 1),
        }

    def eta(self, ahead):
        """Số giây ước tính tới khi lượt có `ahead` lượt chờ phía trước được chạy."""
        backlog = self._running + ahead - self.workers + 1
        return max(0, math.ceil(backlog * self.seconds_per_job / self.workers))

    def position(self, ticket):
        """1 = đứng đầu hàng chờ; 0 = đang chạy hoặc chưa vào hàng."""
        try:
            return self._waiting.index(ticket) + 1
        except ValueError:
            return 0

    # ------------------------------------------------------------------
    def reserve(self, user_id):
        if user_id in self._users:
            raise QueueRejected("Bạn đang có một lượt chấm chưa xong. Đợi lượt đó có kết quả rồi gửi tiếp.", 409)
        pending = len(self._waiting) + len(self._reserved)
        if pending >= self.max_waiting:
            wait = max(5, self.eta(pending))
            raise QueueRejected(f"Máy chủ đang bận, hàng chờ đã đầy. Thử lại sau khoảng {wait} giây.",
                                503, retry_after=wait)
        ticket = Ticket(user_id)
        self._users.add(user_id)
        self._reserved.add(ticket)
        return ticket

    def enqueue(self, ticket):
        self._reserved.discard(ticket)
        self._waiting.append(ticket)
        self._dispatch()

    async def turns(self, ticket):
        """Sinh (vị trí, giây ước tính) cho tới khi tới lượt; không sinh gì nếu chạy được ngay."""
        while not ticket.ready.is_set():
            moved = self._moved  # lấy trước khi yield để không lỡ lần dịch chuyển xảy ra trong lúc gửi
            pos = self.position(ticket)
            yield pos, self.eta(pos - 1)
            await moved.wait()

    def release(self, ticket, completed=False):
        """Gọi đúng một lần cho mỗi lượt, ở bất kỳ trạng thái nào."""
        self._users.discard(ticket.user_id)
        if ticket.ready.is_set():
            self._running -= 1
            if completed:
                elapsed = time.perf_counter() - ticket.started_at
                self.seconds_per_job = 0.8 * self.seconds_per_job + 0.2 * elapsed
        elif ticket in self._reserved:
            self._reserved.discard(ticket)
        else:
            self._waiting.remove(ticket)
        self._dispatch()

    # ------------------------------------------------------------------
    def _dispatch(self):
        while self._waiting and self._running < self.workers:
            ticket = self._waiting.popleft()
            self._running += 1
            ticket.started_at = time.perf_counter()
            ticket.ready.set()
        self._moved.set()
        self._moved = asyncio.Event()
