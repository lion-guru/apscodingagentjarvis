"""
Hybrid Linear Attention Engine for DevMind IDE.
Combines KDA (Key-Query-Value Attention) with Kimi Delta Attention
for efficient context processing and compression.
"""
import math
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class AttentionConfig:
    head_dim: int = 64
    num_heads: int = 8
    use_kda: bool = True
    use_delta: bool = True
    compression_ratio: float = 0.5
    delta_threshold: float = 0.01
    kernel_type: str = "elu"
    temperature: float = 1.0


@dataclass
class AttentionResult:
    compressed_messages: List[Dict[str, Any]]
    compression_ratio: float
    attention_weights: List[float]
    kda_scores: List[float]
    delta_scores: List[float]
    total_tokens_saved: int
    execution_time_ms: float


class HybridLinearAttention:
    def __init__(self, config: AttentionConfig = None):
        self.config = config or AttentionConfig()
        self._key_cache: List[List[float]] = []
        self._value_cache: List[List[float]] = []
        self._query_cache: List[List[float]] = []
        self._attention_weights: List[float] = []
        self._kda_scores: List[float] = []
        self._delta_scores: List[float] = []

    def forward(self, query, key, value, attention_mask=None):
        start = time.perf_counter()
        self._query_cache = query
        self._key_cache = key
        self._value_cache = value

        if self.config.use_kda and self.config.use_delta:
            result = self._hybrid_forward(query, key, value, attention_mask)
        elif self.config.use_kda:
            result = self._kda_attention(query, key, value)
        elif self.config.use_delta:
            result = self._kimi_delta_attention(query, key, value)
        else:
            result = self._linear_attention(query, key, value)

        elapsed = (time.perf_counter() - start) * 1000
        return result

    def _hybrid_forward(self, query, key, value, attention_mask=None):
        kda_out = self._kda_attention(query, key, value)
        delta_out = self._kimi_delta_attention(query, key, value)
        linear_out = self._linear_attention(query, key, value)

        kda_weight = self.config.compression_ratio
        delta_weight = (1.0 - self.config.compression_ratio) * 0.5
        linear_weight = (1.0 - self.config.compression_ratio) * 0.5

        if attention_mask is not None:
            mask_factor = self._apply_mask(attention_mask, len(query))
            kda_weight *= mask_factor
            delta_weight *= mask_factor
            linear_weight *= mask_factor

        total_weight = kda_weight + delta_weight + linear_weight
        if total_weight == 0:
            total_weight = 1.0

        result = []
        for i in range(len(query)):
            row = []
            for j in range(len(value[0]) if value else 0):
                kda_val = kda_out[i][j] if i < len(kda_out) and j < len(kda_out[i]) else 0.0
                delta_val = delta_out[i][j] if i < len(delta_out) and j < len(delta_out[i]) else 0.0
                linear_val = linear_out[i][j] if i < len(linear_out) and j < len(linear_out[i]) else 0.0
                combined = (kda_weight * kda_val + delta_weight * delta_val + linear_weight * linear_val) / total_weight
                row.append(combined)
            result.append(row)

        self._attention_weights = [kda_weight / total_weight, delta_weight / total_weight, linear_weight / total_weight]
        return result

    def _kda_attention(self, query, key, value):
        q_len = len(query)
        k_len = len(key)
        d = len(query[0]) if query else 0
        if q_len == 0 or k_len == 0 or d == 0:
            return [[0.0] * len(value[0])] * q_len if value else []

        scores = []
        for i in range(q_len):
            row = []
            for j in range(k_len):
                dot = sum(query[i][k] * key[j][k] for k in range(d))
                norm_q = math.sqrt(sum(x * x for x in query[i]))
                norm_k = math.sqrt(sum(x * x for x in key[j]))
                if norm_q > 0 and norm_k > 0:
                    dot = dot / (norm_q * norm_k + 1e-8)
                row.append(dot)
            scores.append(row)

        self._kda_scores = [max(row) if row else 0.0 for row in scores]
        v_dim = len(value[0]) if value else 0
        result = []
        for i in range(q_len):
            row = [0.0] * v_dim
            weight_sum = 0.0
            for j in range(k_len):
                w = math.exp(scores[i][j])
                weight_sum += w
                for k in range(v_dim):
                    row[k] += w * value[j][k]
            if weight_sum > 0:
                for k in range(v_dim):
                    row[k] /= weight_sum
            result.append(row)
        return result

    def _kimi_delta_attention(self, query, key, value, delta_threshold=None):
        threshold = delta_threshold or self.config.delta_threshold
        q_len = len(query)
        k_len = len(key)
        d = len(query[0]) if query else 0
        if q_len == 0 or k_len == 0 or d == 0:
            return [[0.0] * len(value[0])] * q_len if value else []

        delta_scores = []
        for i in range(q_len):
            row = []
            for j in range(k_len):
                diff = sum(abs(query[i][k] - key[j][k]) for k in range(d))
                delta_val = diff / (d + 1e-8)
                row.append(delta_val)
            delta_scores.append(row)

        self._delta_scores = [min(row) if row else float("inf") for row in delta_scores]
        v_dim = len(value[0]) if value else 0
        result = []
        for i in range(q_len):
            row = [0.0] * v_dim
            weight_sum = 0.0
            for j in range(k_len):
                if delta_scores[i][j] < threshold:
                    w = 1.0 / (delta_scores[i][j] + 1e-8)
                else:
                    w = 0.0
                weight_sum += w
                for k in range(v_dim):
                    row[k] += w * value[j][k]
            if weight_sum > 0:
                for k in range(v_dim):
                    row[k] /= weight_sum
            result.append(row)
        return result

    def _linear_attention(self, query, key, value):
        q_len = len(query)
        k_len = len(key)
        d = len(query[0]) if query else 0
        if q_len == 0 or k_len == 0 or d == 0:
            return [[0.0] * len(value[0])] * q_len if value else []

        k_vec = [self._apply_kernel(sum(key[j][f] * key[j][f] for f in range(d))) for j in range(k_len)]
        v_dim = len(value[0]) if value else 0
        kv_sum = [[0.0] * v_dim for _ in range(d)]
        for j in range(k_len):
            for k in range(v_dim):
                for f in range(d):
                    kv_sum[f][k] += k_vec[j] * value[j][k]

        result = []
        for i in range(q_len):
            row = [0.0] * v_dim
            for f in range(d):
                qk = self._apply_kernel(query[i][f] * query[i][f])
                for k in range(v_dim):
                    row[k] += qk * kv_sum[f][k]
            result.append(row)
        return result

    def _apply_kernel(self, x):
        if self.config.kernel_type == "elu":
            return math.exp(x) - 1.0 if x >= 0 else -math.exp(-x) + 1.0
        elif self.config.kernel_type == "relu":
            return max(0.0, x)
        elif self.config.kernel_type == "gelu":
            return 0.5 * x * (1.0 + math.tanh(math.sqrt(2.0 / math.pi) * (x + 0.044715 * x * x * x)))
        return math.exp(x)

    def _apply_mask(self, attention_mask, q_len):
        if not attention_mask:
            return 1.0
        total = 0.0
        count = 0
        for i in range(min(q_len, len(attention_mask))):
            for j in range(len(attention_mask[i])):
                total += attention_mask[i][j]
                count += 1
        return total / count if count > 0 else 1.0

    def compress_context(self, messages, compression_ratio=None):
        ratio = compression_ratio or self.config.compression_ratio
        if ratio >= 1.0 or len(messages) <= 1:
            return messages
        target_count = max(1, int(len(messages) * ratio))
        if target_count >= len(messages):
            return messages
        message_vectors = self._messages_to_vectors(messages)
        if not message_vectors:
            return messages[:target_count]
        importance_scores = self._compute_importance(message_vectors)
        indexed = sorted(enumerate(importance_scores), key=lambda x: x[1], reverse=True)
        selected_indices = sorted([idx for idx, _ in indexed[:target_count]])
        compressed = [messages[idx] for idx in selected_indices]
        if len(compressed) < len(messages):
            compressed.append({"role": "system", "content": f"[Compressed {len(messages) - len(compressed)} messages into summary]", "compressed": True})
        return compressed

    def _messages_to_vectors(self, messages):
        vectors = []
        for msg in messages:
            content = msg.get("content", "")
            if not content:
                vectors.append([0.0] * self.config.head_dim)
                continue
            vec = [(hash(content + str(i)) % 1000) / 1000.0 for i in range(self.config.head_dim)]
            vectors.append(vec)
        return vectors

    def _compute_importance(self, vectors):
        if not vectors:
            return []
        importance = []
        for i, vec in enumerate(vectors):
            norm = math.sqrt(sum(x * x for x in vec))
            uniqueness = 1.0
            for j, other in enumerate(vectors):
                if i != j:
                    sim = sum(a * b for a, b in zip(vec, other)) / (norm * math.sqrt(sum(x * x for x in other)) + 1e-8)
                    uniqueness -= abs(sim)
            importance.append(norm * max(0.0, uniqueness))
        return importance


class AttentionRouter:
    def __init__(self, config: AttentionConfig = None):
        self.config = config or AttentionConfig()
        self._engine = HybridLinearAttention(self.config)

    def route(self, messages, model="", context_length=0):
        use_kda = self.config.use_kda
        use_delta = self.config.use_delta
        if context_length > 8192:
            use_kda = True
            use_delta = True
            self.config.compression_ratio = min(0.8, self.config.compression_ratio + 0.2)
        elif context_length > 4096:
            use_kda = True
            use_delta = False
        elif context_length > 2048:
            use_kda = False
            use_delta = True

        compressed = self._engine.compress_context(messages, self.config.compression_ratio)
        tokens_saved = sum(len(m.get("content", "").split()) for m in messages) - sum(len(m.get("content", "").split()) for m in compressed)
        return AttentionResult(
            compressed_messages=compressed,
            compression_ratio=self.config.compression_ratio,
            attention_weights=self._engine._attention_weights,
            kda_scores=self._engine._kda_scores,
            delta_scores=self._engine._delta_scores,
            total_tokens_saved=tokens_saved,
            execution_time_ms=0.0,
        )
