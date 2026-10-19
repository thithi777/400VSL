"""Dynamic Time Warping với hai đầu nới lỏng.

Video mẫu có phần đứng yên trước/sau động tác, đoạn webcam 2,56 s thì có thể cắt sớm.
Cho phép đường căn chỉnh bắt đầu và kết thúc lệch tối đa `margin` (tỉ lệ độ dài) ở mỗi
chuỗi thay vì buộc khớp frame đầu với frame đầu, frame cuối với frame cuối.
Bước đi: (1,1), (1,0), (0,1).
"""
import numpy as np


def dtw(cost, margin=0.15):
    """
    cost: (N, M) chi phí cục bộ giữa frame i của chuỗi A và frame j của chuỗi B
    Return: (path, mean_cost)
        path: mảng (K, 2) các cặp (i, j) theo thời gian
        mean_cost: chi phí trung bình trên đường đi
    """
    cost = np.asarray(cost, dtype=np.float64)
    n, m = cost.shape
    if n == 0 or m == 0:
        raise ValueError("Chuỗi rỗng")

    start_a = max(1, int(round(n * margin)))
    start_b = max(1, int(round(m * margin)))

    acc = np.full((n, m), np.inf)
    length = np.zeros((n, m), dtype=np.int64)
    move = np.full((n, m), -1, dtype=np.int8)   # 0 chéo, 1 từ trên (i-1), 2 từ trái (j-1), -1 điểm bắt đầu

    for i in range(n):
        row_cost = cost[i]
        for j in range(m):
            c = row_cost[j]

            # Điểm bắt đầu tự do trên cạnh đầu, trong phạm vi margin.
            # Chi phí không âm nên bắt đầu mới ở đây luôn không tệ hơn đi tiếp từ ô trước.
            if (i == 0 and j < start_b) or (j == 0 and i < start_a):
                acc[i, j], length[i, j], move[i, j] = c, 1, -1
                continue

            best, best_len, best_move = np.inf, 0, -1
            if i > 0 and j > 0 and acc[i - 1, j - 1] < best:
                best, best_len, best_move = acc[i - 1, j - 1], length[i - 1, j - 1], 0
            if i > 0 and acc[i - 1, j] < best:
                best, best_len, best_move = acc[i - 1, j], length[i - 1, j], 1
            if j > 0 and acc[i, j - 1] < best:
                best, best_len, best_move = acc[i, j - 1], length[i, j - 1], 2

            acc[i, j] = best + c
            length[i, j] = best_len + 1
            move[i, j] = best_move

    # Điểm kết thúc tự do trên cạnh cuối, trong phạm vi margin; chọn theo chi phí trung bình
    end_a = n - max(1, int(round(n * margin)))
    end_b = m - max(1, int(round(m * margin)))
    candidates = [(n - 1, j) for j in range(max(end_b, 0), m)] + [(i, m - 1) for i in range(max(end_a, 0), n)]
    end = min(candidates, key=lambda ij: acc[ij] / max(length[ij], 1))

    path = []
    i, j = end
    while True:
        path.append((i, j))
        mv = move[i, j]
        if mv == -1:
            break
        if mv == 0:
            i, j = i - 1, j - 1
        elif mv == 1:
            i -= 1
        else:
            j -= 1
    path.reverse()

    return np.asarray(path, dtype=np.int64), float(acc[end] / max(length[end], 1))
