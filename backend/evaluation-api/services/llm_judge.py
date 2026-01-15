"""
LLM Judge Evaluator
===================
Evaluates ADAM agent responses using LLM-as-a-judge.
"""

import json
import re
import logging
from typing import Dict
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class EvaluationResult(BaseModel):
    """Structured output for LLM-as-a-judge evaluation"""
    score: int = Field(
        description="Score from 0-100 evaluating how well the response addresses the question and follows instructions"
    )
    reasoning: str = Field(
        description="Detailed explanation of the score, highlighting strengths and weaknesses"
    )


class ADAMEvaluator:
    """Evaluates ADAM agent responses using LLM-as-a-judge"""
    
    def __init__(self, model_name: str = "gemini-flash-latest"):
        """
        Initialize the evaluator with an LLM judge.
        
        Args:
            model_name: Gemini model to use for judging
        """
        self.judge_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert evaluator for an AI agent called ADAM that analyzes advertising campaign data.

Your task is to evaluate ADAM's response against a reference output or evaluation instruction.

Evaluation Criteria:
1. Accuracy: Does the response correctly address the user's question?
2. Completeness: Does it cover all aspects mentioned in the reference/instruction?
3. Clarity: Is the response clear and well-structured?
4. Data Quality: If data/tables are provided, are they accurate and relevant?
5. Actionability: Does it provide useful insights or next steps?

Score from 0-100:
- 90-100: Excellent - Meets or exceeds all criteria
- 70-89: Good - Meets most criteria with minor issues
- 50-69: Adequate - Meets some criteria but has notable gaps
- 30-49: Poor - Significant issues or missing key information
- 0-29: Very Poor - Fails to address the question appropriately

Be objective and provide specific reasoning for your score.

You MUST respond with a valid JSON object in the following format:
{{
  "score": <number from 0-100>,
  "reasoning": "<detailed explanation of the score>"
}}"""),
            ("human", """Reference Input (User Question):
{reference_input}

Reference Output / Evaluation Instruction:
{reference_output}

ADAM's Actual Response:
{adam_response}

Evaluate ADAM's response and provide a score (0-100) with detailed reasoning in JSON format.""")
        ])
        
        self.llm = ChatGoogleGenerativeAI(model=model_name, temperature=0)
        
        # Try to use structured output if supported, otherwise will parse JSON manually
        try:
            self.judge = self.judge_prompt | self.llm.with_structured_output(EvaluationResult)
            self.use_structured_output = True
        except Exception:
            # Fallback to manual JSON parsing
            self.judge = self.judge_prompt | self.llm
            self.use_structured_output = False
            logger.info("⚠️  Structured output not supported, will parse JSON manually")
    
    def evaluate_response(
        self, 
        reference_input: str, 
        reference_output: str, 
        adam_response: str
    ) -> Dict:
        """
        Evaluates ADAM's response using LLM-as-a-judge.
        
        Args:
            reference_input: The question/input given to ADAM
            reference_output: Expected output or evaluation instructions
            adam_response: ADAM's actual response
            
        Returns:
            Dict with 'score' (int) and 'feedback' (str)
        """
        try:
            result = self.judge.invoke({
                "reference_input": reference_input,
                "reference_output": reference_output,
                "adam_response": adam_response
            })
            
            # Handle structured output
            if self.use_structured_output and hasattr(result, 'score'):
                return {
                    "score": result.score,
                    "feedback": result.reasoning
                }
            
            # Handle manual JSON parsing
            else:
                # Extract content from AIMessage if needed
                if hasattr(result, 'content'):
                    content = result.content
                else:
                    content = str(result)
                
                # Try to find JSON in the response
                json_match = re.search(r'\{[\s\S]*"score"[\s\S]*"reasoning"[\s\S]*\}', content)
                if json_match:
                    json_str = json_match.group(0)
                    eval_data = json.loads(json_str)
                    return {
                        "score": int(eval_data.get("score", 0)),
                        "feedback": eval_data.get("reasoning", content)
                    }
                
                # If no JSON found, try to parse score from text
                score_match = re.search(r'(?:score|Score)[:=\s]+(\d+)', content)
                score = int(score_match.group(1)) if score_match else 50
                
                return {
                    "score": score,
                    "feedback": content
                }
            
        except Exception as e:
            logger.error(f"Error in LLM judge evaluation: {e}")
            import traceback
            traceback.print_exc()
            return {
                "score": 0,
                "feedback": f"Evaluation failed: {str(e)}"
            }
    
    async def evaluate_response_async(
        self, 
        reference_input: str, 
        reference_output: str, 
        adam_response: str
    ) -> Dict:
        """
        Async version: Evaluates ADAM's response using LLM-as-a-judge.
        
        Args:
            reference_input: The question/input given to ADAM
            reference_output: Expected output or evaluation instructions
            adam_response: ADAM's actual response
            
        Returns:
            Dict with 'score' (int) and 'feedback' (str)
        """
        try:
            # Use ainvoke for async operations
            result = await self.judge.ainvoke({
                "reference_input": reference_input,
                "reference_output": reference_output,
                "adam_response": adam_response
            })
            
            # Handle structured output
            if self.use_structured_output and hasattr(result, 'score'):
                return {
                    "score": result.score,
                    "feedback": result.reasoning
                }
            
            # Handle manual JSON parsing
            else:
                # Extract content from AIMessage if needed
                if hasattr(result, 'content'):
                    content = result.content
                else:
                    content = str(result)
                
                # Try to find JSON in the response
                json_match = re.search(r'\{[\s\S]*"score"[\s\S]*"reasoning"[\s\S]*\}', content)
                if json_match:
                    json_str = json_match.group(0)
                    eval_data = json.loads(json_str)
                    return {
                        "score": int(eval_data.get("score", 0)),
                        "feedback": eval_data.get("reasoning", content)
                    }
                
                # If no JSON found, try to parse score from text
                score_match = re.search(r'(?:score|Score)[:=\s]+(\d+)', content)
                score = int(score_match.group(1)) if score_match else 50
                
                return {
                    "score": score,
                    "feedback": content
                }
            
        except Exception as e:
            logger.error(f"Error in async LLM judge evaluation: {e}")
            import traceback
            traceback.print_exc()
            return {
                "score": 0,
                "feedback": f"Evaluation failed: {str(e)}"
            }

