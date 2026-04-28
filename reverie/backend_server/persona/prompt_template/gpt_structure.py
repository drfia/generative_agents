"""
Author: Joon Sung Park (joonspk@stanford.edu)

File: gpt_structure.py
Description: Wrapper functions for calling AI APIs.
Modified to use Anthropic API via litellm proxy instead of OpenAI.
"""
import json
import random
import time
import os
import sys

import httpx
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from utils import *

# Load env vars from .env file at project root
def _load_env():
  env_path = os.path.join(os.path.dirname(__file__), "../../../../.env")
  env_path = os.path.abspath(env_path)
  if os.path.exists(env_path):
    with open(env_path) as f:
      for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
          k, v = line.split("=", 1)
          os.environ.setdefault(k.strip(), v.strip())

_load_env()

def _get_model():
  return os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")

def _detect_proxy():
  """Detect proxy from env vars or macOS system settings."""
  proxy = (os.environ.get("HTTPS_PROXY")
           or os.environ.get("https_proxy")
           or os.environ.get("HTTP_PROXY")
           or os.environ.get("http_proxy"))
  if proxy:
    return proxy
  # Auto-detect macOS system proxy via scutil
  try:
    import subprocess
    result = subprocess.run(
      ["scutil", "--proxy"], capture_output=True, text=True, timeout=3
    )
    host = port = None
    for line in result.stdout.splitlines():
      line = line.strip()
      if "HTTPSProxy :" in line:
        host = line.split(":", 1)[1].strip()
      elif "HTTPSPort :" in line:
        port = line.split(":", 1)[1].strip()
    if host and port:
      return f"http://{host}:{port}"
  except Exception:
    pass
  return None

_PROXY = _detect_proxy()

def _call_api(prompt, max_tokens=1024):
  """Direct HTTP call to Anthropic-compatible endpoint (no system proxy)."""
  base_url = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com").rstrip("/")
  api_key = os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
  url = f"{base_url}/v1/messages"
  headers = {
    "x-api-key": api_key,
    "anthropic-version": "2023-06-01",
    "content-type": "application/json",
  }
  payload = {
    "model": _get_model(),
    "max_tokens": max_tokens,
    "messages": [{"role": "user", "content": prompt}],
  }
  # Disable system proxy — the litellm endpoint is directly accessible
  resp = requests.post(url, headers=headers, json=payload,
                       proxies={"https": None, "http": None}, timeout=60)
  resp.raise_for_status()
  data = resp.json()
  return data["content"][0]["text"]


def temp_sleep(seconds=0.1):
  time.sleep(seconds)


def ChatGPT_single_request(prompt):
  temp_sleep()
  return _call_api(prompt)


# ============================================================================
# #####################[SECTION 1: CHATGPT-3 STRUCTURE] ######################
# ============================================================================

def GPT4_request(prompt):
  """
  Given a prompt, make a request to Anthropic and return the response.
  """
  temp_sleep()
  try:
    return _call_api(prompt)
  except Exception as e:
    print(f"API ERROR: {e}")
    return "ChatGPT ERROR"


def ChatGPT_request(prompt):
  """
  Given a prompt, make a request to Anthropic and return the response.
  """
  try:
    return _call_api(prompt)
  except Exception as e:
    print(f"API ERROR: {e}")
    return "ChatGPT ERROR"


def GPT4_safe_generate_response(prompt,
                                example_output,
                                special_instruction,
                                repeat=3,
                                fail_safe_response="error",
                                func_validate=None,
                                func_clean_up=None,
                                verbose=False):
  prompt = 'GPT-3 Prompt:\n"""\n' + prompt + '\n"""\n'
  prompt += f"Output the response to the prompt above in json. {special_instruction}\n"
  prompt += "Example output json:\n"
  prompt += '{"output": "' + str(example_output) + '"}'

  if verbose:
    print("CHAT GPT PROMPT")
    print(prompt)

  for i in range(repeat):
    try:
      curr_gpt_response = GPT4_request(prompt).strip()
      end_index = curr_gpt_response.rfind('}') + 1
      curr_gpt_response = curr_gpt_response[:end_index]
      curr_gpt_response = json.loads(curr_gpt_response)["output"]

      if func_validate(curr_gpt_response, prompt=prompt):
        return func_clean_up(curr_gpt_response, prompt=prompt)

      if verbose:
        print("---- repeat count: \n", i, curr_gpt_response)
        print(curr_gpt_response)
        print("~~~~")

    except:
      pass

  return False


def ChatGPT_safe_generate_response(prompt,
                                   example_output,
                                   special_instruction,
                                   repeat=3,
                                   fail_safe_response="error",
                                   func_validate=None,
                                   func_clean_up=None,
                                   verbose=False):
  prompt = '"""\n' + prompt + '\n"""\n'
  prompt += f"Output the response to the prompt above in json. {special_instruction}\n"
  prompt += "Example output json:\n"
  prompt += '{"output": "' + str(example_output) + '"}'

  if verbose:
    print("CHAT GPT PROMPT")
    print(prompt)

  for i in range(repeat):
    try:
      curr_gpt_response = ChatGPT_request(prompt).strip()
      end_index = curr_gpt_response.rfind('}') + 1
      curr_gpt_response = curr_gpt_response[:end_index]
      curr_gpt_response = json.loads(curr_gpt_response)["output"]

      if func_validate(curr_gpt_response, prompt=prompt):
        return func_clean_up(curr_gpt_response, prompt=prompt)

      if verbose:
        print("---- repeat count: \n", i, curr_gpt_response)
        print(curr_gpt_response)
        print("~~~~")

    except:
      pass

  return False


def ChatGPT_safe_generate_response_OLD(prompt,
                                       repeat=3,
                                       fail_safe_response="error",
                                       func_validate=None,
                                       func_clean_up=None,
                                       verbose=False):
  if verbose:
    print("CHAT GPT PROMPT")
    print(prompt)

  for i in range(repeat):
    try:
      curr_gpt_response = ChatGPT_request(prompt).strip()
      if func_validate(curr_gpt_response, prompt=prompt):
        return func_clean_up(curr_gpt_response, prompt=prompt)
      if verbose:
        print(f"---- repeat count: {i}")
        print(curr_gpt_response)
        print("~~~~")
    except:
      pass
  print("FAIL SAFE TRIGGERED")
  return fail_safe_response


# ============================================================================
# ###################[SECTION 2: ORIGINAL GPT-3 STRUCTURE] ###################
# ============================================================================

def GPT_request(prompt, gpt_parameter):
  """
  Replaces legacy GPT-3 Completion API with Anthropic messages API.
  gpt_parameter is kept for interface compatibility but mostly ignored.
  """
  temp_sleep()
  try:
    max_tokens = gpt_parameter.get("max_tokens", 512)
    return _call_api(prompt, max_tokens=max_tokens)
  except Exception as e:
    print(f"TOKEN LIMIT EXCEEDED or API ERROR: {e}")
    return "TOKEN LIMIT EXCEEDED"


def generate_prompt(curr_input, prompt_lib_file):
  """
  Takes in the current input and the path to a prompt file.
  Replaces !<INPUT N>! placeholders with actual input values.
  """
  if type(curr_input) == type("string"):
    curr_input = [curr_input]
  curr_input = [str(i) for i in curr_input]

  f = open(prompt_lib_file, "r")
  prompt = f.read()
  f.close()
  for count, i in enumerate(curr_input):
    prompt = prompt.replace(f"!<INPUT {count}>!", i)
  if "<commentblockmarker>###</commentblockmarker>" in prompt:
    prompt = prompt.split("<commentblockmarker>###</commentblockmarker>")[1]
  return prompt.strip()


def safe_generate_response(prompt,
                           gpt_parameter,
                           repeat=5,
                           fail_safe_response="error",
                           func_validate=None,
                           func_clean_up=None,
                           verbose=False):
  if verbose:
    print(prompt)

  for i in range(repeat):
    curr_gpt_response = GPT_request(prompt, gpt_parameter)
    if func_validate(curr_gpt_response, prompt=prompt):
      return func_clean_up(curr_gpt_response, prompt=prompt)
    if verbose:
      print("---- repeat count: ", i, curr_gpt_response)
      print(curr_gpt_response)
      print("~~~~")
  return fail_safe_response


def get_embedding(text, model="text-embedding-ada-002"):
  """
  Embedding via Anthropic is not directly available.
  Falls back to a simple zero-vector with a warning.
  If you need real embeddings, integrate a separate embedding service.
  """
  text = text.replace("\n", " ")
  if not text:
    text = "this is blank"
  print(f"[WARNING] get_embedding called — Anthropic does not support embeddings. "
        f"Returning zero vector. Consider using a dedicated embedding model.")
  # Return a 1536-dim zero vector to maintain interface compatibility
  return [0.0] * 1536


if __name__ == '__main__':
  # Quick smoke test
  result = ChatGPT_request("Say hello in one sentence.")
  print("Response:", result)
