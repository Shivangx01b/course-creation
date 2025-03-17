

from core.data_type import SummaryState, SummaryStateInput, SummaryStateOutput, FinalReport,  LLMJSON, LLMJSONFollow, LLMJSONTitles
from core.prompt import query_writer_instructions, summarizer_instructions, reflection_instructions, titles_generation_instructions
from core.utils import tavily_search, deduplicate_and_format_sources, format_sources, Configuration

from langchain_openai import ChatOpenAI
import json

from typing_extensions import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from langgraph.graph import START, END, StateGraph
from langchain_core.runnables import RunnableConfig
from langchain_core.output_parsers import JsonOutputParser

import os



llm = ChatOpenAI(model="gpt-4-turbo", temperature=0)

llm_json_mode = llm.with_structured_output(LLMJSON, method="json_mode")
llm_json_mode_follow = llm.with_structured_output(LLMJSONFollow, method="json_mode")
llm_json_mode_title = llm.with_structured_output(LLMJSONTitles, method="json_mode")



#Nodes
def generate_query(state: SummaryState):
    """ Generate a query for web search """

    # Format the prompt
    query_writer_instructions_formatted = query_writer_instructions.format(research_topic=state.research_topic)

    # Generate a query
    result = llm_json_mode.invoke(
        [SystemMessage(content=query_writer_instructions_formatted),
        HumanMessage(content=f"Generate a query for web search:")]
    )
    
    query = result
    
    
    return {"search_query": query.query}

def web_research(state: SummaryState):
    """ Gather information from the web """

    
    search_results = tavily_search(state.search_query, include_raw_content=True, max_results=1)
    search_str = deduplicate_and_format_sources(search_results, max_tokens_per_source=1000, include_raw_content=True)
    
    return {"sources_gathered": [format_sources(search_results)], "research_loop_count": state.research_loop_count + 1, "web_research_results": [search_str]}

def summarize_sources(state: SummaryState):
    """ Summarize the gathered sources """

    # Existing summary
    existing_summary = state.running_summary

    # Most recent web research
    most_recent_web_research = state.web_research_results[-1]

    # Build the human message
    if existing_summary:
        human_message_content = (
            f"<User Input> \n {state.research_topic} \n <User Input>\n\n"
            f"<Existing Summary> \n {existing_summary} \n <Existing Summary>\n\n"
            f"<New Search Results> \n {most_recent_web_research} \n <New Search Results>"
        )
    else:
        human_message_content = (
            f"<User Input> \n {state.research_topic} \n <User Input>\n\n"
            f"<Search Results> \n {most_recent_web_research} \n <Search Results>"
        )

    # Run the LLM
    result = llm.invoke(
        [SystemMessage(content=summarizer_instructions),
        HumanMessage(content=human_message_content)]
    )

    running_summary = result.content
    return {"running_summary": running_summary}

def reflect_on_summary(state: SummaryState):
    """ Reflect on the summary and generate a follow-up query """

    result = llm_json_mode_follow.invoke(
        [SystemMessage(content=reflection_instructions.format(research_topic=state.research_topic)),
        HumanMessage(content=f"Identify a knowledge gap and generate a follow-up web search query based on our existing knowledge: {state.running_summary}")]
    )
    follow_up_query = result

    # Get the follow-up query
    query = follow_up_query.follow_up_query

    # JSON mode can fail in some cases
    if not query:

        # Fallback to a placeholder query
        return {"search_query": f"Tell me more about {state.research_topic}"}

    # Update search query with follow-up query
    return {"search_query": follow_up_query.follow_up_query}

def route_research(state: SummaryState, config: RunnableConfig) -> Literal["finalize_summary", "web_research"]:
    """ Route the research based on the follow-up query """

    configurable = Configuration.from_runnable_config(config)
    if state.research_loop_count <= int(configurable.max_web_research_loops):
        return "web_research"
    else:
        return "finalize_summary"

def finalize_summary(state: SummaryState):
    """ Finalize the summary """

    # Format all accumulated sources into a single bulleted list
    all_sources = "\n".join(source for source in state.sources_gathered)
    state.running_summary = f"## Summary\n\n{state.running_summary}\n\n ### Sources:\n{all_sources}"
    
    return {"running_summary": state.running_summary}

def create_titles(state: SummaryState):
    """ Create titles for the courses from the summary"""
    summary_made = state.running_summary
    result = llm_json_mode_title.invoke(
        [SystemMessage(content=titles_generation_instructions.format(summary_data=summary_made)),
        HumanMessage(content=f"Generate list of modules which would be required to make a course on this knowledge: {summary_made}")]
    )
    titles = result.titles
    all_sources = "\n".join(source for source in state.sources_gathered)
    content = titles
    return {"title_list": content}



def create_content(state:SummaryState):
    """Create content from the list of titles"""
    titles = state.title_list
    print("Titles", titles)
    state.title_count = len(titles)
    final_course_content = []
    for title in titles:
        # Format the prompt
        print("Title", title)
        query_writer_instructions_formatted = query_writer_instructions.format(research_topic=title)

        # Generate a query
        result = llm_json_mode.invoke(
            [SystemMessage(content=query_writer_instructions_formatted),
            HumanMessage(content=f"Generate a query for web search:")]
        )
        
        query = result
        

        # Call web search
        search_results = tavily_search(query.query, include_raw_content=True, max_results=1)
        search_str = deduplicate_and_format_sources(search_results, max_tokens_per_source=1000, include_raw_content=True)
        web_research_results = search_str
        #summarize the results
        
        existing_summary = ""

        # Most recent web research
        most_recent_web_research = web_research_results[-1]

        # Build the human message
        if existing_summary:
            human_message_content = (
                f"<User Input> \n {title} \n <User Input>\n\n"
                f"<Existing Summary> \n {existing_summary} \n <Existing Summary>\n\n"
                f"<New Search Results> \n {most_recent_web_research} \n <New Search Results>"
            )
        else:
            human_message_content = (
                f"<User Input> \n {title} \n <User Input>\n\n"
                f"<Search Results> \n {most_recent_web_research} \n <Search Results>"
            )

        # Run the LLM
        result = llm.invoke(
            [SystemMessage(content=summarizer_instructions),
            HumanMessage(content=human_message_content)]
        )

        result_generated = {
            "title": title,
            "content": result.content,
            "sources": [format_sources(search_results)]
        }

        print("Report =============================================")
        print("Title: ", title)
        print("Content: ", result.content)
        print("Sources: ", [format_sources(search_results)])
        print("END ===============================================\n")
        final_course_content.append(result_generated)
        
    # Format all accumulated sources into a single bulleted list
    all_sources = "\n".join(source for source in state.sources_gathered)
    final_output = f"### Summary\n\n{state.running_summary}\n\n ### Course Content\n\n{final_course_content} ### Sources:\n{all_sources}"
    return {"course_content": final_output}


def handler(topic):
    # Add nodes and edges
    builder = StateGraph(SummaryState, input=SummaryStateInput, output=FinalReport, config_schema=Configuration)
    builder.add_node("generate_query", generate_query)
    builder.add_node("web_research", web_research)
    builder.add_node("summarize_sources", summarize_sources)
    builder.add_node("reflect_on_summary", reflect_on_summary)
    builder.add_node("finalize_summary", finalize_summary)

    builder.add_node("title_generation", create_titles)

    builder.add_node("content_create",  create_content)




    # Add edges
    builder.add_edge(START, "generate_query")
    builder.add_edge("generate_query", "web_research")
    builder.add_edge("web_research", "summarize_sources")
    builder.add_edge("summarize_sources", "reflect_on_summary")
    builder.add_conditional_edges("reflect_on_summary", route_research)

    builder.add_edge("finalize_summary", "title_generation")
    builder.add_edge("title_generation", "content_create")
    builder.add_edge("content_create", END)
    graph = builder.compile()

    research_input = SummaryStateInput(research_topic=topic)
    summary = graph.invoke(research_input)
    return summary

    



    




