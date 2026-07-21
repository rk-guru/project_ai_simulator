

deep_agent_prompt="""
# Project Files Q&A workflow
Answer questions using the indexed project files.
1. **Plan**: Use write_todos to break complex questions into focused search queries.
2. **Search**: Call search_project_files with a query .
3. **Analyze**: Delegate each chunk file to the chunk-analyst subagent with task().
for question check if the data is already present in the rag information
Do not answer from memory when file evidence is required. Search first.




"""
#
# from ai_tools import get_flow_diagram_from_db
# import json
#
# project_id="73b19ca3-d2a0-4c98-9ee2-5acb8faabc9f"
# diagram_data = get_flow_diagram_from_db(project_id)
# print( json.dumps(diagram_data, indent=2))