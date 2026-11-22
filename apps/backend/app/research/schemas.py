from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, SecretStr

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')

class ConnectionInput(Strict):
    api_key: SecretStr
    model: str = Field(default='gpt-5-mini', pattern=r'^[a-zA-Z0-9_.:-]{1,100}$')

class RunInput(Strict):
    competitors: list[str] = Field(default_factory=list, max_length=5)
    customer_notes: str = Field(default='', max_length=15000)

class Plan(Strict):
    objective: str
    questions: list[str]
    market_queries: list[str]
    competitor_queries: list[str]
    completion_criteria: list[str]
    assumptions: list[str]

class ExtractedFinding(Strict):
    source_id: str
    quote: str
    finding: str
    limitation: str

class CompetitorFact(Strict):
    dimension: Literal['positioning', 'features', 'pricing', 'gaps']
    text: str
    source_id: str
    quote: str

class Competitor(Strict):
    name: str
    facts: list[CompetitorFact]

class Analysis(Strict):
    findings: list[ExtractedFinding]
    competitors: list[Competitor]
    gaps: list[str]

class Claim(Strict):
    id: str
    type: Literal['observation', 'inference', 'hypothesis', 'experiment']
    text: str
    evidence_ids: list[str]
    limitation: str

class Section(Strict):
    id: Literal['summary', 'market', 'customers', 'opportunities', 'validation']
    title: str
    eyebrow: str
    blocks: list[Claim]

class Draft(Strict):
    title: str
    subtitle: str
    sections: list[Section]
    limitations: list[str]

class ClaimReview(Strict):
    claim_id: str
    supported: bool
    reason: str

class Review(Strict):
    claims: list[ClaimReview]
    gaps: list[str]
