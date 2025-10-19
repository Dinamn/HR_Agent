# HR_Agent

A smart HR assistant that helps employees interact with company systems using natural language

---

## 🚀 Core Features

### 🧠 Personalized Responses
Understands the employee’s data (from SAP) and answers questions such as:
- “How many vacation days do I have left?”

### ⚙️ Action Automation
Executes HR tasks on behalf of the user, such as:
- Applying for leave  
- Submitting work-from-home forms  

### 📘 Policy-Aware Q&A
Retrieves and interprets policies (PDFs, documents, etc.) to answer questions like:
- “What’s the maternity leave policy?”
- “Can I carry over unused vacation days?”

---

## 🧩 Tech Stack

| Component | Technology |
|------------|-------------|
| **Backend** | Python, LangGraph |
| **LLM** | OpenAI GPT |
| **Data Sources** | Saudi Law policy documents (via RAG) |
| **Frontend** | TBD (for demo) |

---

## 🎯 Vision
To create an **AI-driven HR copilot** that automates repetitive employee tasks, answers policy questions intelligently, and improves HR accessibility across organizations.

---

## 🧪 Example Query Flow

```text
User: "Apply for 3 days of leave next week."

HR Agent:
- Reads user data from SAP
- Checks leave balance
- Applies leave automatically
- Confirms via natural language response
