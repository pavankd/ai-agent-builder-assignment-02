from langchain_community.tools.tavily_search import TavilySearchResults


def search_web(query: str) -> str:
    tool = TavilySearchResults(max_results=5)
    results = tool.invoke({"query": query})

    if not isinstance(results, list):
        return str(results)

    lines = []
    for item in results:
        if isinstance(item, dict):
            title = item.get("title", "")
            content = item.get("content", "")[:400]
            lines.append(f"• {title}: {content}")
    return "\n".join(lines) if lines else "No results found."
