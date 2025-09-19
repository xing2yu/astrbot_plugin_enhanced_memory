import networkx as nx
import json
import os
from typing import List, Dict, Any
import logging

logger = logging.getLogger("astrbot.plugin.enhanced_memory")

class MemoryGraph:
    def __init__(self, graph_path: str):
        self.graph_path = graph_path
        self.graph = nx.Graph()
        
        self._ensure_storage_path()
        self.load_graph()
    
    def _ensure_storage_path(self):
        """确保存储路径存在"""
        os.makedirs(os.path.dirname(self.graph_path), exist_ok=True)
    
    def load_graph(self):
        """加载记忆图"""
        try:
            if os.path.exists(self.graph_path):
                with open(self.graph_path, 'r', encoding='utf-8') as f:
                    graph_data = json.load(f)
                    self.graph = nx.node_link_graph(graph_data)
                
                logger.info(f"已加载记忆图，包含 {self.graph.number_of_nodes()} 个节点和 {self.graph.number_of_edges()} 条边")
            else:
                self.graph = nx.Graph()
                logger.info("创建了新的记忆图")
        except Exception as e:
            logger.error(f"加载记忆图失败: {e}")
            self.graph = nx.Graph()
    
    def save_graph(self):
        """保存记忆图"""
        try:
            graph_data = nx.node_link_data(self.graph)
            with open(self.graph_path, 'w', encoding='utf-8') as f:
                json.dump(graph_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"已保存记忆图，包含 {self.graph.number_of_nodes()} 个节点和 {self.graph.number_of_edges()} 条边")
            return True
        except Exception as e:
            logger.error(f"保存记忆图失败: {e}")
            return False
    
    def add_memory(self, memory_id: str, memory_data: Dict[str, Any]):
        """添加记忆到图中"""
        self.graph.add_node(memory_id, **memory_data)
        self.save_graph()
    
    def remove_memory(self, memory_id: str):
        """从图中移除记忆"""
        if memory_id in self.graph:
            self.graph.remove_node(memory_id)
            self.save_graph()
    
    def add_association(self, memory_id_1: str, memory_id_2: str, relation_type: str, strength: float = 1.0):
        """添加记忆关联"""
        if memory_id_1 in self.graph and memory_id_2 in self.graph:
            self.graph.add_edge(memory_id_1, memory_id_2, 
                               relation_type=relation_type, strength=strength)
            self.save_graph()
            return True
        return False
    
    def remove_association(self, memory_id_1: str, memory_id_2: str):
        """移除记忆关联"""
        if self.graph.has_edge(memory_id_1, memory_id_2):
            self.graph.remove_edge(memory_id_1, memory_id_2)
            self.save_graph()
            return True
        return False
    
    def get_associated_memories(self, memory_id: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """获取关联记忆"""
        if memory_id not in self.graph:
            return []
        
        # 获取直接关联的记忆
        neighbors = list(self.graph.neighbors(memory_id))
        results = []
        
        for neighbor_id in neighbors[:max_results]:
            edge_data = self.graph[memory_id][neighbor_id]
            results.append({
                "memory_id": neighbor_id,
                "relation_type": edge_data.get("relation_type", "unknown"),
                "strength": edge_data.get("strength", 1.0)
            })
        
        return results
    
    def find_paths_between(self, memory_id_1: str, memory_id_2: str, max_paths: int = 3):
        """查找两个记忆之间的路径"""
        try:
            if memory_id_1 not in self.graph or memory_id_2 not in self.graph:
                return []
            
            paths = list(nx.all_simple_paths(
                self.graph, memory_id_1, memory_id_2, cutoff=3
            ))[:max_paths]
            
            return paths
        except Exception as e:
            logger.error(f"查找记忆路径失败: {e}")
            return []
    
    def get_clusters(self):
        """获取记忆聚类"""
        try:
            clusters = list(nx.connected_components(self.graph))
            return clusters
        except Exception as e:
            logger.error(f"获取记忆聚类失败: {e}")
            return []