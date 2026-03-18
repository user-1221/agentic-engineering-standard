## Purpose

Search the web using the Brave Search API when the user needs current information.

## When to Use

- User asks about current events or recent information
- User explicitly asks to search the web
- Question requires facts beyond training data

## How to Execute

1. Call the `brave_search` tool with a concise query
2. Format results as a bulleted list with title, URL, and snippet
3. Summarize the key findings in 2-3 sentences
4. Cite sources with URLs

## Error Handling

- **API timeout**: Retry once, then inform user
- **No results**: Suggest alternative search terms
- **Rate limit**: Wait and retry (max 5 searches per turn)
