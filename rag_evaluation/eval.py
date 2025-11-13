import json

from langchain_openai import ChatOpenAI
from langchain_openai import AzureChatOpenAI

from langsmith import Client

from typing_extensions import Annotated, TypedDict

 
 
# Load the JSON files

def load_json_data(rag_answers_file, ground_truth_file):

    """Load RAG answers and ground truth from JSON files"""

    with open(rag_answers_file, 'r') as f:

        rag_data = json.load(f)

    with open(ground_truth_file, 'r') as f:

        ground_truth_data = json.load(f)

    return rag_data, ground_truth_data
 
 
# Grade output schemas

class CorrectnessGrade(TypedDict):

    explanation: Annotated[str, ..., "Explain your reasoning for the score"]

    correct: Annotated[bool, ..., "True if the answer is correct, False otherwise."]
 
 
class RelevanceGrade(TypedDict):

    explanation: Annotated[str, ..., "Explain your reasoning for the score"]

    relevant: Annotated[bool, ..., "Provide the score on whether the answer addresses the question"]
 
 
# Grade prompts

correctness_instructions = """You are a teacher grading a quiz. You will be given a QUESTION, the GROUND TRUTH (correct) ANSWER, and the STUDENT ANSWER. Here is the grade criteria to follow:

(1) Grade the student answers based ONLY on their factual accuracy relative to the ground truth answer. (2) Ensure that the student answer does not contain any conflicting statements.

(3) It is OK if the student answer contains more information than the ground truth answer, as long as it is factually accurate relative to the  ground truth answer.
 
Correctness:

A correctness value of True means that the student's answer meets all of the criteria.

A correctness value of False means that the student's answer does not meet all of the criteria.
 
Explain your reasoning in a step-by-step manner to ensure your reasoning and conclusion are correct. Avoid simply stating the correct answer at the outset."""
 
relevance_instructions = """You are a teacher grading a quiz. You will be given a QUESTION and a STUDENT ANSWER. Here is the grade criteria to follow:

(1) Ensure the STUDENT ANSWER is concise and relevant to the QUESTION

(2) Ensure the STUDENT ANSWER helps to answer the QUESTION
 
Relevance:

A relevance value of True means that the student's answer meets all of the criteria.

A relevance value of False means that the student's answer does not meet all of the criteria.
 
Explain your reasoning in a step-by-step manner to ensure your reasoning and conclusion are correct. Avoid simply stating the correct answer at the outset."""
 


# Initialize grader LLMs
endpoint = ""
model_name = "grok-3"
deployment_name = "grok-3"
api_key = ""

correctness_llm = ChatOpenAI(
    base_url=endpoint,
    api_key=api_key,
    model=model_name,
    temperature=0,).with_structured_output(

    CorrectnessGrade, method="json_schema", strict=True

)
 
relevance_llm = ChatOpenAI(
    base_url=endpoint,
    api_key=api_key,
    model=model_name,
    temperature=0,
).with_structured_output(

    RelevanceGrade, method="json_schema", strict=True

)
 
print('\nafter LLMMM\n')
# Evaluator functions

def correctness(question: str, rag_answer: str, ground_truth_answer: str) -> dict:

    """Evaluator for RAG answer accuracy"""

    answers = f"""\

QUESTION: {question}

GROUND TRUTH ANSWER: {ground_truth_answer}

STUDENT ANSWER: {rag_answer}"""

    grade = correctness_llm.invoke([

        {"role": "system", "content": correctness_instructions},

        {"role": "user", "content": answers},

    ])

    return grade
 
 
def relevance(question: str, rag_answer: str) -> dict:

    """Evaluator for RAG answer relevance"""

    answer = f"QUESTION: {question}\nSTUDENT ANSWER: {rag_answer}"

    grade = relevance_llm.invoke([

        {"role": "system", "content": relevance_instructions},

        {"role": "user", "content": answer},

    ])

    return grade
 
 
def evaluate_from_json(rag_answers_file: str, ground_truth_file: str, use_langsmith: bool = True):

    """Main evaluation function that processes JSON files and runs evaluations"""

    # Load data

    rag_data, ground_truth_data = load_json_data(rag_answers_file, ground_truth_file)

    # Create a mapping for ground truth by question

    gt_mapping = {}

    if isinstance(ground_truth_data, list):

        # If ground truth is a list of {question, answer} objects

        gt_mapping = {item['question']: item['answer'] for item in ground_truth_data}

    elif isinstance(ground_truth_data, dict):

        # If ground truth is a dict with questions as keys

        gt_mapping = ground_truth_data

    results = []

    # Process each RAG result

    for item in rag_data:

        # Extract data based on structure

        if isinstance(item, dict):

            question = item.get('question', item.get('query', ''))

            rag_answer = item.get('answer', item.get('response', ''))

        else:

            print(f"Unexpected item format: {item}")

            continue

        # Get ground truth answer

        ground_truth_answer = gt_mapping.get(question, '')

        if not ground_truth_answer:

            print(f"Warning: No ground truth found for question: {question}")

            continue

        # Run evaluations

        eval_result = {

            'question': question,

            'rag_answer': rag_answer,

            'ground_truth': ground_truth_answer,

            'evaluations': {}

        }

        # Correctness evaluation

        correctness_result = correctness(question, rag_answer, ground_truth_answer)

        eval_result['evaluations']['correctness'] = {

            'score': correctness_result['correct'],

            'explanation': correctness_result['explanation']

        }

        # Relevance evaluation

        relevance_result = relevance(question, rag_answer)

        eval_result['evaluations']['relevance'] = {

            'score': relevance_result['relevant'],

            'explanation': relevance_result['explanation']

        }
        print(f"processing: {len(results)}\n")
        results.append(eval_result)

    # Calculate summary metrics

    summary = calculate_summary_metrics(results)

    # Optionally log to LangSmith

    if use_langsmith:

        log_to_langsmith(results, summary)

    return results, summary
 
 
def calculate_summary_metrics(results):

    """Calculate summary metrics from evaluation results"""

    metrics = {

        'total_evaluated': len(results),

        'correctness': {'passed': 0, 'total': 0, 'percentage': 0},

        'relevance': {'passed': 0, 'total': 0, 'percentage': 0}

    }

    for result in results:

        evals = result['evaluations']

        for metric_name in ['correctness', 'relevance']:

            if metric_name in evals:

                metrics[metric_name]['total'] += 1

                if evals[metric_name]['score']:

                    metrics[metric_name]['passed'] += 1

    # Calculate percentages

    for metric_name in ['correctness', 'relevance']:

        if metrics[metric_name]['total'] > 0:

            metrics[metric_name]['percentage'] = (

                metrics[metric_name]['passed'] / metrics[metric_name]['total'] * 100

            )

    return metrics
 
 
def log_to_langsmith(results, summary):

    """Log results to LangSmith"""

    try:

        client = Client()

        # Create a dataset if needed

        dataset_name = "RAG Evaluation from JSON"

        if not client.has_dataset(dataset_name=dataset_name):

            dataset = client.create_dataset(dataset_name=dataset_name)

        print(f"Logged {len(results)} evaluations to LangSmith")

        print(f"Summary: {summary}")

    except Exception as e:

        print(f"Warning: Could not log to LangSmith: {e}")
 
 
def save_results(results, summary, output_file="evaluation_results.json"):

    """Save evaluation results to a JSON file"""

    output = {

        'summary': summary,

        'detailed_results': results

    }

    with open(output_file, 'w') as f:

        json.dump(output, f, indent=2)

    print(f"Results saved to {output_file}")
 
 
# Example of expected JSON formats

"""

Example rag_answers.json format:

[

  {

    "question": "What is machine learning?",

    "answer": "Machine learning is a subset of artificial intelligence..."

  },

  {

    "question": "What is Python?",

    "answer": "Python is a high-level programming language..."

  }

]
 
Example ground_truth.json format:

[

  {

    "question": "What is machine learning?",

    "answer": "Machine learning is a field of AI that..."

  },

  {

    "question": "What is Python?",

    "answer": "Python is a programming language..."

  }

]

"""
 
 
# Main execution

if __name__ == "__main__":
    print('\n in main\n')

    # Replace these with your actual file paths

    RAG_ANSWERS_FILE = "/home/lujain/Desktop/kaust_file/gitrepo/HR_Agent/rag_evaluation/agent_answers_A.json"

    GROUND_TRUTH_FILE = "/home/lujain/Desktop/kaust_file/gitrepo/HR_Agent/rag_evaluation/questions_A.json"

    # Run evaluation

    results, summary = evaluate_from_json(

        RAG_ANSWERS_FILE, 

        GROUND_TRUTH_FILE,

        use_langsmith=False  # Set to False if you don't want to use LangSmith

    )

    # Save results

    save_results(results, summary)

    # Print summary

    print("\n=== Evaluation Summary ===")

    print(f"Total questions evaluated: {summary['total_evaluated']}")

    print(f"\nCorrectness: {summary['correctness']['passed']}/{summary['correctness']['total']} "

          f"({summary['correctness']['percentage']:.1f}%)")

    print(f"Relevance: {summary['relevance']['passed']}/{summary['relevance']['total']} "

          f"({summary['relevance']['percentage']:.1f}%)")
 