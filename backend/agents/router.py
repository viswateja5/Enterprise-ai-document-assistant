import re
from pydantic import BaseModel, Field
from services.llm_factory import get_llm
from agents.graph_state import AgentState

class RouteDecision(BaseModel):
    """
    Pydantic schema for structured output classification of query routing.
    """
    intent: str = Field(
        description="Must be exactly one of: 'greeting' (hi/hello/goodbye/what can you do), 'casual' (small talk, jokes, personal chatter), 'document' (questions about uploaded files/papers/docs), 'real_time' (current events, today's news/stocks/sports), 'general_knowledge' (broad concepts, coding help, maths, geography), or 'reasoning' (complex multi-step questions, comparisons between docs and real-time data)"
    )
    decision: str = Field(
        description="Must be exactly one of: 'rag' (for uploaded document queries), 'web' (for real-time stock/news/events), 'llm' (for general reasoning/knowledge/greetings/casual conversation), or 'hybrid' (combining document context and real-time search)"
    )
    query_type: str = Field(
        default="fact",
        description="Must be exactly one of: 'fact' (lookups/basic questions), 'summary' (summarize concepts/chapters/files), 'comparison' (compare differences), or 'study' (worksheets, quizzes, MCQs, flashcards, Revision Sheets)"
    )
    explanation: str = Field(description="Short sentence justifying the choice.")

async def route_query(state: AgentState) -> dict:
    """
    LangGraph routing node. Classifies the query and populates the 'decision', 'intent', and 'query_type' state fields.
    """
    query = state.get("query", "").strip()
    doc_count = state.get("document_count", 0)
    
    if not query:
        return {
            "intent": "casual",
            "decision": "llm", 
            "query_type": "fact", 
            "reasoning_trace": ["Empty query, defaulted to general LLM route."]
        }

    # Fast path regex for common greetings/casual queries to minimize LLM invocation latency
    clean_query = query.lower().strip("?.! ")
    greeting_patterns = [
        r"^(hi|hello|hey|g'day|yo|hi there|hello there)$",
        r"^good\s+(morning|afternoon|evening|night|day)$",
        r"^how\s+are\s+you(\s+doing)?$",
        r"^how's\s+it\s+going$",
        r"^what\s+can\s+you\s+do$",
        r"^who\s+are\s+you$",
        r"^what\s+is\s+your\s+name$",
        r"^(tell\s+me\s+a\s+)?joke$",
        r"^thank\s+you(\s+very\s+much)?$",
        r"^thanks(\s+a\s+lot)?$",
        r"^(bye|goodbye|see\s+you)$"
    ]
    
    is_greeting_match = False
    for pat in greeting_patterns:
        if re.search(pat, clean_query):
            is_greeting_match = True
            break
            
    if is_greeting_match:
        intent = "greeting" if any(w in clean_query for w in ["hi", "hello", "morning", "afternoon", "evening", "you", "name", "do", "features"]) else "casual"
        return {
            "intent": intent,
            "decision": "llm",
            "query_type": "fact",
            "reasoning_trace": state.get("reasoning_trace", []) + [f"Fast-path regex matched: intent='{intent}', decision='llm'."]
        }

    # If no documents are uploaded in the active session, bypass the LLM classifier to save latency.
    if doc_count == 0:
        real_time_keywords = ["weather", "news", "stock", "price", "sport", "score", "today", "current events"]
        is_real_time = any(w in clean_query for w in real_time_keywords)
        intent = "real_time" if is_real_time else "general_knowledge"
        decision = "web" if is_real_time else "llm"
        
        return {
            "intent": intent,
            "decision": decision,
            "query_type": "fact",
            "reasoning_trace": state.get("reasoning_trace", []) + [
                f"Bypassed LLM query classifier because active session has 0 documents. Routed query as '{intent}' -> '{decision}'."
            ]
        }

    system_prompt = (
        "You are an expert query routing agent.\n"
        "Your task is to analyze the user's query and classify it into one of six query intent categories:\n"
        "1. 'greeting': Friendly hello, morning wishes, thank you, goodbye, or asking what the assistant can do.\n"
        "2. 'casual': Small talk, chit-chat, telling a joke, or light banter.\n"
        "3. 'document': The query asks specifically about uploaded files, documents, user papers, or details expected to be in the database context.\n"
        "4. 'real_time': The query asks about real-time events, current news, today's stock prices, sports scores, weather, or technology updates that require a live web search.\n"
        "5. 'general_knowledge': The query asks for general knowledge, coding, programming explanations, recipes, math calculations, or generic logic.\n"
        "6. 'reasoning': The query requires multi-step analysis, logical reasoning, or combining both document context and live web search.\n\n"
        "Based on the intent, map it to one of four routing decisions:\n"
        "- 'rag': For 'document' intent.\n"
        "- 'web': For 'real_time' intent.\n"
        "- 'llm': For 'greeting', 'casual', and 'general_knowledge' intents.\n"
        "- 'hybrid': For 'reasoning' intent.\n\n"
        "You must also classify the style/format of the request into 'query_type':\n"
        "- 'fact': Simple lookup, data point, or single detail inquiry.\n"
        "- 'summary': Requests summarizes, overviews, outlines, or key takeaways.\n"
        "- 'comparison': Comparison of different versions, sections, pros/cons, or differences.\n"
        "- 'study': Requests study materials, MCQs, quiz creation, revision sheets, flashcards, or interview prep.\n\n"
        f"User Query: {query}"
    )

    reasoning_trace = []
    intent = "general_knowledge"
    decision = "llm"
    query_type = "fact"

    try:
        llm = get_llm(streaming=False)
        try:
            structured_llm = llm.with_structured_output(RouteDecision)
            res = await structured_llm.ainvoke(system_prompt)
            intent = res.intent.lower().strip()
            decision = res.decision.lower().strip()
            query_type = res.query_type.lower().strip()
            reasoning_trace.append(f"Structured router intent: '{intent}' / decision: '{decision}' / type: '{query_type}' ({res.explanation})")
        except Exception:
            # Fallback to standard text generation + parsing
            res = await llm.ainvoke(
                f"{system_prompt}\n\nRespond ONLY with a JSON matching this structure: {{\"intent\": \"greeting|casual|document|real_time|general_knowledge|reasoning\", \"decision\": \"rag|web|llm|hybrid\", \"query_type\": \"fact|summary|comparison|study\", \"explanation\": \"...\"}}"
            )
            text = res.content
            match_int = re.search(r'"intent"\s*:\s*"(\w+)"', text)
            match_dec = re.search(r'"decision"\s*:\s*"(\w+)"', text)
            match_type = re.search(r'"query_type"\s*:\s*"(\w+)"', text)
            if match_int:
                intent = match_int.group(1).lower().strip()
            if match_dec:
                decision = match_dec.group(1).lower().strip()
            if match_type:
                query_type = match_type.group(1).lower().strip()
            reasoning_trace.append(f"Text-parsed router intent: '{intent}' / decision: '{decision}' / type: '{query_type}'")
    except Exception as e:
        intent = "general_knowledge"
        decision = "llm"
        query_type = "fact"
        reasoning_trace.append(f"Routing failed with error: {str(e)}. Defaulted to 'llm' fallback.")

    # Clamp decision/intent to valid options
    if intent not in ["greeting", "casual", "document", "real_time", "general_knowledge", "reasoning"]:
        intent = "general_knowledge"
    if decision not in ["rag", "web", "llm", "hybrid"]:
        decision = "llm"
    if query_type not in ["fact", "summary", "comparison", "study"]:
        query_type = "fact"

    return {
        "intent": intent,
        "decision": decision,
        "query_type": query_type,
        "reasoning_trace": state.get("reasoning_trace", []) + reasoning_trace
    }
