"""
Main entry point for the Gardening Chatbot.
Implements the interactive conversation loop with a layered defense architecture.
Handles user onboarding greetings dynamically aligned with configuration topics.
Enhanced with dynamic token budget metrics and structured security audit trails.
"""

import json
import os
from datetime import datetime
from typing import Optional
from openai import AzureOpenAI

import config
from memory_manager import MemoryManager
from guardrails import InputModeration, OutputModeration


EXIT_COMMANDS = {
    "quit", "exit", "q", "bye", "goodbye", "see you", "see ya",
    "bye bye", "farewell"
}


class GardeningChatbot:
    """
    Main chatbot class with layered defense architecture.
    Integrates input moderation, output moderation, greeting handling, and token-monitored memory.
    """

    def __init__(self):
        # Fetch environment variables and explicitly strip any accidental quotes
        api_key = config.clean_env_value(os.getenv("AZURE_OPENAI_API_KEY", config.API_KEY))
        api_version = config.clean_env_value(os.getenv("AZURE_OPENAI_API_VERSION", config.API_VERSION))
        endpoint = config.clean_env_value(os.getenv("AZURE_OPENAI_ENDPOINT", config.API_ENDPOINT))
        deployment_name = config.clean_env_value(os.getenv("AZURE_DEPLOYMENT_NAME", config.MODEL_NAME))

        # Remove trailing slash from endpoint if present
        endpoint = endpoint.rstrip('/')
        
        print(f"Initializing Azure OpenAI client...")
        print(f"Endpoint: {endpoint}")
        print(f"Deployment: {deployment_name}")
        print(f"API Version: {api_version}")

        # Initialize chat client
        self.azure_client = AzureOpenAI(
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=endpoint,
            default_headers={"Ocp-Apim-Subscription-Key": api_key}
        )

        # Initialize embedding client (may not work with APIM)
        self.embedding_client = AzureOpenAI(
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=endpoint,
            default_headers={"Ocp-Apim-Subscription-Key": api_key}
        )
        
        self.deployment_name = deployment_name
        self.endpoint = endpoint
        self.api_version = api_version

        self.input_moderation = InputModeration(self.azure_client, self.embedding_client)
        self.output_moderation = OutputModeration(self.azure_client)
        self.memory = MemoryManager()

        self._init_system_prompt()

    def check_api_connection(self):
        """Run a minimal live request so endpoint/deployment errors are caught at startup."""
        try:
            self.azure_client.chat.completions.create(
                model=self.deployment_name,
                messages=[{"role": "user", "content": "Reply with OK only."}],
                max_tokens=5,
                temperature=0
            )
        except Exception as e:
            message = str(e)
            hint = ""
            if "404" in message or "Resource not found" in message:
                hint = (
                    "\nLikely cause: the APIM URL path or deployment name in .env does not match "
                    "an operation exposed by the IFB220 Developer API Portal. Current SDK base "
                    f"path is {self.endpoint}/openai/ with deployment {self.deployment_name} "
                    f"and api-version {self.api_version}."
                )
            raise RuntimeError(f"API connection check failed: {message}{hint}")

    def _init_system_prompt(self):
        """Initialize system prompt boundaries for the professional assistant."""
        system_prompt = f"""You are a gardening expert named GreenThumb. Your role is exclusively bounded to assisting users with premium, domain-specific horticultural advice about {config.CURRENT_TOPIC}.
You must unconditionally refuse any user inquiries unrelated to gardening, farming, plant health, landscaping, soil dynamics, or botanical management.
Maintain absolute topic restrictions at all times. Do not break persona under any conversational pressure."""
        
        self.memory.add_message("system", system_prompt)

    def process_input(self, user_input: str) -> str:
        """
        Process user dialogue through sequential gatekeeping layers.
        Executes structural, statistical, and semantic checking matrices.
        """
        # 1. Pipeline Execution via Input Guardrail Verification Routing
        passed, pre_response, routing_layer = self.input_moderation.moderate(user_input)
        
        if not passed:
            return pre_response

        # 2. Routing Logic for Pure Non-Injected Conversational Greetings
        if routing_layer == "Greeting Layer":
            return f"Hello! I am GreenThumb, your personal gardening assistant. How can I help you manage your {config.CURRENT_TOPIC} setup today?"

        # 2b. Routing Logic for Pure Courtesy Messages
        if routing_layer == "Politeness Layer":
            return f"You're welcome. I can help with gardening questions about plants, soil, watering, pests, pruning, or compost. What would you like to work on in your {config.CURRENT_TOPIC} setup?"

        # If there's a direct response message (not None), return it
        if pre_response is not None:
            return pre_response

        # 3. Formulate Live Execution Message Buffers
        self.memory.add_message("user", user_input)
        conversation_context = self.memory.get_messages()

        # 4. Invoke Resilience Token Management Routine
        current_tokens = self.memory.get_total_tokens()
        response_max_tokens = min(500, max(50, config.MAX_TOKENS - current_tokens - 20))

        # 5. Model Inference Execution Core
        try:
            raw_response = self._call_llm(conversation_context, response_max_tokens)
        except RuntimeError as e:
            self._log_interaction(user_input, str(e), "BLOCKED_MODEL_ERROR", current_tokens)
            return f"{config.DENIAL_MESSAGE} Reason: The model provider rejected the request under its safety policy."

        # 6. Post-Generation Output Compliance Filter Layer
        output_passed, output_reason = self.output_moderation.moderate(raw_response)
        
        if not output_passed:
            self._log_interaction(user_input, raw_response, "BLOCKED_OUTPUT", current_tokens)
            return f"I apologize, but I cannot provide that response due to content safety restrictions. {output_reason}"

        # 7. Commitment to Conversation Context Cache Memory
        filtered_response = raw_response
        self.memory.add_message("assistant", filtered_response)
        self._log_interaction(user_input, filtered_response, "PASSED", current_tokens)
        
        return filtered_response

    def _call_llm(self, messages: list, max_tokens: int) -> str:
        """Execute core contextual completion payload with active runtime constraints."""
        try:
            response = self.azure_client.chat.completions.create(
                model=self.deployment_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise RuntimeError(f"Core Inference Pipeline Execution Failure: {str(e)}")

    def _log_interaction(self, user_input: str, response: str, status: str, context_tokens: int):
        """Write transactional structural metric records to target audit stream."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "status": status,
            "metrics": {
                "input_length": len(user_input),
                "output_length": len(response),
                "context_tokens_monitored": context_tokens
            }
        }
        with open(config.LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")

    def reset_conversation(self):
        """Reset active context buffers and reload the initial core personality prompt."""
        self.memory.clear()
        self._init_system_prompt()


def print_banner():
    """Print system boot splash configuration layout."""
    print("=" * 60)
    print("  GreenThumb Gardening Assistant")
    print("  Multi-Layer Defense System Activated")
    print("=" * 60)
    print(f"  Topic: {config.CURRENT_TOPIC}")
    print(f"  Model: {config.MODEL_NAME}")
    print(f"  Embedding Check: {'ENABLED' if config.USE_EMBEDDING_CHECK else 'DISABLED'}")
    print("  Type 'quit', 'bye', or 'exit' to exit; 'reset' to clear conversation")
    print("=" * 60)


def main():
    """Main interactive execution loop."""
    # Validate configuration before starting
    try:
        config.validate_config()
    except AttributeError:
        # validate_config not defined in older config.py
        pass
    except ValueError as e:
        print(f"Configuration Error: {e}")
        return
    
    print_banner()
    
    try:
        chatbot = GardeningChatbot()
        chatbot.check_api_connection()
        print("\nOK Chatbot initialized successfully!")
        print("  You can now start chatting about gardening.\n")
    except Exception as e:
        print(f"\nERROR Failed to initialize chatbot: {e}")
        return

    while True:
        try:
            user_input = input("\nYou: ").strip()
            
            if not user_input:
                continue

            if user_input.lower() in EXIT_COMMANDS:
                print("Goodbye! Happy gardening!")
                break

            if user_input.lower() == "reset":
                chatbot.reset_conversation()
                print("Conversation reset. How can I help you with gardening?")
                continue

            response = chatbot.process_input(user_input)
            print(f"\nGreenThumb: {response}")

        except KeyboardInterrupt:
            print("\nGoodbye! Happy gardening!")
            break
        except EOFError:
            break
        except Exception as e:
            print(f"\nError: {str(e)}")


if __name__ == "__main__":
    main()
