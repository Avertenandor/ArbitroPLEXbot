"""Interview tool handler for conducting interviews with admins.

This module provides tools for ARIA to start, manage, and cancel interviews
with admin users, collecting their responses for the knowledge base.
"""

from typing import Any

from loguru import logger

from ..base import BaseToolHandler, HandlerContext
from app.services.ai_interview_service import get_interview_service, init_interview_service


__all__ = ["InterviewToolHandler"]


class InterviewToolHandler(BaseToolHandler):
    """Handler for interview-related tools.

    This handler manages interview operations including starting interviews,
    checking status, and canceling active interviews with admins.

    Supported tools:
        - start_interview: Initiates a new interview with an admin
        - get_interview_status: Retrieves the status of an active interview
        - cancel_interview: Cancels an ongoing interview
    """

    def __init__(self, context: HandlerContext) -> None:
        """Initialize the interview tool handler.

        Args:
            context: Handler context containing bot, session, and admin data.
        """
        super().__init__(context)

    def get_tool_names(self) -> set[str]:
        """Get the set of tool names handled by this handler.

        Returns:
            Set containing the names of all interview tools.
        """
        return {"start_interview", "get_interview_status", "cancel_interview"}

    async def handle(
        self,
        tool_name: str,
        tool_input: dict,
        resolve_admin_id_func: Any = None,
        **kwargs
    ) -> dict[str, Any]:
        """Handle execution of interview tools.

        Args:
            tool_name: Name of the tool to execute.
            tool_input: Dictionary containing tool-specific input parameters.
            resolve_admin_id_func: Function to resolve admin identifiers to IDs.
            **kwargs: Additional keyword arguments.

        Returns:
            Dictionary containing the execution result with success status
            and either data or error information.
        """
        # Check if resolve_admin_id_func is provided
        if resolve_admin_id_func is None:
            logger.error(f"Interview tool '{tool_name}' called without resolve_admin_id_func")
            return {
                "success": False,
                "error": "Cannot resolve admin identifier - resolver function not provided"
            }

        # Get or initialize interview service
        interview_service = get_interview_service(self.context.bot)
        if not interview_service:
            interview_service = init_interview_service(self.context.bot)
            logger.info("Initialized interview service")

        # Route to appropriate handler
        if tool_name == "start_interview":
            return await self._handle_start_interview(
                tool_input, resolve_admin_id_func, interview_service
            )
        elif tool_name == "get_interview_status":
            return await self._handle_get_interview_status(
                tool_input, resolve_admin_id_func, interview_service
            )
        elif tool_name == "cancel_interview":
            return await self._handle_cancel_interview(
                tool_input, resolve_admin_id_func, interview_service
            )
        else:
            logger.error(f"Unknown interview tool: {tool_name}")
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}"
            }

    async def _handle_start_interview(
        self,
        tool_input: dict,
        resolve_admin_id_func: Any,
        interview_service: Any
    ) -> dict[str, Any]:
        """Handle the start_interview tool.

        Args:
            tool_input: Input parameters including admin_identifier, topic, and questions.
            resolve_admin_id_func: Function to resolve admin identifier.
            interview_service: Interview service instance.

        Returns:
            Dictionary with success status and interview details or error.
        """
        logger.info(f"Starting interview with tool_input: {tool_input}")

        # Extract parameters
        admin_identifier = tool_input.get("admin_identifier")
        topic = tool_input.get("topic")
        questions = tool_input.get("questions", [])

        # Validate parameters
        if not admin_identifier:
            logger.warning("start_interview called without admin_identifier")
            return {
                "success": False,
                "error": "admin_identifier is required"
            }

        if not topic:
            logger.warning("start_interview called without topic")
            return {
                "success": False,
                "error": "topic is required"
            }

        if not questions or not isinstance(questions, list):
            logger.warning(f"start_interview called with invalid questions: {questions}")
            return {
                "success": False,
                "error": "questions must be a non-empty list"
            }

        # Resolve admin identifier
        try:
            admin_info = await resolve_admin_id_func(admin_identifier)
            if not admin_info:
                logger.warning(f"Could not resolve admin identifier: {admin_identifier}")
                return {
                    "success": False,
                    "error": f"Could not find admin: {admin_identifier}"
                }

            target_admin_id = admin_info.get("id")
            target_admin_username = admin_info.get("username", "Unknown")

            if not target_admin_id:
                logger.error(f"Resolved admin info missing ID: {admin_info}")
                return {
                    "success": False,
                    "error": "Invalid admin information returned"
                }
        except Exception as e:
            logger.error(f"Error resolving admin identifier '{admin_identifier}': {e}")
            return {
                "success": False,
                "error": f"Error resolving admin: {str(e)}"
            }

        # Start the interview
        try:
            result = await interview_service.start_interview(
                interviewer_id=self.context.admin_id,
                target_admin_id=target_admin_id,
                target_admin_username=target_admin_username,
                topic=topic,
                questions=questions
            )
            logger.info(f"Interview started: {result}")
            return result
        except Exception as e:
            logger.error(f"Error starting interview: {e}")
            return {
                "success": False,
                "error": f"Failed to start interview: {str(e)}"
            }

    async def _handle_get_interview_status(
        self,
        tool_input: dict,
        resolve_admin_id_func: Any,
        interview_service: Any
    ) -> dict[str, Any]:
        """Handle the get_interview_status tool.

        Args:
            tool_input: Input parameters including admin_identifier.
            resolve_admin_id_func: Function to resolve admin identifier.
            interview_service: Interview service instance.

        Returns:
            Dictionary with success status and interview status or error.
        """
        logger.info(f"Getting interview status with tool_input: {tool_input}")

        # Extract parameters
        admin_identifier = tool_input.get("admin_identifier")

        # Validate parameters
        if not admin_identifier:
            logger.warning("get_interview_status called without admin_identifier")
            return {
                "success": False,
                "error": "admin_identifier is required"
            }

        # Resolve admin identifier
        try:
            admin_info = await resolve_admin_id_func(admin_identifier)
            if not admin_info:
                logger.warning(f"Could not resolve admin identifier: {admin_identifier}")
                return {
                    "success": False,
                    "error": f"Could not find admin: {admin_identifier}"
                }

            target_admin_id = admin_info.get("id")
            if not target_admin_id:
                logger.error(f"Resolved admin info missing ID: {admin_info}")
                return {
                    "success": False,
                    "error": "Invalid admin information returned"
                }
        except Exception as e:
            logger.error(f"Error resolving admin identifier '{admin_identifier}': {e}")
            return {
                "success": False,
                "error": f"Error resolving admin: {str(e)}"
            }

        # Get interview status
        try:
            status = interview_service.get_interview_status(target_admin_id)
            if status is None:
                logger.info(f"No interview found for admin {target_admin_id}")
                return {
                    "success": False,
                    "error": f"No interview found for admin {admin_identifier}"
                }

            logger.info(f"Interview status retrieved: {status}")
            return {
                "success": True,
                **status
            }
        except Exception as e:
            logger.error(f"Error getting interview status: {e}")
            return {
                "success": False,
                "error": f"Failed to get interview status: {str(e)}"
            }

    async def _handle_cancel_interview(
        self,
        tool_input: dict,
        resolve_admin_id_func: Any,
        interview_service: Any
    ) -> dict[str, Any]:
        """Handle the cancel_interview tool.

        Args:
            tool_input: Input parameters including admin_identifier.
            resolve_admin_id_func: Function to resolve admin identifier.
            interview_service: Interview service instance.

        Returns:
            Dictionary with success status and cancellation details or error.
        """
        logger.info(f"Canceling interview with tool_input: {tool_input}")

        # Extract parameters
        admin_identifier = tool_input.get("admin_identifier")

        # Validate parameters
        if not admin_identifier:
            logger.warning("cancel_interview called without admin_identifier")
            return {
                "success": False,
                "error": "admin_identifier is required"
            }

        # Resolve admin identifier
        try:
            admin_info = await resolve_admin_id_func(admin_identifier)
            if not admin_info:
                logger.warning(f"Could not resolve admin identifier: {admin_identifier}")
                return {
                    "success": False,
                    "error": f"Could not find admin: {admin_identifier}"
                }

            target_admin_id = admin_info.get("id")
            if not target_admin_id:
                logger.error(f"Resolved admin info missing ID: {admin_info}")
                return {
                    "success": False,
                    "error": "Invalid admin information returned"
                }
        except Exception as e:
            logger.error(f"Error resolving admin identifier '{admin_identifier}': {e}")
            return {
                "success": False,
                "error": f"Error resolving admin: {str(e)}"
            }

        # Cancel the interview
        try:
            result = await interview_service.cancel_interview(target_admin_id)
            logger.info(f"Interview canceled: {result}")
            return result
        except Exception as e:
            logger.error(f"Error canceling interview: {e}")
            return {
                "success": False,
                "error": f"Failed to cancel interview: {str(e)}"
            }
