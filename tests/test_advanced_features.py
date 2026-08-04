"""
Unit tests for DevMind IDE advanced features.
Tests for attention_engine, stream_manager, hermes_agent, moe_router, multimodal_engine, reasoning_engine.
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from moe_router import ExpertProfile
from reasoning_engine import ReasoningStep


class TestAttentionEngine(unittest.TestCase):
    def setUp(self):
        from attention_engine import AttentionConfig, HybridLinearAttention, AttentionRouter
        self.config = AttentionConfig()
        self.engine = HybridLinearAttention(self.config)
        self.router = AttentionRouter(self.config)

    def test_attention_config_defaults(self):
        self.assertEqual(self.config.head_dim, 64)
        self.assertEqual(self.config.num_heads, 8)
        self.assertTrue(self.config.use_kda)
        self.assertTrue(self.config.use_delta)
        self.assertEqual(self.config.compression_ratio, 0.5)

    def test_kda_attention(self):
        query = [[1.0, 0.0], [0.0, 1.0]]
        key = [[1.0, 0.0], [0.0, 1.0]]
        value = [[2.0, 3.0], [4.0, 5.0]]
        result = self.engine._kda_attention(query, key, value)
        self.assertEqual(len(result), 2)
        self.assertEqual(len(result[0]), 2)

    def test_kimi_delta_attention(self):
        query = [[1.0, 0.0], [0.0, 1.0]]
        key = [[1.0, 0.0], [0.0, 1.0]]
        value = [[2.0, 3.0], [4.0, 5.0]]
        result = self.engine._kimi_delta_attention(query, key, value)
        self.assertEqual(len(result), 2)

    def test_linear_attention(self):
        query = [[1.0, 0.0], [0.0, 1.0]]
        key = [[1.0, 0.0], [0.0, 1.0]]
        value = [[2.0, 3.0], [4.0, 5.0]]
        result = self.engine._linear_attention(query, key, value)
        self.assertEqual(len(result), 2)

    def test_compress_context(self):
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
            {"role": "user", "content": "How are you?"},
            {"role": "assistant", "content": "I am fine"},
        ]
        compressed = self.engine.compress_context(messages, compression_ratio=0.5)
        self.assertLessEqual(len(compressed), len(messages))

    def test_router_route(self):
        messages = [
            {"role": "user", "content": "Test message"},
        ]
        result = self.router.route(messages, context_length=100)
        self.assertEqual(result.compression_ratio, 0.5)
        self.assertIsInstance(result.compressed_messages, list)


class TestStreamManager(unittest.TestCase):
    def setUp(self):
        from stream_manager import StreamManager, StreamChannel, StreamRouter
        self.manager = StreamManager(max_concurrent=3)
        self.router = StreamRouter()

    def test_stream_manager_init(self):
        self.assertEqual(self.manager.max_concurrent, 3)
        self.assertEqual(len(self.manager.channels), 0)

    def test_register_stream(self):
        async def dummy_stream():
            yield "item1"
            yield "item2"

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(self.manager.register_stream("test", dummy_stream()))
            self.assertEqual(result, "test")
        finally:
            loop.close()

    def test_list_channels(self):
        channels = self.manager.list_channels()
        self.assertIsInstance(channels, list)

    def test_get_channel(self):
        channel = self.manager.get_channel("nonexistent")
        self.assertIsNone(channel)

    def test_stream_router_route(self):
        event = {"type": "token", "content": "hello"}
        channel = self.router.route(event)
        self.assertEqual(channel, "token")

    def test_stream_router_register_handler(self):
        handler_called = []
        async def handler(event):
            handler_called.append(event)
        self.router.register_handler("test", handler)
        self.assertIn("test", self.router._handlers)


class TestMoERouter(unittest.TestCase):
    def setUp(self):
        from moe_router import MoERouter, ExpertProfile, TaskClassifier, MoEPolicy
        self.router = MoERouter()
        self.classifier = TaskClassifier()
        self.policy = MoEPolicy()

    def test_classify_code(self):
        result = self.classifier.classify("implement a new feature in python")
        self.assertEqual(result["type"], "code")

    def test_classify_reasoning(self):
        result = self.classifier.classify("why does this happen and how to fix it")
        self.assertEqual(result["type"], "reasoning")

    def test_classify_search(self):
        result = self.classifier.classify("find the location of the file")
        self.assertEqual(result["type"], "search")

    def test_route_task(self):
        from agent_core import Task
        task = Task(title="Test", description="implement a new feature")
        expert = self.router.route_task(task)
        self.assertIsInstance(expert, str)

    def test_add_expert(self):
        expert = ExpertProfile(expert_name="test_expert", model="gemma3:1b")
        self.router.add_expert(expert)
        self.assertIn("test_expert", self.router.experts)

    def test_remove_expert(self):
        expert = ExpertProfile(expert_name="temp_expert", model="gemma3:1b")
        self.router.add_expert(expert)
        result = self.router.remove_expert("temp_expert")
        self.assertTrue(result)
        self.assertNotIn("temp_expert", self.router.experts)

    def test_get_expert_status(self):
        status = self.router.get_expert_status()
        self.assertEqual(status["status"], "ok")
        self.assertIsInstance(status["experts"], list)

    def test_balance_load(self):
        experts = [
            ExpertProfile(expert_name="e1", model="gemma3:1b"),
            ExpertProfile(expert_name="e2", model="gemma3:1b"),
        ]
        weights = self.policy.balance_load(experts)
        self.assertEqual(len(weights), 2)


class TestMultimodalEngine(unittest.TestCase):
    def setUp(self):
        from multimodal_engine import VLMEngine, MimoArchitecture, BigPixelProcessor, VisionConfig
        self.vlm = VLMEngine()
        self.mimo = MimoArchitecture()
        self.bigpixel = BigPixelProcessor()

    def test_vlm_validate_image(self):
        result = self.vlm.validate_image("test_data", "image/png")
        self.assertTrue(result)

    def test_vlm_validate_invalid_image(self):
        result = self.vlm.validate_image("test_data", "image/unsupported")
        self.assertFalse(result)

    def test_vlm_compress_image(self):
        result = self.vlm.compress_image("test_data", target_size_kb=500)
        self.assertEqual(result, "test_data")

    def test_mimo_add_input(self):
        self.mimo.add_input("input1", "text", "hello", priority=1)
        self.assertEqual(len(self.mimo.input_channels), 1)

    def test_mimo_add_output(self):
        self.mimo.add_output("output1", "text", "text", "stdout")
        self.assertEqual(len(self.mimo.output_channels), 1)

    def test_bigpixel_process(self):
        result = asyncio.run(self.bigpixel.process_big_pixel("test.png"))
        self.assertIn("test.png", result)

    def test_bigpixel_stitch(self):
        result = asyncio.run(self.bigpixel.stitch_results(["tile1", "tile2"]))
        self.assertEqual(result, "tile1\ntile2")


class TestReasoningEngine(unittest.TestCase):
    def setUp(self):
        from reasoning_engine import ReasoningEngine, ReasoningConfig, ReasoningTrace, ReasoningStep
        self.engine = ReasoningEngine()
        self.config = ReasoningConfig()
        self.trace = ReasoningTrace()

    def test_reasoning_config_defaults(self):
        self.assertTrue(self.config.enabled)
        self.assertEqual(self.config.max_steps, 10)
        self.assertEqual(self.config.style, "chain_of_thought")

    def test_reasoning_trace_add_step(self):
        step = ReasoningStep(step_number=1, thought="Analyzing the task", confidence=0.8)
        self.trace.add_step(step)
        self.assertEqual(self.trace.total_steps, 1)

    def test_reasoning_trace_to_dict(self):
        step = ReasoningStep(step_number=1, thought="Test thought", confidence=0.9)
        self.trace.add_step(step)
        d = self.trace.to_dict()
        self.assertEqual(d["total_steps"], 1)
        self.assertEqual(len(d["steps"]), 1)

    def test_reasoning_trace_get_final_conclusion(self):
        step = ReasoningStep(step_number=1, thought="Final answer", confidence=0.95)
        self.trace.add_step(step)
        conclusion = self.trace.get_final_conclusion()
        self.assertEqual(conclusion, "Final answer")

    def test_strip_reasoning(self):
        text = "Some text <thinking>internal reasoning</thinking> more text"
        stripped = self.engine.strip_reasoning(text)
        self.assertNotIn("<thinking>", stripped)
        self.assertIn("Some text", stripped)
        self.assertIn("more text", stripped)

    def test_extract_reasoning_blocks(self):
        text = "Before <thinking>reasoning 1</thinking> middle <thinking>reasoning 2</thinking> after"
        blocks = self.engine.extract_reasoning_blocks(text)
        self.assertEqual(len(blocks), 2)

    def test_verify_reasoning(self):
        result = asyncio.run(self.engine.verify_reasoning("some reasoning", "some evidence"))
        self.assertTrue(result)

    def test_self_consistency_check(self):
        result = asyncio.run(self.engine.self_consistency_check("some reasoning", None))
        self.assertTrue(result)


class TestHermesAgent(unittest.TestCase):
    def setUp(self):
        from hermes_agent import HermesAgent, HermesToolExecutor, create_hermes_agents
        self.agent = HermesAgent(model="gemma3:1b", reasoning_depth=1, tool_calling_mode="auto", max_execution_steps=5)
        self.executor = HermesToolExecutor()
        self.agents = create_hermes_agents()

    def test_hermes_agent_init(self):
        self.assertEqual(self.agent.role, "hermes")
        self.assertEqual(self.agent.reasoning_depth, 1)
        self.assertEqual(self.agent.tool_calling_mode, "auto")
        self.assertEqual(self.agent.max_execution_steps, 5)

    def test_hermes_tool_executor_validate_params(self):
        result = self.executor.validate_tool_params("unknown_tool", {})
        self.assertFalse(result)

    def test_create_hermes_agents(self):
        self.assertIn("hermes", self.agents)
        self.assertIn("hermes_fast", self.agents)
        self.assertIn("hermes_deep", self.agents)

    def test_hermes_agent_set_moe_router(self):
        router = object()
        self.agent.set_moe_router(router)
        self.assertEqual(self.agent._moe_router, router)


if __name__ == "__main__":
    unittest.main(verbosity=2)
