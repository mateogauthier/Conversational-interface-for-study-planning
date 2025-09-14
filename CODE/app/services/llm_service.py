"""LLM service for Ollama integration."""

import json
import logging
import requests
from typing import Optional, Dict, Any, List
from requests.exceptions import RequestException, ConnectionError, Timeout

from app.core.config import get_settings
from app.core.exceptions import LLMException, LLMNotAvailableHTTPException

logger = logging.getLogger(__name__)
settings = get_settings()


class LLMService:
    """Service for LLM operations using Ollama."""
    
    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.default_model = settings.ollama_model
        self.timeout = settings.ollama_timeout
    
    def is_available(self) -> bool:
        """Check if Ollama service is available."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except (RequestException, ConnectionError, Timeout):
            return False
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """Get list of available models."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            return data.get("models", [])
            
        except (RequestException, ConnectionError, Timeout) as e:
            logger.error(f"Error getting models: {str(e)}")
            raise LLMNotAvailableHTTPException(f"Cannot connect to Ollama: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error getting models: {str(e)}")
            raise LLMException(f"Error getting models: {str(e)}")
    
    def model_exists(self, model: str) -> bool:
        """Check if a specific model exists."""
        try:
            models = self.get_available_models()
            return any(m.get("name", "").startswith(model) for m in models)
        except Exception:
            return False
    
    def ensure_model(self, model: str) -> bool:
        """Ensure a model is available, pull if necessary."""
        try:
            if self.model_exists(model):
                return True
            
            logger.info(f"Model {model} not found, attempting to pull...")
            pull_url = f"{self.base_url}/api/pull"
            
            response = requests.post(
                pull_url, 
                json={"name": model}, 
                timeout=300  # 5 minutes for model pulling
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully pulled model {model}")
                return True
            else:
                logger.error(f"Failed to pull model {model}: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error ensuring model {model}: {str(e)}")
            return False
    
    def generate_response(self, prompt: str, model: Optional[str] = None) -> Dict[str, Any]:
        """Generate a response using Ollama."""
        if not self.is_available():
            raise LLMNotAvailableHTTPException("Ollama service is not available")
        
        model = model or self.default_model
        
        try:
            # Ensure model is available
            if not self.ensure_model(model):
                logger.warning(f"Model {model} not available, falling back to {self.default_model}")
                model = self.default_model
                if not self.ensure_model(model):
                    raise LLMException(f"Default model {self.default_model} is not available")
            
            # Generate response
            url = f"{self.base_url}/api/generate"
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": True
            }
            
            response = requests.post(url, json=payload, stream=True, timeout=self.timeout)
            response.raise_for_status()
            
            # Process streaming response
            fragments = []
            for line in response.iter_lines():
                if line:
                    try:
                        decoded = line.decode('utf-8')
                        obj = json.loads(decoded)
                        fragment = obj.get("response", "")
                        fragments.append(fragment)
                        
                        # Check if this is the last chunk
                        if obj.get("done", False):
                            break
                            
                    except json.JSONDecodeError:
                        continue
            
            answer = "".join(fragments)
            
            if not answer.strip():
                raise LLMException("Empty response received from LLM")
            
            return {
                "response": answer,
                "model_used": model
            }
            
        except (RequestException, ConnectionError, Timeout) as e:
            logger.error(f"Error querying Ollama: {str(e)}")
            raise LLMNotAvailableHTTPException(f"Cannot connect to Ollama: {str(e)}")
        except LLMException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in LLM query: {str(e)}")
            raise LLMException(f"Error generating response: {str(e)}")
    
    def generate_with_context(self, prompt: str, context: str, model: Optional[str] = None) -> Dict[str, Any]:
        """Generate a response with provided context."""
        enhanced_prompt = f"""Based on the following context, please answer the question:

Context:
{context}

Question: {prompt}

Please provide a comprehensive answer based on the context provided above."""
        
        return self.generate_response(enhanced_prompt, model)
    
    def get_service_info(self) -> Dict[str, Any]:
        """Get information about the LLM service."""
        try:
            is_available = self.is_available()
            
            info = {
                "service": "Ollama",
                "base_url": self.base_url,
                "is_available": is_available,
                "default_model": self.default_model
            }
            
            if is_available:
                try:
                    models = self.get_available_models()
                    info["available_models"] = [m.get("name", "") for m in models]
                    info["total_models"] = len(models)
                except Exception:
                    info["available_models"] = []
                    info["total_models"] = 0
            
            return info
            
        except Exception as e:
            logger.error(f"Error getting service info: {str(e)}")
            return {
                "service": "Ollama",
                "base_url": self.base_url,
                "is_available": False,
                "error": str(e)
            }


# Global LLM service instance
llm_service = LLMService()
