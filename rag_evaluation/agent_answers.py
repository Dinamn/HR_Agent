"""
Simple script to read questions from a JSON file, call the agent, 
and save questions and answers to agent_answers.json
"""

import json
from datetime import datetime
import sys

# Now this works:
from .agent import agent_respond


def load_questions(input_file="questions.json"):
    """
    Load questions from a JSON file.
    
    Expected format:
    [
        {"question": "What's my leave balance?"},
        {"question": "Show me my history"},
        ...
    ]
    
    Or simply:
    [
        "What's my leave balance?",
        "Show me my history",
        ...
    ]
    
    Args:
        input_file: Path to the JSON file with questions
    
    Returns:
        List of question strings
    """
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Handle different formats
    questions = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, str):
                questions.append(item)
            elif isinstance(item, dict) and 'question' in item:
                questions.append(item['question'])
            elif isinstance(item, dict) and 'query' in item:
                questions.append(item['query'])
    
    return questions


def get_agent_answer(question, user_id=1, thread_id=None):
    """
    Call the agent and get the answer.
    
    Args:
        question: The user's question
        user_id: User ID for the agent
        thread_id: Thread ID for the conversation (use unique ID for each question to avoid memory carryover)
    
    Returns:
        The agent's answer as a string
    """
    # from KAUST_Agent.app.agent import agent_respond
    
    try:
        answer = agent_respond(question, user_id, thread_id)
        return answer
    except Exception as e:
        return f"Error: {str(e)}"


def process_questions(input_file="questions.json", output_file="agent_answers.json", user_id=1):
    """
    Read questions from input file, get answers from agent, save to output file.
    Each question gets a unique thread ID so there's no memory carryover between questions.
    
    Args:
        input_file: JSON file with questions
        output_file: JSON file to save answers
        user_id: User ID for the agent
    """
    print(f"Loading questions from: {input_file}")
    
    # Load questions
    questions = load_questions(input_file)
    print(f"Loaded {len(questions)} questions\n")
    
    # Process each question
    results = []
    for i, question in enumerate(questions, 1):
        print(f"[{i}/{len(questions)}] Question: {question}")
        
        # Create a unique thread ID for each question to prevent memory carryover
        thread_id = f"question_{i}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        # Get answer from agent
        answer = get_agent_answer(question, user_id, thread_id)
        
        # Save result
        result = {
            "question": question,
            "answer": answer
        }
        results.append(result)
        
        print(f"Answer: {answer[:100]}...\n")
    
    # Save to JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Results saved to: {output_file}")
    print(f"Total: {len(results)} question-answer pairs")
    print(f"Note: Each question used a unique thread ID (no memory carryover)")


if __name__ == "__main__":
    import sys
    
    # Default files
    input_file = "/home/lujain/Desktop/kaust_file/gitrepo/HR_Agent/rag_evaluation/questions_A.json"
    output_file = "/home/lujain/Desktop/kaust_file/gitrepo/HR_Agent/rag_evaluation/agent_answers_A.json"
    user_id = 1
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    if len(sys.argv) > 3:
        user_id = int(sys.argv[3])
    
    # Process
    process_questions(input_file, output_file, user_id)