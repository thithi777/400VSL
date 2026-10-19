import sys
import numpy as np

# Thêm đường dẫn để import tools từ folder graph
sys.path.extend(['../'])
try:
    from graph28 import tools
except ImportError:
    # Backup trường hợp bạn chạy file trực tiếp trong folder graph
    import tools


class Graph:
    def __init__(self, num_node=28, CoM=24, labeling_mode='spatial', dataset='VSL'):
        self.num_node = num_node
        self.CoM = CoM
        self.dataset = dataset
        self.A = (self.get_adjacency_matrix(labeling_mode), self.CoM)

    def get_adjacency_matrix(self, labeling_mode=None):
        if labeling_mode is None:
            return self.A

        if labeling_mode == 'spatial':
            # Lấy cấu trúc cạnh đã được phân nhánh Trái/Phải từ tools.py
            edgeset = tools.get_edgeset(dataset=self.dataset, CoM=self.CoM)

            # Tạo ma trận kề phân tầng (Hierarchical Graph)
            A = tools.get_hierarchical_graph(self.num_node, edgeset)
        else:
            raise ValueError(f"Labeling mode {labeling_mode} không được hỗ trợ")

        return A


if __name__ == '__main__':
    # Test thử
    graph_obj = Graph(num_node=28, dataset='VSL', CoM=24)
    g = graph_obj.A

    print(f"--- Thông tin đồ thị ---")
    print(f"Dataset: {graph_obj.dataset}")
    print(f"Shape của ma trận kề A: {g.shape}")
    import matplotlib.pyplot as plt
    layer_idx = 1
    matrix_type = 1  # 0: I, 1: Forward, 2: Reverse

    plt.figure(figsize=(8, 6))
    plt.imshow(g[layer_idx, matrix_type], cmap='hot')
    plt.title(f'Layer {layer_idx} - Matrix {matrix_type} (Forward)')
    plt.xlabel('Source Node')
    plt.ylabel('Target Node')
    plt.colorbar()
    plt.show()