

deep_agent_prompt="""
# Project Files Q&A workflow
Answer questions using the indexed project files.
1. **Plan**: Use write_todos to break complex questions into focused search queries.
2. **Search**: Call search_project_files with a query .
3. **Analyze**: Delegate each chunk file to the chunk-analyst subagent with task().
for question check if the data is already present in the rag information
Do not answer from memory when file evidence is required. Search first.




"""

def flowdiagram_prompt(reference_structure):
    prompt=f"""consider you are a chemical engineering assistant and you are generating a simulation diagram for a process plant .
    use the reference structure as the base for the return structure where the model should follow for returning
    create id for all equipment with similar structure that it should use the name with numer like Heater_1 , Heater_2
    this is used for equipment id and to specify the outlet connections as well 
    follow exactly what the input provide and generate json with the existing equipment and compounds 
    use the same name for compounds exactly as input
    if recycle is present in the process doesnt recycle the stream instead leave it as product steam 
    reference structure:{reference_structure}
    make sure to return exactly in the reference structure without any symbol or additional comments or message
    """
    return prompt
#
# from ai_tools import get_flow_diagram_from_db
# import json
#
# project_id="73b19ca3-d2a0-4c98-9ee2-5acb8faabc9f"
# diagram_data = get_flow_diagram_from_db(project_id)
# print( json.dumps(diagram_data, indent=2))