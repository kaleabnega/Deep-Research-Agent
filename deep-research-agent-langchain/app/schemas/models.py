from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class EvidenceConstraints(BaseModel):
    source_types: Optional[List[str]] = None
    time_range: Optional[Dict[str, int]] = None
    quality: Optional[str] = None


class TaskSpec(BaseModel):
    question: str
    audience: str = "general reader"
    max_length: int = 400
    evidence_constraints: Optional[EvidenceConstraints] = None


class SubQuestion(BaseModel):
    text: str
    priority: int = 1
    tactics: List[str] = Field(default_factory=list)
    query_variants: List[str] = Field(default_factory=list)


class Plan(BaseModel):
    sub_questions: List[SubQuestion]
    success_criteria: List[str] = Field(default_factory=list)
    max_iterations: int = 2
    confidence_threshold: float = 0.65
    evidence_constraints: Optional[EvidenceConstraints] = None


class Evidence(BaseModel):
    url: str
    title: str
    snippet: str
    captured_at: str
    source_type: str
    relevance: float
    freshness: float
    trust: float
    score: float


class Claim(BaseModel):
    text: str
    support: List[Evidence]
    uncertainty: str
    confidence: float


class SubQuestionBriefing(BaseModel):
    sub_question: str
    claim: Claim


class Briefing(BaseModel):
    title: str
    overview: str
    findings: List[SubQuestionBriefing]
    uncertainties: List[str]
    sources: List[Evidence]
    metrics: Optional[Dict[str, Any]] = None
