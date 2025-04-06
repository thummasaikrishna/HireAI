# talent_resonance/agents/base_agent.py
import uuid
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class BaseAgent(ABC):
    """Base class for all agents in the Talent Resonance Platform."""
    
    def __init__(self, agent_id: Optional[str] = None, name: str = "Agent"):
        """
        Initialize a base agent.
        
        Args:
            agent_id: Unique identifier for the agent
            name: Human-readable name for the agent
        """
        self.agent_id = agent_id or str(uuid.uuid4())
        self.name = name
        self.logger = logging.getLogger(f"agent.{self.name}")
        self.inbox = []
        self.outbox = []
        self.status = "idle"
    
    @abstractmethod
    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an incoming message and produce a response.
        
        Args:
            message: The incoming message to process
            
        Returns:
            The response message
        """
        pass
    
    async def receive_message(self, message: Dict[str, Any]) -> None:
        """
        Add a message to the agent's inbox.
        
        Args:
            message: The message to add
        """
        self.logger.debug(f"Received message: {message.get('type', 'unknown')}")
        self.inbox.append(message)
        self.status = "processing"
        response = await self.process_message(message)
        self.outbox.append(response)
        self.status = "idle"
        return response
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the agent.
        
        Returns:
            A dictionary with the agent's status information
        """
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "status": self.status,
            "inbox_size": len(self.inbox),
            "outbox_size": len(self.outbox)
        }

# talent_resonance/agents/orchestrator.py
import asyncio
from typing import Dict, Any, List, Callable, Optional
import logging
from .base_agent import BaseAgent

class OrchestratorAgent(BaseAgent):
    """
    Central orchestrator that coordinates all agent activities.
    """
    
    def __init__(self, agent_id: Optional[str] = None):
        super().__init__(agent_id, "Orchestrator")
        self.agents = {}
        self.workflows = {}
        self.active_processes = {}
        self.logger = logging.getLogger("agent.orchestrator")
    
    def register_agent(self, agent: BaseAgent) -> None:
        """
        Register an agent with the orchestrator.
        
        Args:
            agent: The agent to register
        """
        self.agents[agent.agent_id] = agent
        self.logger.info(f"Registered agent: {agent.name} (ID: {agent.agent_id})")
    
    def register_workflow(self, workflow_id: str, steps: List[Dict[str, Any]]) -> None:
        """
        Register a workflow with the orchestrator.
        
        Args:
            workflow_id: A unique identifier for the workflow
            steps: A list of workflow steps, each containing agent IDs and transition logic
        """
        self.workflows[workflow_id] = steps
        self.logger.info(f"Registered workflow: {workflow_id} with {len(steps)} steps")
    
    async def start_workflow(self, workflow_id: str, initial_data: Dict[str, Any]) -> str:
        """
        Start a new workflow process.
        
        Args:
            workflow_id: The ID of the workflow to start
            initial_data: The initial data to pass to the first step
            
        Returns:
            The ID of the new process
        """
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow not found: {workflow_id}")
        
        process_id = f"process_{len(self.active_processes) + 1}"
        self.active_processes[process_id] = {
            "workflow_id": workflow_id,
            "current_step": 0,
            "data": initial_data,
            "status": "running"
        }
        
        # Start the workflow execution
        asyncio.create_task(self._execute_workflow(process_id))
        
        return process_id
    
    async def _execute_workflow(self, process_id: str) -> None:
        """
        Execute a workflow process.
        
        Args:
            process_id: The ID of the process to execute
        """
        process = self.active_processes[process_id]
        workflow = self.workflows[process["workflow_id"]]
        
        while process["current_step"] < len(workflow) and process["status"] == "running":
            step = workflow[process["current_step"]]
            agent_id = step["agent_id"]
            
            if agent_id not in self.agents:
                self.logger.error(f"Agent not found: {agent_id}")
                process["status"] = "error"
                break
            
            agent = self.agents[agent_id]
            
            # Prepare message for the agent
            message = {
                "process_id": process_id,
                "type": step["message_type"],
                "data": process["data"],
                "workflow_id": process["workflow_id"],
                "step_id": process["current_step"]
            }
            
            # Send message to agent and wait for response
            self.logger.info(f"Sending message to {agent.name} for process {process_id}")
            response = await agent.receive_message(message)
            
            # Update process data with response
            process["data"].update(response.get("data", {}))
            
            # Determine next step
            transition_logic = step.get("transition", {})
            if "next_step" in transition_logic:
                process["current_step"] = transition_logic["next_step"]
            else:
                process["current_step"] += 1
            
            # Check if workflow is complete
            if process["current_step"] >= len(workflow):
                process["status"] = "completed"
                self.logger.info(f"Workflow completed for process {process_id}")
    
    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an incoming message.
        
        Args:
            message: The message to process
            
        Returns:
            The response message
        """
        message_type = message.get("type", "unknown")
        
        if message_type == "start_workflow":
            workflow_id = message.get("workflow_id")
            initial_data = message.get("data", {})
            process_id = await self.start_workflow(workflow_id, initial_data)
            return {
                "type": "workflow_started",
                "process_id": process_id,
                "status": "running"
            }
        
        elif message_type == "get_process_status":
            process_id = message.get("process_id")
            if process_id not in self.active_processes:
                return {
                    "type": "error",
                    "error": "Process not found",
                    "process_id": process_id
                }
            
            return {
                "type": "process_status",
                "process_id": process_id,
                "status": self.active_processes[process_id]["status"],
                "current_step": self.active_processes[process_id]["current_step"],
                "workflow_id": self.active_processes[process_id]["workflow_id"]
            }
        
        elif message_type == "pause_process":
            process_id = message.get("process_id")
            if process_id in self.active_processes:
                self.active_processes[process_id]["status"] = "paused"
                return {
                    "type": "process_paused",
                    "process_id": process_id
                }
            return {
                "type": "error",
                "error": "Process not found",
                "process_id": process_id
            }
        
        else:
            return {
                "type": "error",
                "error": f"Unknown message type: {message_type}"
            }
