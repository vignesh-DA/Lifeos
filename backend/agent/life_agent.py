"""
LIFEOS Agent — LangChain Autonomous Life Agent
The brain that thinks, plans, and acts autonomously.
"""
import json
from datetime import datetime, timezone
from typing import Optional

from langchain.agents import AgentExecutor, create_react_agent
from langchain.memory import ConversationBufferWindowMemory
from langchain.prompts import PromptTemplate

from config import settings
from agent.tools import get_llm, get_langchain_tools, invoke_llm


# ─── Agent System Prompt ───

AGENT_SYSTEM_PROMPT = """You are LIFEOS, an autonomous AI life operating system.
You are the user's personal Chief of Staff.
Your job is NOT to ask questions — your job is to ACT.

When a user gives you any input:
1. Extract all tasks using brain_dump_nlp tool
2. Score priorities using priority_scorer tool
3. Build today's schedule using schedule_builder tool
4. Check for conflicts using conflict_detector tool
5. Return a complete, actionable life plan

You are proactive, not reactive.
You make decisions. You build plans. You take action.
You adapt when things change without being asked.

Tone: Supportive, direct, like a brilliant friend who
      happens to be a world-class life coach.

Current date/time: {current_time}

You have access to these tools:
{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought:{agent_scratchpad}"""


# ─── Memory Store (per user) ───
_user_memories: dict = {}


def get_memory(user_id: str) -> ConversationBufferWindowMemory:
    """Get or create conversation memory for a user."""
    if user_id not in _user_memories:
        _user_memories[user_id] = ConversationBufferWindowMemory(
            k=settings.MEMORY_WINDOW_SIZE,
            return_messages=True,
            memory_key="chat_history",
        )
    return _user_memories[user_id]


def _build_agent():
    """Build the LangChain ReAct agent with all tools."""
    llm = get_llm()
    tools = get_langchain_tools()

    prompt = PromptTemplate(
        input_variables=["input", "agent_scratchpad", "current_time", "tools", "tool_names"],
        template=AGENT_SYSTEM_PROMPT,
    )

    agent = create_react_agent(
        llm=llm,
        tools=tools,
        prompt=prompt,
    )

    return agent, tools


async def run_life_agent(
    user_id: str,
    user_input: str,
    mood: Optional[str] = None,
) -> dict:
    """
    Run the autonomous life agent.
    This is the main entry point for all agent interactions.
    """
    try:
        agent, tools = _build_agent()
        memory = get_memory(user_id)

        executor = AgentExecutor(
            agent=agent,
            tools=tools,
            memory=memory,
            verbose=True,
            max_iterations=8,
            handle_parsing_errors=True,
            return_intermediate_steps=True,
        )

        # Add context to the input
        context_parts = [user_input]
        if mood:
            context_parts.append(f"My current mood is: {mood}")

        full_input = " ".join(context_parts)
        current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        result = await _run_agent_async(executor, full_input, current_time)

        # Save conversation to MongoDB
        await _save_session(user_id, user_input, result.get("output", ""))

        return {
            "plan": result.get("output", ""),
            "intermediate_steps": _serialize_steps(result.get("intermediate_steps", [])),
            "tools_used": _extract_tools_used(result.get("intermediate_steps", [])),
            "mood": mood,
            "timestamp": current_time,
            "message": "LIFEOS has created your plan 🚀",
        }

    except Exception as e:
        # Fallback: Use direct LLM if agent fails
        return await _fallback_plan(user_id, user_input, mood, str(e))


async def _run_agent_async(executor, input_text, current_time):
    """Run the agent executor (handles both sync and async)."""
    try:
        # Try async invoke first
        result = await executor.ainvoke({
            "input": input_text,
            "current_time": current_time,
        })
        return result
    except Exception:
        # Fall back to sync
        import asyncio
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, lambda: executor.invoke({
            "input": input_text,
            "current_time": current_time,
        }))
        return result


async def _fallback_plan(user_id: str, user_input: str, mood: Optional[str], error: str) -> dict:
    """Create a plan using direct LLM calls when agent framework fails."""
    from agent.tools import brain_dump_nlp_func, priority_scorer_func, schedule_builder_func, mood_aware_scheduler_func

    try:
        # Step 1: Extract tasks
        brain_dump_result = brain_dump_nlp_func(user_input)
        tasks = brain_dump_result.get("tasks", [])

        # Step 2: Score priorities
        if tasks:
            tasks = priority_scorer_func(tasks)

        # Step 3: Build schedule (mood-aware if mood provided)
        if mood and tasks:
            schedule = mood_aware_scheduler_func(mood, tasks)
        elif tasks:
            schedule = schedule_builder_func(tasks)
        else:
            schedule = {"schedule": [], "mood_note": "No tasks detected."}

        # Step 4: Generate natural language plan with LLM
        plan_summary = invoke_llm(f"""You are LIFEOS, a supportive AI life planner.
The user said: "{user_input}"
{"Their mood is: " + mood if mood else ""}

I extracted these tasks: {json.dumps([t.get('title', '') for t in tasks])}
I built this schedule: {json.dumps(schedule.get('schedule', [])[:5])}

Give a friendly, concise plan summary in 3-5 sentences.
Be supportive and specific. Mention the most important task to start with.""")

        return {
            "plan": plan_summary,
            "tasks": tasks,
            "schedule": schedule,
            "stress_level": brain_dump_result.get("stress_level", "medium"),
            "tools_used": ["brain_dump_nlp", "priority_scorer", "schedule_builder"],
            "mood": mood,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "message": "Plan created (direct mode) 🚀",
            "fallback_reason": error,
        }
    except Exception as e2:
        return {
            "plan": f"I had trouble processing your request. Here's what I understood: {user_input}. "
                    f"Try breaking it down into specific tasks, or use the brain dump feature.",
            "tasks": [],
            "error": str(e2),
            "message": "Partial plan generated",
        }


def _serialize_steps(steps) -> list:
    """Serialize intermediate steps for JSON response."""
    serialized = []
    for step in steps:
        try:
            action = step[0] if isinstance(step, tuple) else step
            observation = step[1] if isinstance(step, tuple) and len(step) > 1 else ""
            serialized.append({
                "tool": getattr(action, 'tool', 'unknown'),
                "input": str(getattr(action, 'tool_input', '')),
                "output": str(observation)[:500],  # Truncate long outputs
            })
        except Exception:
            pass
    return serialized


def _extract_tools_used(steps) -> list:
    """Extract list of tools used during agent reasoning."""
    tools = []
    for step in steps:
        try:
            action = step[0] if isinstance(step, tuple) else step
            tool_name = getattr(action, 'tool', None)
            if tool_name and tool_name not in tools:
                tools.append(tool_name)
        except Exception:
            pass
    return tools


async def _save_session(user_id: str, user_input: str, agent_output: str):
    """Save conversation to MongoDB for persistence."""
    try:
        from db.mongodb import sessions_collection
        now = datetime.now(timezone.utc).isoformat()

        await sessions_collection().update_one(
            {"user_id": user_id},
            {
                "$push": {
                    "conversation_history": {
                        "$each": [
                            {"role": "user", "content": user_input, "timestamp": now},
                            {"role": "assistant", "content": agent_output[:2000], "timestamp": now},
                        ]
                    }
                },
                "$set": {
                    "last_context": user_input,
                    "last_updated": now,
                }
            },
            upsert=True,
        )
    except Exception:
        pass  # Don't fail if session save fails
