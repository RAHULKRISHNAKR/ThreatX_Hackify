import os
import platform
import json
import requests
import time
from datetime import datetime, timedelta
from subprocess import run
from rich.prompt import Prompt
from rich import print
from rich.console import Console
from rich.panel import Panel
from rich.console import Group
from rich.align import Align
from rich import box
from rich.markdown import Markdown
from typing import Any
from dotenv import load_dotenv
import google.generativeai as genai
import openai

# Load environment variables
load_dotenv()
RUNPOD_ENDPOINT_ID = os.getenv("RUNPOD_ENDPOINT_ID")
RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AI_OPTION = os.getenv("AI_OPTION")

console = Console()

# Add rate limiting variables
MAX_REQUESTS_PER_MINUTE = 60
request_timestamps = []
model = None
last_initialization_attempt = None
INITIALIZATION_COOLDOWN = 60  # seconds

def check_rate_limit():
    """Check if we're within rate limits"""
    global request_timestamps
    current_time = datetime.now()
    # Remove timestamps older than 1 minute
    request_timestamps = [ts for ts in request_timestamps 
                        if current_time - ts < timedelta(minutes=1)]
    
    if len(request_timestamps) >= MAX_REQUESTS_PER_MINUTE:
        return False
    
    request_timestamps.append(current_time)
    return True

def initialize_gemini():
    global model, last_initialization_attempt
    
    # Check if we're trying to initialize too frequently
    if last_initialization_attempt and \
       time.time() - last_initialization_attempt < INITIALIZATION_COOLDOWN:
        print("Waiting for initialization cooldown...")
        return False
        
    last_initialization_attempt = time.time()
    
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
            
        print(f"Attempting to initialize Gemini with key: {api_key[:10]}...")
        genai.configure(api_key=api_key)
        
        # Initialize model with just the name
        model = genai.GenerativeModel('models/gemini-1.5-pro')
        
        # Simple test without generation config
        test_response = model.generate_content("test")
        if not hasattr(test_response, 'text'):
            raise ValueError("Model test failed - invalid response format")
            
        print("Gemini model initialized successfully!")
        return True
        
    except Exception as e:
        print(f"Failed to initialize Gemini: {str(e)}")
        model = None
        return False

# Initialize Gemini if it's selected
if AI_OPTION == "GEMINI":
    if not initialize_gemini():
        print("Warning: Gemini initialization failed!")

# Configure OpenAI
if AI_OPTION == "OPENAI":
    openai.api_key = OPENAI_API_KEY

# Llama configuration moved to a separate function to avoid indentation issues
def setup_llama():
    if AI_OPTION == "LLAMALOCAL":
        model_name_or_path = "localmodels/Llama-2-7B-Chat-ggml"
        model_basename = "llama-2-7b-chat.ggmlv3.q4_0.bin"
        model_path = hf_hub_download(repo_id=model_name_or_path, filename=model_basename)
        callback_manager = CallbackManager([StreamingStdOutCallbackHandler()])
        return LlamaCpp(
            model_path=model_path,
            input={
                "temperature": 0.6,
                "max_length": 1000,
                "top_p": 0.9
            },
            callback_manager=callback_manager,
            max_tokens=1000,
            n_batch=32,
            n_gpu_layers=60,
            verbose=False,
            n_ctx=1000,
            streaming=True,
            f16_kv=True,
            use_mlock=True,
        )
    return None

def gemini_api(prompt):
    global model
    
    if not check_rate_limit():
        return "Rate limit exceeded. Please wait a minute before trying again."
    
    try:
        if model is None:
            if not initialize_gemini():
                return "Error: Could not initialize Gemini model. Please try again later."

        response = model.generate_content(prompt)
        return response.text if hasattr(response, 'text') else str(response)

    except Exception as e:
        error_msg = str(e)
        print(f"Gemini API error: {error_msg}")
        
        if "429" in error_msg or "quota" in error_msg.lower():
            return "Service is currently busy. Please try again in a few minutes."
        return f"Error: {error_msg}"

def openai_api(prompt):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=1000
    )
    return response.choices[0].message.content

def llama_api(prompt):
    payload = json.dumps({
        "input": {
            "prompt": prompt,
            "max_new_tokens": 4500,
            "temperature": 0.9,
            "top_k": 50,
            "top_p": 0.7,
            "repetition_penalty": 1.2,
            "batch_size": 8,
            "stop": [
                "</s>"
            ]
        }
    })
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {RUNPOD_API_KEY}',
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    response_t = json.loads(response.text)
    return response_t["output"]

def Print_AI_out(prompt, ai_option):
    try:
        # Simplified prompt without special formatting
        formatted_prompt = f"""
You are a cybersecurity expert assistant. Please help with this query:
{prompt}

Provide your response in clear, concise language using Markdown formatting where appropriate.
"""
        
        if ai_option == "GEMINI":
            response = gemini_api(formatted_prompt)
        elif ai_option == "OPENAI":
            response = openai_api(formatted_prompt)
        elif ai_option == "RUNPOD":
            response = llama_api(formatted_prompt)
        # elif ai_option == "LLAMALOCAL":
        #     response = llm(formatted_prompt)
        else:
            response = "Invalid AI option selected"
        
        return str(response).strip()
        
    except Exception as e:
        print(f"Detailed Print_AI_out error: {str(e)}")  # This will help debug
        return "I apologize, but I'm having trouble processing that request."

def clearscr() -> None:
    try:
        osp = platform.system()
        match osp:
            case 'Darwin':
                os.system("clear")
            case 'Linux':
                os.system("clear")
            case 'Windows':
                os.system("cls")
    except Exception:
        pass

def save_chat(chat_history: list[Any, Any]) -> None:
    f = open('chat_history.json', 'w+')
    f.write(json.dumps(chat_history))
    f.close

def vuln_analysis(scan_type, file_path, ai_option) -> Panel:
    global chat_history
    f = open(file_path, "r")
    file_data = f.read()
    f.close
    instructions = """
    You are a Universal Vulnerability Analyzer powered by the Llama2 model. Your main objective is to analyze any provided scan data or log data to identify potential vulnerabilities in the target system or network. You can use the scan type or the scanner type to prepare better report.
        1. Data Analysis: Thoroughly analyze the given scan data or log data to uncover vulnerabilities and security issues in the target environment.
        2. Format Flexibility: Be adaptable to handle various data formats, such as NMAP scans, vulnerability assessment reports, security logs, or any other relevant data.
        3. Vulnerability Identification: Identify different types of vulnerabilities, including but not limited to software vulnerabilities, misconfigurations, exposed sensitive information, potential security risks, and more.
        4. Accuracy and Precision: Ensure the analysis results are accurate and precise to provide reliable information for further actions.
        5. Comprehensive Report: Generate a detailed vulnerability report that includes the following sections:
            - Vulnerability Summary: A brief overview of the detected vulnerabilities.
            - Software Vulnerabilities: List of identified software vulnerabilities with their respective severity levels.
            - Misconfigurations: Highlight any misconfigurations found during the analysis.
            - Exposed Sensitive Information: Identify any exposed sensitive data, such as passwords, API keys, or usernames.
            - Security Risks: Flag potential security risks and their implications.
            - Recommendations: Provide actionable recommendations to mitigate the detected vulnerabilities.
        6. Threat Severity: Prioritize vulnerabilities based on their severity level to help users focus on critical issues first.
        7. Context Awareness: Consider the context of the target system or network when analyzing vulnerabilities. Take into account factors like system architecture, user permissions, and network topology.
        8. Handling Unsupported Data: If the provided data format is unsupported or unclear, politely ask for clarifications or indicate the limitations.
        9. Language and Style: Use clear and concise language to present the analysis results. Avoid jargon and unnecessary technicalities.
        10. Provide output in Markdown. 
    """

    data = f"""
        Provide the scan type: {scan_type} 
        Provide the scan data or log data that needs to be analyzed: {file_data}
    """
    prompt = f"[INST] <<SYS>> {instructions}<</SYS>> Data to be analyzed: {data} [/INST]"
    if ai_option == "RUNPOD":
        out = llama_api(prompt)
    else:
        out = Print_AI_out(prompt, ai_option)
    ai_out = Markdown(out)
    message_panel = Panel(
        Align.center(
            Group("\n", Align.center(ai_out)),
            vertical="middle",
        ),
        box=box.ROUNDED,
        padding=(1, 2),
        title="[b red]The HackBot AI output",
        border_style="blue",
    )
    save_data = {
        "Query": str(prompt),
        "AI Answer": str(out)
    }
    chat_history.append(save_data)
    return message_panel

def static_analysis(language_used, file_path, ai_option) -> Panel:
    global chat_history
    f = open(file_path, "r")
    file_data = f.read()
    f.close
    instructions = """
        Analyze the given programming file details to identify and clearly report bugs, vulnerabilities, and syntax errors.
        Additionally, search for potential exposure of sensitive information such as API keys, passwords, and usernames. Please provide result in Markdown.
    """
    data = f"""
        - Programming Language: {language_used}
        - File Name: {file_path}
        - File Data: {file_data}
    """
    prompt = f"[INST] <<SYS>> {instructions}<</SYS>> Data to be analyzed: {data} [/INST]"
    if ai_option == "RUNPOD":
        out = llama_api(prompt)
    else:
        out = Print_AI_out(prompt, ai_option)
    ai_out = Markdown(out)
    message_panel = Panel(
        Align.center(
            Group("\n", Align.center(ai_out)),
            vertical="middle",
        ),
        box=box.ROUNDED,
        padding=(1, 2),
        title="[b red]The ThreatX AI output",
        border_style="blue",
    )
    save_data = {
        "Query": str(prompt),
        "AI Answer": str(out)
    }
    chat_history.append(save_data)
    return message_panel

def main() -> None:
    clearscr()
    banner = """
    ------------ThreatX----------------
    """
    contact_dev = """
    
    Github = https://github.com/rahulkrishnakr
    """

    help_menu = """
    - clear_screen: Clears the console screen for better readability.
    - quit_bot: This is used to quit the chat application
    - bot_banner: Prints the default bots banner.
    - contact_dev: Provides my contact information.
    - save_chat: Saves the current sessions interactions.
    - help_menu: Lists chatbot commands.
    - vuln_analysis: Does a Vuln analysis using the scan data or log file.
    - static_code_analysis: Does a Static code analysis using the scan data or log file.
    """
    console.print(Panel(Markdown(banner)), style="bold green")
    while True:
        try:
            prompt_in = Prompt.ask('> ')
            if prompt_in == 'quit_bot':
                quit()
            elif prompt_in == 'clear_screen':
                clearscr()
                pass
            elif prompt_in == 'bot_banner':
                console.print(Panel(Markdown(banner)), style="bold green")
                pass
            elif prompt_in == 'save_chat':
                save_chat(chat_history)
                pass
            elif prompt_in == 'static_code_analysis':
                print(Markdown('----------'))
                language_used = Prompt.ask('Language Used> ')
                file_path = Prompt.ask('File Path> ')
                print(Markdown('----------'))
                print(static_analysis(language_used, file_path, AI_OPTION))
                pass
            elif prompt_in == 'vuln_analysis':
                print(Markdown('----------'))
                language_used = Prompt.ask('Scan Type > ')
                file_path = Prompt.ask('File Path > ')
                print(Markdown('----------'))
                print(static_analysis(language_used, file_path, AI_OPTION))
                pass
            elif prompt_in == 'contact_dev':
                console.print(Panel(
                    Align.center(
                        Group(Align.center(Markdown(contact_dev))),
                        vertical="middle",
                    ),
                    title="Dev Contact",
                    border_style="red"
                ),
                    style="bold green"
                )
                pass
            elif prompt_in == 'help_menu':
                console.print(Panel(
                    Align.center(
                        Group(Align.center(Markdown(help_menu))),
                        vertical="middle",
                    ),
                    title="Help Menu",
                    border_style="red"
                ),
                    style="bold green"
                )
                pass
            else:
                instructions = """
                You are an helpful cybersecurity assistant and I want you to answer my query and provide output in Markdown: 
                """
                prompt = f"[INST] <<SYS>> {instructions}<</SYS>> Cybersecurity Query: {prompt_in} [/INST]"
                print(Print_AI_out(prompt, AI_OPTION))
                pass
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    main()
