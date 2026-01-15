"""
Pydantic Models for API
========================
Shared data models used across different route modules.
"""

from pydantic import BaseModel, Field
from typing import List, Literal


class ChatMessage(BaseModel):
    """Message to be processed by the multi-agent system"""
    content: str = Field(
        ..., 
        description="The message content to be processed",
        example="Analyze the DV360 campaign performance for last month"
    )
    user_email: str = Field(
        ..., 
        description="User's email address for conversation tracking",
        example="user@company.com"
    )
    partner: str = Field(
        ..., 
        description="Partner name for context",
        example="Google DV360"
    )
    use_memory: bool = Field(
        default=True,
        description="Whether to use conversation history and memory for this message",
        example=True
    )


class DownloadLink(BaseModel):
    """Download link with label"""
    url: str = Field(..., description="Download URL")
    label: str = Field(..., description="Link label/description")


class AdamChatResponse(BaseModel):
    """Response from the multi-agent system"""
    response: str = Field(
        ..., 
        description="AI-generated response to the user's message",
        example="Based on your DV360 data analysis, I found several optimization opportunities..."
    )
    conversation_id: str = Field(
        ..., 
        description="Unique conversation identifier",
        example="conv_12345_20240918"
    )
    timestamp: str = Field(
        ..., 
        description="Response timestamp in ISO format",
        example="2024-09-18T10:30:00"
    )
    download_links: List[DownloadLink] = Field(
        default=[],
        description="List of downloadable files generated during processing"
    )


class HistoryRequest(BaseModel):
    """Request to retrieve conversation history for a user-partner combination"""
    user_email: str = Field(
        ..., 
        description="User's email address to retrieve history for",
        example="user@company.com"
    )
    partner: str = Field(
        default="Default Partner",
        description="Partner name for conversation isolation",
        example="Acme Corp"
    )


class ResetRequest(BaseModel):
    """Request to reset user's conversation for a specific partner"""
    user_email: str = Field(
        ..., 
        description="User's email address to reset conversation for",
        example="user@company.com"
    )
    partner: str = Field(
        default="Default Partner",
        description="Partner name for conversation isolation",
        example="Acme Corp"
    )


class Feedback(BaseModel):
    """User feedback on AI responses"""
    user_query: str = Field(
        ..., 
        description="Original user query",
        example="Analyze campaign performance"
    )
    ai_response: str = Field(
        ..., 
        description="AI response that user is providing feedback on",
        example="Your campaign shows 15% improvement..."
    )
    feedback: str = Field(
        ..., 
        description="User's feedback text",
        example="This analysis was very helpful and accurate"
    )
    partner_name: str = Field(
        ..., 
        description="Partner name",
        example="Google DV360"
    )
    user_email: str = Field(
        ..., 
        description="User's email address",
        example="user@company.com"
    )
    sentiment: Literal['positive', 'negative', 'neutral'] = Field(
        ..., 
        description="Feedback sentiment classification"
    )


class ConfigRequest(BaseModel):
    """Configuration update request"""
    setting_name: str = Field(
        ..., 
        description="Name of the setting to update",
        example="conversation_history_limit"
    )
    setting_value: str = Field(
        ..., 
        description="New value for the setting",
        example="50"
    )


class CsvDataResponse(BaseModel):
    """Response for CSV data preview with pagination"""
    headers: List[str] = Field(
        ...,
        description="Column headers from the CSV file"
    )
    rows: List[List[str]] = Field(
        ...,
        description="Data rows from the CSV file"
    )
    total_rows: int = Field(
        ...,
        description="Total number of rows in the CSV file"
    )
    offset: int = Field(
        ...,
        description="Current offset (starting row)"
    )
    limit: int = Field(
        ...,
        description="Number of rows returned"
    )
    has_more: bool = Field(
        ...,
        description="Whether there are more rows available"
    )

