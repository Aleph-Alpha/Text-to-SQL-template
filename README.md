# Text-to-SQL Workshop

## Task

Build, benchmark, and deploy a **Text-to-SQL Skill**, then integrate it into a complete application and deploy to Pharia Assistant.

You will create a PhariaAI skill that translates natural language to SQL queries:

**Your Task**: Build a **SQL Generation Skill** that:
- Accepts natural language questions and translates them into SQL queries using RAG and few-shot learning
- Achieves >70% accuracy on the provided test set
- Integrates seamlessly with the pre-built backend and frontend

The deployed application will:
- Accept natural language questions in a chat-like input (e.g., *"Show me the top 5 customers by total orders"*)
- Translate questions into SQL queries using **your PhariaAI skill**
- Execute SQL queries against the Northwind database
- Display results in a user-friendly table format
- Generate interactive charts from the data (using the pre-built chart generation skill)
- Be accessible as a **custom application inside Pharia Assistant**

**Key Challenge**: Accurately translate diverse natural language queries into correct SQL statements, handling various query complexities from simple selections to complex joins and aggregations.

**Deliverables**

- A functioning SQL generation skill that generates valid SQL queries
- Benchmarked solution demonstrating high accuracy on the provided test set
- SQL skill deployed to PhariaKernel and integrated with the backend
- **Complete application deployed and accessible in Pharia Assistant**
- Present your solution at the end of the workshop

**Tools & Data Provided**

- **Document Index Collection**: 1000+ curated question/SQL pairs ready for few-shot learning (namespace: `Studio`, collection: `text-to-sql-examples`, index=`asym-1024`)
- **Database**: Classic Northwind database (SQLite3) simulating an e-commerce dataset
- **Test Dataset**: 100+ curated test examples with 5 different database schemas for evaluation in [`skill/evaluation/test-data/test_split.json`](skill/evaluation/test-data/test_split.json)
- **Database Schemas**: Schema files for benchmarking databases in [`skill/evaluation/test-data/`](skill/evaluation/test-data/)
- **Database Service**: [`db_service.py`](service/src/service/db_service.py) for schema extraction and query execution (pre-built)
- **Template Starter File**: [`sql_generation.py`](skill/sql_generation.py) with Input/Output models pre-defined
- **Pre-built Backend & Frontend**: Fully functional application - you only build the SQL generation skill!

---

## Prerequisites

- ✅ Completed **PhariaAcademy Learning** course
- ✅ Understand the core components of PhariaAI (PhariaStudio, PhariaKernel, PhariaAssistant)
- ✅ Finish the technical setup along with the [E2E tutorial](https://github.com/Aleph-Alpha/tutorials/)

---

## Data Availability and Access

| Dataset | Contents | Location |
|---------|----------|----------|
| `Document Index Collection` | **1000+ curated question/SQL pairs** for few-shot learning | PhariaStudio Document Index (`Studio/text-to-sql-examples/asym-1024`) |
| `Northwind Database` | Classic e-commerce dataset with customers, products, orders, employees | [`service/src/data/northwind-SQLite3/`](service/src/data/northwind-SQLite3/) |
| `Test Split` | 100+ curated test examples with questions and expected SQL queries | [`skill/evaluation/test-data/test_split.json`](skill/evaluation/test-data/test_split.json) |
| `Database Schemas` | SQL schema files for 5 evaluation databases (car, concert_singer, employee_hire_evaluation, flight_2, pets_1) | [`skill/evaluation/test-data/`](skill/evaluation/test-data/) |

### About the Databases

The **Northwind database** is the main database used in the application. It simulates a typical e-commerce dataset with tables for customers, products, orders, employees, suppliers, and more, making it ideal for demonstrating SQL query capabilities.

For benchmarking, additional database schemas are provided (automotive, entertainment, HR, aviation, pets) to test the generalization capability of your skills.

### Test Data Structure

Each entry in [`skill/evaluation/test-data/test_split.json`](skill/evaluation/test-data/test_split.json) contains:
- `question`: Natural language question
- `query`: Expected SQL query
- `db_id`: Database identifier (references one of the 5 schemas in test-data/)

This test data is used for evaluating your SQL generation skill.

---

## Tools

- **Pharia Custom Application** – Pre-built UI and backend are provided; you focus on building skills
- **PhariaStudio** – Develop, debug, and benchmark your skills
- **PhariaSearch Document Index** – Store few-shot examples for retrieval-augmented generation
- **PhariaKernel** – Deploy and host your skills
- **PhariaAssistant** – Showcase your deployed application
- **Database Service** (`service/src/service/db_service.py`) – Extract schema and execute queries (already integrated)

Full documentation: [Aleph Alpha Docs](https://docs.aleph-alpha.com/)

---

## Models Available

You may use **any model** visible in your **PhariaStudio Playground** workspace, including:

- Generation Models (e.g., `llama-3.1-8b-instruct`, `llama-3.3-70b-instruct`, etc.)
- Embedding Models (e.g., `pharia-1-embedding-4608-control`, `pharia-1-embedding-256-control`)

Select the model in your flow configuration or switch interactively in the Playground.

---

## ⚙️ Setup Instructions

### Step 1: Environment Setup

1. **Configure environment variables** in [`skill/.env`](skill/.env):
   ```env
   PHARIA_AI_TOKEN=your_token
   PHARIA_KERNEL_ADDRESS=your_kernel_address
   
   SKILL_REGISTRY=your_registry
   SKILL_REPOSITORY=your_repository
   SKILL_REGISTRY_USER=your_user
   SKILL_REGISTRY_TOKEN=your_token
   ```

2. **Review the project structure** and understand where data is located
3. **Explore the files**:
   - [`skill/sql_generation.py`](skill/sql_generation.py) - SQL generation skill starter (YOUR TASK)
   - [`skill/chart_generation.py`](skill/chart_generation.py) - Chart generation skill (pre-built, ready to deploy)
   - [`skill/chart_classifier.py`](skill/chart_classifier.py) - Chart classifier skill (pre-built, for reference or extension)
   - [`skill/evaluation/test-data/`](skill/evaluation/test-data/) - Test data and schemas for benchmarking

---

## Part 1: Build and Benchmark the SQL Generation Skill

### Required Input/Output Models

Your skill **MUST** use these exact models for backend integration:

```python
from pydantic import BaseModel

class Input(BaseModel):
    question: str                    # The user's question in natural language
    database_schema: str | None = None  # (Optional) The schema of the target database, to support multiple databases

class Output(BaseModel):
    answer: str | None              # Generated SQL query or None if impossible
    duration: float | None = None   # Optional: generation time, could be used as a metric in evaluation
```

### Step 1.1: Access the Few-Shot Examples Collection

**Good news!** We've already prepared a curated **Document Index collection with 1000+ question/SQL pairs** for you to use.

**Collection Details**:
- **Namespace**: `Studio`
- **Collection**: `text-to-sql-examples`
- **Index**: `asym-1024`
- **Content**: 1000+ question/SQL pairs across multiple databases
- **Format**: 
  - Document content: Natural language question (e.g., "How many customers are there?")
  - Document metadata: `{"query": "SELECT COUNT(*) FROM Customers;"}`


**Note**: If you want to see how a collection is set up and how ingestion is done, you can check [`service/src/service/prepare_collection.py`](service/src/service/prepare_collection.py).

### Step 1.2: Implement the Skill

**Edit file**: [`skill/sql_generation.py`](skill/sql_generation.py)

This file already has the Input/Output models defined. You need to implement:

1. **Add the `@skill` decorator and main function**:
   ```python
   from pharia_skill import skill, Csi, IndexPath, Message, ChatParams
   from pydantic import BaseModel
   
   @skill
   def generate_sql(csi: Csi, input: Input) -> Output:
       # Your implementation here
       pass
   ```

2. **Retrieve few-shot examples from the Document Index**:

   Use this code to search for similar questions and retrieve relevant SQL examples:

   ```python
   # Define the few-shot example model
   class FewShotExample(BaseModel):
       question: str
       sql_query: str
   
   # Collection configuration
   NAMESPACE = "Studio"
   COLLECTION = "text-to-sql-examples"
   INDEX = "asym-1024"
   
   # Set up index path
   index = IndexPath(
       namespace=NAMESPACE,
       collection=COLLECTION,
       index=INDEX,
   )
   
   # Search for similar questions and extract SQL examples
   few_shot_examples = []
   search_results = csi.search(index, input.question, max_results=10)
   
   if search_results:
       # Get metadata for each document (contains the SQL query)
       for result in search_results:
           metadata = csi.document_metadata(result.document_path)
           sql_query = metadata.get("query")
           
           # Only include examples that have a valid SQL query
           if sql_query:
               few_shot_examples.append(
                   FewShotExample(
                       question=result.content,
                       sql_query=sql_query
                   )
               )
   ```

   **What this does**:
   - Searches the Document Index for the 10 most similar questions to the user's input
   - Retrieves the metadata (which contains the SQL query) for each result
   - Builds a list of few-shot examples to include in your prompt

3. **Design your prompts**:
   - **System Prompt**: Instruct the model to generate SQL with proper syntax, handle edge cases, use JOINs/aggregations appropriately
   - **User Prompt**: Include:
     - Database schema (you can generate this dynamically using `db_service.py`—call its `.structure()` method to get the schema as a string, then pass it as an input to your skill alongside the question)
     - The few-shot examples you retrieved above
     - The user's question
   
   Use Jinja2 templates or f-strings to format your prompts with the examples.

4. **Call the chat model**:
   ```python
   messages = [
       Message.system(your_system_prompt),
       Message.user(your_user_prompt),
   ]
   
   response = csi.chat("qwen3-30b-a3b-thinking-2507-fp8", messages, ChatParams())
   ```

5. **Extract SQL** using the provided `extract_sql_text()` function:
   ```python
   sql_output = extract_sql_text(response.message.content.strip())
   ```

6. **Return the result**:
   ```python
   if not sql_output or sql_output == "None":
       return Output(answer=None)
   
   return Output(answer=sql_output)
   ```

7. **Test locally** with DevCsi:
   ```bash
   cd skill/
   python sql_generation.py
   ```

**Need help?** Ask your instructor for guidance on prompt engineering and RAG implementation.

### Step 1.3: Evaluate and Benchmark

Test your skill against the provided test dataset to measure accuracy:

1. **Use the test data** in [`skill/evaluation/test-data/test_split.json`](skill/evaluation/test-data/test_split.json):
   - Contains 100+ test examples across 5 different databases
   - Each example has a question, expected SQL query, and database identifier

2. **Define your evaluation approach and run a benchmark**:
   - Clearly specify your evaluation metrics (e.g., exact match rate, duration).
   - Implement your evaluation logic (how will you compare model output with the expected SQL? Consider normalizing, allowing for minor differences, etc.).
   - Create a task for evaluation, create a dataset from the test example, and set up a benchmark.
   - Refer to this tutorial for detailed guidance on setting up datasets, tasks, and running benchmarks:  
     [LLM as a judge evaluation](https://github.com/Aleph-Alpha/tutorials/blob/main/4.%20Evaluation/2.%20Evaluation%20(Advanced)%20-%20LLM-as-a-Judge.ipynb)
   - After running the benchmark, analyze the results and iterate as needed.

3. **Iterate on your prompts** based on results:
   - Target: >70% accuracy
   - Review failed cases
   - Improve system/user prompts
   - Try different models (`qwen3-30b-a3b-thinking-2507-fp8`, `llama-3.3-70b-instruct`)
   - Adjust your few-shot example retrieval strategy

**Ask your instructor** for help setting up evaluation if needed.

### Step 1.4: Deploy the Skill

Once you're satisfied with the benchmark results:

```bash
cd skill/
pharia-skill build sql_generation
pharia-skill publish sql_generation.wasm --name sql-generator
```


**Important**: 
1. Ask your operator to update the `namespace.toml` under [Infineon Workshop Kernel Playground](https://gitlab.aleph-alpha.de/innovation/infineon-workshop-kernel-playground/-/blob/main/namespace.toml?ref_type=heads) to make your skill available to `Pharia Kernel`
2. Update the skill name in [`service/src/service/tools.py`](service/src/service/tools.py) (line 26):
```python
skill = Skill(namespace="playground", name="sql-generator")
```

---


## Step 2: Integration Testing

Now that your SQL skill and the chart generation skill are deployed, test the complete application locally before deploying to Pharia Assistant.

### Local Testing

1. **Start the backend**:
   ```bash
   cd service/
   uv run uvicorn service.main:app --reload
   ```

2. **Start the frontend**:
   ```bash
   cd ui/
   pnpm install
   pnpm dev
   ```

3. **Test the complete flow**:
   - Enter a natural language question (e.g., "Show me customers by region")
   - Verify SQL is generated and displayed correctly
   - Verify SQL executes and results appear in the table
   - Verify chart is generated and displayed beautifully

### Preview in Pharia Assistant

Before final deployment, preview your application in Pharia Assistant:

```bash
npx @aleph-alpha/pharia-ai-cli preview
```

Open Pharia Assistant and test in dev mode. This allows you to:
- Test the application as end-users will experience it
- Verify all integrations work correctly
- Make final adjustments before production deployment

---

## Step 3: Deploy the Complete Application to Pharia Assistant

This is the final step - deploying your complete application to production!

### Pre-Deployment Checklist

Ensure all environment variables are configured:
- ✅ Root directory: [`.env`](.env)
- ✅ Service directory: [`service/.env`](service/.env)
- ✅ UI directory: [`ui/.env`](ui/.env)

Verify:
- ✅ SQL generation skill is built, published, and benchmarked
- ✅ Chart generation skill is built and published
- ✅ SQL-generation Skill name is updated in [`tools.py`](service/src/service/tools.py)
- ✅ Application tested locally and in preview mode

### Publish and Deploy

```bash
# Publish application container
npx @aleph-alpha/pharia-ai-cli publish

# Deploy to Pharia Assistant
npx @aleph-alpha/pharia-ai-cli deploy
```

**Deployment time**: Typically takes 2-5 minutes.

### Access Your Application

Once deployment is complete:

1. **Open Pharia Assistant** in your browser
2. **Find your application** in the applications list
3. **Start using it!** Ask questions like:
   - "How many customers do we have in each region?"
   - "Show me the top 10 products by revenue"
   - "What are the monthly order trends?"

Your application is now **live and accessible to all users** with access to your Pharia Assistant instance!

---

## 🏁 You're Done!

You now have a **complete Text-to-SQL application deployed to Pharia Assistant**!

Your deployed application allows users to:
- Ask questions in plain English through Pharia Assistant
- See the generated SQL queries
- View query results in interactive tables
- Generate beautiful charts with one click
- Access everything seamlessly within Pharia Assistant

**What you've accomplished**:
✅ Built an SQL generation skill using RAG and few-shot learning  
✅ Achieved high accuracy on benchmark tests  
✅ Deployed and integrated your skill with a full-stack application  
✅ Deployed the complete system to Pharia Assistant  

---

## 📁 Project Structure

```
├── service/
│   └── src/
│       ├── data/                         # Northwind database
│       │   └── northwind-SQLite3/        # Main Northwind database
│       │       ├── northwind.db          # SQLite database file
│       │       └── ...
│       │           
│       └── service/
│           ├── db_service.py             # Database utilities (pre-built)
│           ├── tools.py                  # ⚠️ UPDATE line 26 with SQL skill name
│           └── ...
├── skill/
│   ├── sql_generation.py                 # ⚠️ YOUR TASK: Implement SQL generation skill
│   ├── chart_generation.py               # Pre-built: Chart generation skill (reference)
│   ├── tool_router.py                    # Example: Skill routing (reference)
│   ├── chart_classifier.py               # Example: Chart classification (reference)
│   └── evaluation/                       # Test data for benchmarking
│       └── test-data/
│           ├── test_split.json           # 100+ test examples
│           ├── car_1.sql                 # Test database schema
│           ├── concert_singer.sql        # Test database schema
│           ├── employee_hire_evaluation.sql  # Test database schema
│           ├── flight_2.sql              # Test database schema
│           └── pets_1.sql                # Test database schema
├── ui/                                   # Pre-built frontend (no changes needed)
└── README.md                             # This file (workshop guide)
```

Good luck, and happy building! 🚀