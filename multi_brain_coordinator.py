"""
Multi-Brain Coordinator for Jarvis/DevMind
Inspired by pguilp25/jarvis - coordinates multiple models for better decisions
"""
import os
import asyncio
import json
from typing import Dict, List, Optional
from datetime import datetime
import httpx

# Model configurations for multi-brain coordination
MODEL_BRAINS = {
    "planner1": {
        "model": "gemini-2.0-flash",
        "api_key": "GEMINI_API_KEY",
        "role": "Primary Planner",
        "strength": "Speed and efficiency"
    },
    "planner2": {
        "model": "gpt-4o-mini",
        "api_key": "OPENAI_API_KEY",
        "role": "Alternative Planner",
        "strength": "Code generation quality"
    },
    "critic1": {
        "model": "claude-3.5-sonnet",
        "api_key": "ANTHROPIC_API_KEY",
        "role": "Quality Critic",
        "strength": "Deep reasoning and analysis"
    },
    "merger": {
        "model": "gemini-2.0-flash",
        "api_key": "GEMINI_API_KEY",
        "role": "Plan Merger",
        "strength": "Synthesis and integration"
    }
}

class MultiBrainCoordinator:
    def __init__(self):
        self.active_models = {}
        self.planning_history = []
        self.critique_history = []
        self.load_configuration()

    def load_configuration(self):
        """Load which models are available based on API keys"""
        for brain_name, config in MODEL_BRAINS.items():
            api_key = os.getenv(config["api_key"])
            if api_key:
                self.active_models[brain_name] = config
                print(f"[MULTI-BRAIN] {brain_name} ({config['model']}) is available")
            else:
                print(f"[MULTI-BRAIN] {brain_name} ({config['model']}) - API key not available")

    async def plan_independently(self, task: str, context: str) -> Dict[str, str]:
        """Have multiple models plan independently"""
        plans = {}
        
        for brain_name, config in self.active_models.items():
            if "planner" in brain_name:
                try:
                    plan = await self.get_model_plan(config, task, context)
                    plans[brain_name] = plan
                    print(f"[MULTI-BRAIN] {brain_name} generated plan")
                except Exception as e:
                    print(f"[MULTI-BRAIN] {brain_name} planning failed: {e}")
                    plans[brain_name] = f"Planning failed: {e}"
        
        self.planning_history.append({
            "task": task,
            "plans": plans,
            "timestamp": datetime.now().isoformat()
        })
        
        return plans

    async def get_model_plan(self, config: Dict, task: str, context: str) -> str:
        """Get a plan from a specific model"""
        api_key = os.getenv(config["api_key"])
        model = config["model"]
        
        prompt = f"""You are a {config['role']}. Your strength is {config['strength']}.

Task: {task}

Context:
{context}

Please provide a detailed plan to accomplish this task. Be specific about steps, files to modify, and approaches to take."""

        # Route to appropriate API based on model
        if "gemini" in model.lower():
            return await self.query_gemini(prompt, api_key, model)
        elif "gpt" in model.lower():
            return await self.query_openai(prompt, api_key, model)
        elif "claude" in model.lower():
            return await self.query_anthropic(prompt, api_key, model)
        else:
            return f"Model {model} not supported for planning"

    async def critique_plans(self, plans: Dict[str, str]) -> Dict[str, str]:
        """Have critic models critique the plans"""
        critiques = {}
        
        for brain_name, config in self.active_models.items():
            if "critic" in brain_name:
                try:
                    critique = await self.get_model_critique(config, plans)
                    critiques[brain_name] = critique
                    print(f"[MULTI-BRAIN] {brain_name} provided critique")
                except Exception as e:
                    print(f"[MULTI-BRAIN] {brain_name} critique failed: {e}")
                    critiques[brain_name] = f"Critique failed: {e}"
        
        self.critique_history.append({
            "plans": plans,
            "critiques": critiques,
            "timestamp": datetime.now().isoformat()
        })
        
        return critiques

    async def get_model_critique(self, config: Dict, plans: Dict[str, str]) -> str:
        """Get critique from a specific model"""
        api_key = os.getenv(config["api_key"])
        model = config["model"]
        
        plans_text = "\n\n".join([f"{name}:\n{plan}" for name, plan in plans.items()])
        
        prompt = f"""You are a {config['role']}. Your strength is {config['strength']}.

Review the following plans and provide constructive criticism:

{plans_text}

Identify:
1. Strengths of each plan
2. Weaknesses or potential issues
3. Missing considerations
4. Which plan (or combination) seems best and why

Be thorough but constructive."""

        if "gemini" in model.lower():
            return await self.query_gemini(prompt, api_key, model)
        elif "gpt" in model.lower():
            return await self.query_openai(prompt, api_key, model)
        elif "claude" in model.lower():
            return await self.query_anthropic(prompt, api_key, model)
        else:
            return f"Model {model} not supported for critique"

    async def merge_plans(self, plans: Dict[str, str], critiques: Dict[str, str]) -> str:
        """Merge the best elements from different plans"""
        merger_config = self.active_models.get("merger")
        if not merger_config:
            # Fallback to first available model
            merger_config = list(self.active_models.values())[0]
        
        try:
            api_key = os.getenv(merger_config["api_key"])
            model = merger_config["model"]
            
            plans_text = "\n\n".join([f"{name}:\n{plan}" for name, plan in plans.items()])
            critiques_text = "\n\n".join([f"{name}:\n{critique}" for name, critique in critiques.items()])
            
            prompt = f"""You are a Plan Merger. Your strength is {merger_config['strength']}.

Original Plans:
{plans_text}

Critiques:
{critiques_text}

Based on the critiques, create a merged plan that:
1. Incorporates the strongest elements from each plan
2. Addresses the weaknesses identified
3. Provides a clear, actionable approach
4. Specifies which elements come from which original plan

Provide the final merged plan."""

            if "gemini" in model.lower():
                return await self.query_gemini(prompt, api_key, model)
            elif "gpt" in model.lower():
                return await self.query_openai(prompt, api_key, model)
            elif "claude" in model.lower():
                return await self.query_anthropic(prompt, api_key, model)
            else:
                return plans.get(list(plans.keys())[0], "No merger available")
                
        except Exception as e:
            print(f"[MULTI-BRAIN] Plan merge failed: {e}")
            # Fallback to first plan
            return plans.get(list(plans.keys())[0], "Merge failed, using first plan")

    async def query_gemini(self, prompt: str, api_key: str, model: str) -> str:
        """Query Google Gemini API"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            
            try:
                return result["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError):
                if "error" in result:
                    raise ValueError(f"Gemini API Error: {result['error'].get('message', 'Unknown')}")
                raise ValueError(f"Unexpected response from Gemini API")

    async def query_openai(self, prompt: str, api_key: str, model: str) -> str:
        """Query OpenAI API"""
        url = "https://api.openai.com/v1/chat/completions"
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2000
        }
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            try:
                return result["choices"][0]["message"]["content"]
            except (KeyError, IndexError):
                if "error" in result:
                    raise ValueError(f"OpenAI API Error: {result['error'].get('message', 'Unknown')}")
                raise ValueError(f"Unexpected response from OpenAI API")

    async def query_anthropic(self, prompt: str, api_key: str, model: str) -> str:
        """Query Anthropic Claude API"""
        url = "https://api.anthropic.com/v1/messages"
        
        payload = {
            "model": model,
            "max_tokens": 2000,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            try:
                return result["content"][0]["text"]
            except (KeyError, IndexError):
                if "error" in result:
                    raise ValueError(f"Anthropic API Error: {result['error'].get('message', 'Unknown')}")
                raise ValueError(f"Unexpected response from Anthropic API")

    async def coordinate_task(self, task: str, context: str) -> Dict:
        """Coordinate a multi-brain task from start to finish"""
        print(f"[MULTI-BRAIN] Starting coordination for task: {task[:50]}...")
        
        # Phase 1: Independent Planning
        print("[MULTI-BRAIN] Phase 1: Independent Planning")
        plans = await self.plan_independently(task, context)
        
        if not plans:
            print("[MULTI-BRAIN] No plans generated, using fallback")
            return {"status": "fallback", "plan": "Direct execution without coordination"}
        
        # Phase 2: Critique
        print("[MULTI-BRAIN] Phase 2: Plan Critique")
        critiques = await self.critique_plans(plans)
        
        # Phase 3: Merge
        print("[MULTI-BRAIN] Phase 3: Plan Merging")
        merged_plan = await self.merge_plans(plans, critiques)
        
        result = {
            "status": "success",
            "original_plans": plans,
            "critiques": critiques,
            "merged_plan": merged_plan,
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"[MULTI-BRAIN] Coordination complete")
        return result

# Global multi-brain coordinator instance
multi_brain_coordinator = MultiBrainCoordinator()

async def coordinate_with_multi_brain(task: str, context: str) -> Dict:
    """Public interface for multi-brain coordination"""
    return await multi_brain_coordinator.coordinate_task(task, context)

if __name__ == "__main__":
    # Test multi-brain coordination
    async def test():
        print("Testing Multi-Brain Coordinator")
        print("=" * 50)
        
        test_task = "Fix the SQL injection vulnerability in the PHP controller"
        test_context = "Project is APS Dream Home, a real estate management system"
        
        result = await coordinate_with_multi_brain(test_task, test_context)
        
        print(f"\nCoordination Result:")
        print(f"Status: {result['status']}")
        if result['status'] == 'success':
            print(f"Plans generated: {len(result['original_plans'])}")
            print(f"Critiques provided: {len(result['critiques'])}")
            print(f"Merged plan length: {len(result['merged_plan'])} characters")
    
    import asyncio
    asyncio.run(test())
