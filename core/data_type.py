import operator
from dataclasses import dataclass, field
from typing_extensions import TypedDict, Annotated
from typing import Annotated, List, TypedDict, Literal
from pydantic import BaseModel, Field

@dataclass(kw_only=True)
class SummaryState:
    research_topic: str = field(default=None) # Report topic     
    search_query: str = field(default=None) # Search query
    title_list: list = field(default=None)  
    contents: str = field(default=None) # Content of each title
    web_research_results: Annotated[list, operator.add] = field(default_factory=list) 
    sources_gathered: Annotated[list, operator.add] = field(default_factory=list) 
    research_loop_count: int = field(default=0) # Research loop count
    running_summary: str = field(default=None) # Final report
    title_count: int = field(default=0)
    

@dataclass(kw_only=True)
class SummaryStateInput:
    research_topic: str = field(default=None) # Report topic     

@dataclass(kw_only=True)
class SummaryStateOutput:
    running_summary: str = field(default=None) # Final report

@dataclass(kw_only=True)
class FinalReport:
    course_content: str = field(default=None)


class LLMJSONFollow(BaseModel):
    follow_up_query: str = Field(
        description="The follow up query generated from the exisiting knowledge"
    )

class LLMJSON(BaseModel):
    query: str = Field(
        description="The generated query for web search",
    )

class LLMJSONTitles(BaseModel):
    titles: list = Field(
        description="The generated list of titles for the course based on the exisiting summary or knowledge"
    )