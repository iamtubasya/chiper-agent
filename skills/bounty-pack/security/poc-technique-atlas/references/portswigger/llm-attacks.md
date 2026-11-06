# PortSwigger WSA — Web LLM Attacks
Source: https://portswigger.net/web-security/llm-attacks

## Technique headings
- API testing
- What is a large language model?
- LLM attacks and prompt injection
- Detecting LLM vulnerabilities
- Exploiting LLM APIs, functions, and plugins
- How LLM APIs work
- Mapping LLM API attack surface
- Chaining vulnerabilities in LLM APIs
- Insecure output handling
- Indirect prompt injection
- Training data poisoning
- Leaking sensitive training data
- Defending against LLM attacks
- Treat APIs given to LLMs as publicly accessible
- Don't feed LLMs sensitive data
- Don't rely on prompting to block attacks
- AI-powered scanner vulnerabilities
- Read more
- Test for vulnerabilities using Burp Suite

## Sub-topic pages
- https://portswigger.net/web-security/llm-attacks/ai-powered-scanner-vulnerabilities


## Labs (2026-10-18 — per-lab scenarios & solutions), 4 lab)

- **Exploiting LLM APIs with excessive agency** (`lab-exploiting-llm-apis-with-excessive-agency`)
  - Solution Note Our Web LLM attacks labs use a live LLM. While we have tested the solutions to these labs extensively, we cannot guarantee how the live chat feature will respond in any given situation due to the unpredictable nature of LLM responses. You may sometimes need to rephrase your prompts or use a slightly different process to solve the lab. . . • From the lab homepage, select Live chat . . • Ask the LLM what APIs it has access to. Note that the LLM can execute raw SQL commands on the database via the Debug SQL API. . • Ask the LLM what arguments the Debug SQL API takes. Note that the A
- **Exploiting vulnerabilities in LLM APIs** (`lab-exploiting-vulnerabilities-in-llm-apis`)
  - Solution Note Our Web LLM attacks labs use a live LLM. While we have tested the solutions to these labs extensively, we cannot guarantee how the live chat feature will respond in any given situation due to the unpredictable nature of LLM responses. You may sometimes need to rephrase your prompts or use a slightly different process to solve the lab. . . • From the lab homepage, click Live chat . . • Ask the LLM what APIs it has access to. The LLM responds that it can access APIs controlling the following functions: . • Password Reset • Newsletter Subscription • Product Information • Consider th
- **Indirect prompt injection** (`lab-indirect-prompt-injection`)
  - Solution Note Our Web LLM attacks labs use a live LLM. While we have tested the solutions to these labs extensively, we cannot guarantee how the live chat feature will respond in any given situation due to the unpredictable nature of LLM responses. You may sometimes need to rephrase your prompts or use a slightly different process to solve the lab. . . Discover the attack surface . • Click Live chat to access the lab's chat function. . • Ask the LLM what APIs it has access to. Note that it supports APIs to both delete accounts and edit their associated email addresses. . • Ask the LLM what arg
- **Exploiting insecure output handling in LLMs** (`lab-exploiting-insecure-output-handling-in-llms`)
  - Solution Note Our Web LLM attacks labs use a live LLM. While we have tested the solutions to these labs extensively, we cannot guarantee how the live chat feature will respond in any given situation due to the unpredictable nature of LLM responses. You may sometimes need to rephrase your prompts or use a slightly different process to solve the lab. . . Create a user account . • Click Register to display the registration page. . • Enter the required details. Note that the Email should be the email address associated with your instance of the lab. It is displayed at the top of the Email client p
