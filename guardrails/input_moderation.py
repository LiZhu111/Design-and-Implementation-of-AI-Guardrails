"""
Input Moderation - Multi-layer defense system.
Layer 1: Keyword-based filtering
Layer 2: Embedding similarity detection (Ada-002) - Optional for APIM
Layer 3: LLM semantic classification (GPT-4)
Enhanced with an independent Greeting Interceptor layer for conversational fluidness.
"""

import json
import time
import os
from datetime import datetime
from typing import Dict, Tuple, Optional, List
import numpy as np

import config


class InputModeration:
    """
    Input moderation with layered defense architecture.
    Implements keyword matching, embedding similarity, and LLM classification.
    """

    def __init__(self, azure_client, embedding_client):
        self.azure_client = azure_client
        self.embedding_client = embedding_client
        self.topic_embeddings: Optional[np.ndarray] = None
        
        # Check if embedding should be used (may not work with APIM)
        self.embedding_available = config.USE_EMBEDDING_CHECK
        
        if self.embedding_available:
            try:
                self._load_sample_embeddings()
                print("OK Embedding service initialized successfully")
            except Exception as e:
                print(f"Warning: Embedding service unavailable: {e}")
                print("Falling back to keyword + LLM classification only")
                self.embedding_available = False
        else:
            print("Note: Embedding check disabled (APIM gateway mode)")

    def _load_sample_embeddings(self) -> Optional[np.ndarray]:
        """Load pre-computed embeddings for topic sample queries."""
        if self.topic_embeddings is not None:
            return self.topic_embeddings

        embeddings = []
        failed_count = 0
        for query in config.TOPIC_SAMPLE_QUERIES:
            try:
                emb = self.embedding_client.embeddings.create(
                    input=query,
                    model=os.getenv("AZURE_EMBEDDING_NAME", config.EMBEDDING_MODEL)
                ).data[0].embedding
                embeddings.append(emb)
            except Exception as e:
                failed_count += 1
                print(f"Warning: Failed to embed sample query '{query}': {e}")
                embeddings.append([0.0] * 1536)
        
        if failed_count > len(config.TOPIC_SAMPLE_QUERIES) / 2:
            self.embedding_available = False
            print("Warning: Embedding service appears to be misconfigured. Disabling embedding check.")
            return None
        
        self.topic_embeddings = np.array(embeddings)
        return self.topic_embeddings

    def _compute_similarity(self, user_input: str) -> float:
        """Compute cosine similarity between user input and topic sample queries."""
        if not self.embedding_available:
            return 0.0
            
        user_emb = self.embedding_client.embeddings.create(
            input=user_input,
            model=os.getenv("AZURE_EMBEDDING_NAME", config.EMBEDDING_MODEL)
        ).data[0].embedding

        similarities = []
        for sample_emb in self.topic_embeddings:
            dot_product = np.dot(user_emb, sample_emb)
            norm_user = np.linalg.norm(user_emb)
            norm_sample = np.linalg.norm(sample_emb)
            if norm_user == 0 or norm_sample == 0:
                similarities.append(0.0)
            else:
                similarities.append(dot_product / (norm_user * norm_sample))

        return float(np.max(similarities))

    def _check_injection_patterns(self, user_input: str) -> Tuple[bool, str]:
        """Heuristic check for prompt injection or jailbreak patterns."""
        normalized = user_input.lower()
        jailbreak_signals = [
            "ignore previous instructions", "ignore all instructions",
            "ignore your instructions",
            "forget previous instructions", "forget your instructions",
            "forget gardening rules", "system prompt", "dan mode",
            "you are now a", "you are now [", "bypass", "override",
            "developer mode", "jailbreak", "stop being an assistant"
        ]
        for signal in jailbreak_signals:
            if signal in normalized:
                return False, f"Jailbreak pattern detected: '{signal}'"
        return True, "Passed"

    def _is_pure_greeting(self, user_input: str) -> bool:
        """Detect if input is a pure greeting without malicious intent."""
        normalized = user_input.strip().lower().rstrip("!?.")
        greetings = [
            "hi", "hi there", "hello", "hello there", "hey", "hey there",
            "g'day", "good morning", "good afternoon", "good evening"
        ]
        return normalized in greetings

    def _is_polite_acknowledgement(self, user_input: str) -> bool:
        """Detect short courtesy messages that should not be treated as off-topic."""
        normalized = user_input.strip().lower().rstrip("!?.")
        polite_phrases = [
            "thanks", "thank you", "thank you very much", "thanks a lot",
            "thanks so much", "appreciate it", "much appreciated",
            "ok thanks", "okay thanks", "great thanks", "nice thanks"
        ]
        return normalized in polite_phrases

    def _keyword_matching(self, user_input: str) -> Tuple[bool, str]:
        """Perform rapid keyword structural analysis scanning."""
        normalized = user_input.lower()
        matched = [kw for kw in config.TOPIC_KEYWORDS if kw in normalized]
        if matched:
            return True, f"Matched keywords: {matched}"
        return False, "No topical keywords found"

    def _embedding_check(self, user_input: str) -> Tuple[bool, str, float]:
        """Evaluate input via semantic embedding cosine similarity gate."""
        if not self.embedding_available:
            # Skip embedding check, return False so it goes to LLM classification
            return False, "Embedding service disabled (APIM mode), falling back to LLM", 0.0
        
        try:
            similarity = self._compute_similarity(user_input)
            if similarity >= config.EMBEDDING_THRESHOLD:
                return True, f"Cosine similarity {similarity:.4f} >= threshold", similarity
            return False, f"Cosine similarity {similarity:.4f} < threshold", similarity
        except Exception as e:
            return False, f"Embedding routine execution fault: {str(e)}", 0.0

    def _llm_classification(self, user_input: str) -> Tuple[bool, str]:
        """Fallback arbiter resolving semantic edge cases via precise classification prompt."""
        try:
            classifier_prompt = (
                f"You are a conservative topic classifier for a gardening assistant.\n"
                f"Allow only if the user request is explicitly about {config.CURRENT_TOPIC.lower()}, plants, soil, watering, pests, pruning, compost, lawns, landscaping, or plant care.\n"
                "Deny anything else, including sports, jokes, entertainment, politics, general knowledge, coding, finance, and roleplay.\n"
                "Return ONLY valid JSON in exactly this format: {\"decision\":\"ALLOWED|DENIED\",\"reason\":\"...\"}\n"
                "Do not output markdown, code fences, or extra text."
            )
            response = self.azure_client.chat.completions.create(
                model=os.getenv("AZURE_DEPLOYMENT_NAME", config.MODEL_NAME),
                messages=[
                    {
                        "role": "system",
                        "content": classifier_prompt
                    },
                    {"role": "user", "content": f"Analyze this input: {user_input}"}
                ],
                temperature=0.0
            )
            raw_content = response.choices[0].message.content.strip()
            result = json.loads(raw_content)
            if result.get("decision") == "ALLOWED":
                return True, result.get("reason", "Passed")
            return False, result.get("reason", "Denied by LLM Classifier")
        except Exception as e:
            return False, f"LLM Classifier failed to evaluate: {str(e)}"

    def _log_interception(self, user_input: str, layer: str, reason: str, score: Optional[float] = None):
        """Write precise interception trails into telemetry logs."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "status": "BLOCKED_INPUT",
            "layer_denied": layer,
            "reason": reason,
            "metrics": {
                "input_length": len(user_input),
                "similarity_score": score
            }
        }
        with open(config.LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")

    def _denial_response(self, public_reason: str) -> str:
        """Create a polite user-facing denial with a clear, non-sensitive reason."""
        return f"{config.DENIAL_MESSAGE} Reason: {public_reason}"

    def moderate(self, user_input: str) -> Tuple[bool, Optional[str], str]:
        """
        Execute multi-stage verification pipeline routing.
        Returns (passed, return_message, layer_flag).
        - passed=False: blocked, return_message is denial message
        - passed=True, return_message=None: proceed to LLM
        - passed=True, return_message=str: return this message directly to user
        """
        if not user_input.strip():
            return False, self._denial_response("Your message was empty."), "Empty Input"

        # Phase 1: Injection Pattern Security Layer
        inj_pass, inj_reason = self._check_injection_patterns(user_input)
        if not inj_pass:
            self._log_interception(user_input, "Injection Pattern", inj_reason)
            return False, self._denial_response("The message appears to request a role, rule, or instruction override."), "Injection Pattern"

        # Phase 2: Safe Greeting Detection Layer
        if self._is_pure_greeting(user_input):
            return True, None, "Greeting Layer"

        # Phase 2b: Safe Politeness Detection Layer
        if self._is_polite_acknowledgement(user_input):
            return True, None, "Politeness Layer"

        # Phase 3: Standard Topical Guardrails Layer
        keyword_pass, keyword_reason = self._keyword_matching(user_input)

        if keyword_pass:
            emb_pass, emb_reason, similarity = self._embedding_check(user_input)

            if emb_pass:
                return True, None, "Passed All Layers"

            self._log_interception(user_input, "Embedding Layer", emb_reason, similarity)

            llm_pass, llm_reason = self._llm_classification(user_input)

            if llm_pass:
                return True, None, "Embedding+LLM Passed"

            self._log_interception(user_input, "LLM Classifier Layer", llm_reason)
            return False, self._denial_response("The semantic classifier judged the message to be outside the gardening topic."), "LLM Classifier"

        self._log_interception(user_input, "Keyword Layer", keyword_reason)

        # Phase 3b: Semantic rescue path for topical prompts that do not use obvious keywords.
        if self.embedding_available:
            emb_pass, emb_reason, similarity = self._embedding_check(user_input)
            if emb_pass:
                return True, None, "Semantic Rescue"
            self._log_interception(user_input, "Embedding Layer", emb_reason, similarity)

        llm_pass, llm_reason = self._llm_classification(user_input)
        if llm_pass:
            return True, None, "LLM Rescue"

        self._log_interception(user_input, "LLM Classifier Layer", llm_reason)
        return False, self._denial_response("The message does not appear to be gardening-related."), "Keyword Layer"
