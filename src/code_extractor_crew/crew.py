from pathlib import Path

from crewai import Agent, Crew, Process, Task, LLM
from crewai_tools import DirectoryReadTool, FileReadTool
from crewai.knowledge.source.pdf_knowledge_source import PDFKnowledgeSource
from crewai.project import CrewBase, agent, crew, task
llm_google = LLM(model="gemini/gemini-1.5-pro",  temperature=0.7)
llm_openai = LLM(model="gpt-4o-mini", temperature=0.7)
llm_local = LLM(model="ollama/deepseek-r1:14b", base_url="http://localhost:11434")

# Repo root is three levels up: src/code_extractor_crew/crew.py -> repo
REPO_ROOT = Path(__file__).resolve().parents[2]
CODE_REPOSITORY = REPO_ROOT / "code_repository"


@CrewBase
class CodeExtractorCrew():
	"""CodeExtractorCrew crew"""

	agents_config = 'config/agents.yaml'
	tasks_config = 'config/tasks.yaml'
	# Instantiate tools
	docs_tool = DirectoryReadTool(directory=str(CODE_REPOSITORY))
	file_tool = FileReadTool()

	pdf_knowledge_source = PDFKnowledgeSource(
		file_paths=['37_Requirements_10_Best_Practices.pdf']
	)

	@agent
	def code_parser(self) -> Agent:
		return Agent(
			config=self.agents_config['code_parser'],
			verbose=True,
			tools=[self.docs_tool, self.file_tool],
			llm=llm_openai
		)

	@agent
	def control_flow_analyzer(self) -> Agent:
		return Agent(
			config=self.agents_config['control_flow_analyzer'],
			verbose=True,
			tools=[self.docs_tool, self.file_tool],
			llm=llm_openai
		)

	@agent
	def data_flow_analyzer(self) -> Agent:
		return Agent(
			config=self.agents_config['data_flow_analyzer'],
			verbose=True,
			tools=[self.docs_tool, self.file_tool],
			llm=llm_openai
		)

	@agent
	def requirement_synthesizer(self) -> Agent:
		return Agent(
			config=self.agents_config['requirement_synthesizer'],
			verbose=True,
			knowledge_sources=[self.pdf_knowledge_source],
			llm=llm_openai
		)

	@agent
	def requirement_validator(self) -> Agent:
		return Agent(
			config=self.agents_config['requirement_validator'],
			verbose=True,
			tools=[self.docs_tool, self.file_tool],
			llm=llm_openai
		)

	@task
	def parse_code(self) -> Task:
		return Task(
			config=self.tasks_config['parse_code'],
		)

	@task
	def analyze_control_flow(self) -> Task:
		return Task(
			config=self.tasks_config['analyze_control_flow'],
		)

	@task
	def analyze_data_flow(self) -> Task:
		return Task(
			config=self.tasks_config['analyze_data_flow'],
		)

	@task
	def synthesize_requirements(self) -> Task:
		return Task(
			config=self.tasks_config['synthesize_requirements'],
		)

	@task
	def validate_requirements(self) -> Task:
		return Task(
			config=self.tasks_config['validate_requirements'],
		)

	@crew
	def crew(self) -> Crew:
		"""Creates the CodeExtractorCrew crew"""
		return Crew(
			agents=self.agents, # Automatically created by the @agent decorator
			tasks=self.tasks, # Automatically created by the @task decorator
			process=Process.sequential,
			verbose=True,
			chat_llm=llm_openai,
			# process=Process.hierarchical, # In case you wanna use that instead https://docs.crewai.com/how-to/Hierarchical/
		)
