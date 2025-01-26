"""
Author: Joon Sung Park (joonspk@stanford.edu)

File: run_gpt_prompt.py
Description: Defines all run gpt prompt functions. These functions directly
interface with the safe_generate_response function.
"""

import re
import datetime
import copy
import json
from pathlib import Path
import random
import string
import traceback
from enum import IntEnum
from pydantic import BaseModel, field_validator

import sys
sys.path.append('../../')
from config import debug
from persona.prompt_template.gpt_structure import (
  generate_prompt,
  safe_generate_response,
  safe_generate_structured_response,
  ChatGPT_safe_generate_response,
  ChatGPT_safe_generate_structured_response,
)
from persona.prompt_template.print_prompt import print_run_prompts

config_path = Path("openai_config.json")
with open(config_path, "r") as f:
  openai_config = json.load(f)

USE_REGEX = True

def get_random_alphanumeric(i=6, j=6): 
  """
  Returns a random alpha numeric strength that has the length of somewhere
  between i and j. 

  INPUT: 
    i: min_range for the length
    j: max_range for the length
  OUTPUT: 
    an alpha numeric str with the length of somewhere between i and j.
  """
  k = random.randint(i, j)
  x = ''.join(random.choices(string.ascii_letters + string.digits, k=k))
  return x


##############################################################################
# CHAPTER 1: Run GPT Prompt
##############################################################################

class WakeUpHour(BaseModel):
  wake_up_hour: int

def run_gpt_prompt_wake_up_hour(persona, test_input=None, verbose=False): 
  """
  Given the persona, returns an integer that indicates the hour when the 
  persona wakes up.  

  INPUT: 
    persona: The Persona class instance 
  OUTPUT: 
    integer for the wake up hour.
  """
  def create_prompt_input(persona, test_input=None): 
    if test_input: return test_input
    prompt_input = [persona.scratch.get_str_iss(),
                    persona.scratch.get_str_lifestyle(),
                    persona.scratch.get_str_firstname()]
    return prompt_input

  def __func_clean_up(gpt_response, prompt=""):
    if isinstance(gpt_response.wake_up_hour, int):
      return gpt_response.wake_up_hour
    raise TypeError("wake_up_hour of type int not found")
  
  def __func_validate(gpt_response, prompt=""): 
    try: __func_clean_up(gpt_response, prompt="")
    except:
      traceback.print_exc()
      return False
    return True

  def get_fail_safe(): 
    fs = 8
    return fs

  gpt_param = {"engine": openai_config["model"], "max_tokens": 100,
             "temperature": 0.8, "top_p": 1, "stream": False,
             "frequency_penalty": 0, "presence_penalty": 0, "stop": ["\n"]}
  prompt_template = "persona/prompt_template/v2/wake_up_hour_v1.txt"
  prompt_input = create_prompt_input(persona, test_input)
  prompt = generate_prompt(prompt_input, prompt_template)
  fail_safe = get_fail_safe()

  output = safe_generate_structured_response(
    prompt,
    gpt_param,
    WakeUpHour,
    5,
    fail_safe,
    __func_validate,
    __func_clean_up
  )
  
  if debug or verbose: 
    print_run_prompts(prompt_template, persona, gpt_param, 
                      prompt_input, prompt, output)
    
  return output, [output, prompt, gpt_param, prompt_input, fail_safe]


class DailyPlan(BaseModel):
  daily_plan: list[str]

def run_gpt_prompt_daily_plan(persona, 
                              wake_up_hour, 
                              test_input=None, 
                              verbose=False):
  """
  Basically the long term planning that spans a day. Returns a list of actions
  that the persona will take today. Usually comes in the following form: 
  'wake up and complete the morning routine at 6:00 am', 
  'eat breakfast at 7:00 am',.. 
  Note that the actions come without a period. 

  INPUT: 
    persona: The Persona class instance 
  OUTPUT: 
    a list of daily actions in broad strokes.
  """
  def create_prompt_input(persona, wake_up_hour, test_input=None):
    if test_input: return test_input
    prompt_input = []
    prompt_input += [persona.scratch.get_str_iss()]
    prompt_input += [persona.scratch.get_str_lifestyle()]
    prompt_input += [persona.scratch.get_str_curr_date_str()]
    prompt_input += [persona.scratch.get_str_firstname()]
    prompt_input += [f"{str(wake_up_hour)}:00 am"]
    return prompt_input

  def __func_clean_up(gpt_response, prompt=""):
    return gpt_response.daily_plan

  def __func_validate(gpt_response, prompt=""):
    try: __func_clean_up(gpt_response, prompt="")
    except:
      traceback.print_exc()
      return False
    return True

  def get_fail_safe(): 
    fs = ['wake up and complete the morning routine at 6:00 am', 
          'eat breakfast at 7:00 am', 
          'read a book from 8:00 am to 12:00 pm', 
          'have lunch at 12:00 pm', 
          'take a nap from 1:00 pm to 4:00 pm', 
          'relax and watch TV from 7:00 pm to 8:00 pm', 
          'go to bed at 11:00 pm'] 
    return fs

  gpt_param = {"engine": openai_config["model"], "max_tokens": 2000, 
               "temperature": 1, "top_p": 1, "stream": False,
               "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
  prompt_template = "persona/prompt_template/v2/daily_planning_v6.txt"
  prompt_input = create_prompt_input(persona, wake_up_hour, test_input)
  prompt = generate_prompt(prompt_input, prompt_template)
  fail_safe = get_fail_safe()

  output = safe_generate_structured_response(
    prompt,
    gpt_param,
    DailyPlan,
    5,
    fail_safe,
    __func_validate,
    __func_clean_up
  )

  if debug or verbose: 
    print_run_prompts(prompt_template, persona, gpt_param, 
                      prompt_input, prompt, output)
    
  return output, [output, prompt, gpt_param, prompt_input, fail_safe]


class Activity(BaseModel):
  date_and_time: str
  activity: str

class HourlySchedule(BaseModel):
  hourly_schedule: list[Activity]

def run_gpt_prompt_generate_hourly_schedule(
  persona,
  curr_hour_str,
  p_f_ds_hourly_org,
  hour_str,
  intermission2=None,
  test_input=None,
  verbose=False,
  all_in_one=False,
):
  def create_prompt_input(
    persona,
    curr_hour_str,
    p_f_ds_hourly_org,
    hour_str,
    intermission2=None,
    test_input=None
  ):
    if test_input:
      return test_input

    schedule_format = '{"hourly_schedule": ['
    for i in range(4):
      hour = hour_str[i]
      schedule_format += f"{{\"date_and_time\":\"{persona.scratch.get_str_curr_date_str()} -- {hour}\","
      schedule_format += '"activity":"[Fill in]"},'
    schedule_format += " ... , "
    schedule_format += f"{{\"date_and_time\":\"{persona.scratch.get_str_curr_date_str()} -- 11:00 PM}}\","
    schedule_format += '"activity":"[Fill in]"}]}'

    if not all_in_one:
      intermission_str = "Complete the given hourly schedule for the following person, filling out the whole rest of their day."
    else:
      intermission_str = "Create an hourly schedule for the following person to fill out their whole day."
    intermission_str += "\nHere is the originally intended hourly breakdown of"
    intermission_str += f" {persona.scratch.get_str_firstname()}'s schedule today: "
    for count, task in enumerate(persona.scratch.daily_req): 
      intermission_str += f"{str(count+1)}) {task}, "
    intermission_str = intermission_str[:-2]

    prior_schedule = ""
    if p_f_ds_hourly_org and not all_in_one:
      prior_schedule = "\nExisting schedule:\n"
      for count, task in enumerate(p_f_ds_hourly_org): 
        prior_schedule += f"[{persona.scratch.get_str_curr_date_str()} --"
        prior_schedule += f" {hour_str[count]}] Activity:"
        prior_schedule += f" {persona.scratch.get_str_firstname()}"
        prior_schedule += f" is {task}\n"
    # prior_schedule = ""

    # prompt_ending = f"[{persona.scratch.get_str_curr_date_str()}"
    # prompt_ending += f" -- {curr_hour_str}] Activity:"
    # prompt_ending += f" {persona.scratch.get_str_firstname()}"
    if not all_in_one:
      prompt_ending = "Completed hourly schedule (start from the hour after the existing schedule ends, and use present progressive tense, e.g. 'waking up and completing the morning routine'):"
    else:
      prompt_ending = "Hourly schedule for the whole day (use present progressive tense, e.g. 'waking up and completing the morning routine'):"

    if intermission2: 
      intermission2 = f"\n{intermission2}"

    # Construct the final prompt input
    prompt_input = [schedule_format]

    prompt_input += [persona.scratch.get_str_iss()]

    prompt_input += [intermission_str]

    prompt_input += [prior_schedule + "\n"]

    if intermission2: 
      prompt_input += [intermission2]
    else: 
      prompt_input += [""]

    prompt_input += [prompt_ending]

    return prompt_input

  def __func_clean_up(gpt_response: HourlySchedule, prompt=""):
    if not all_in_one:
      activity = gpt_response.hourly_schedule[0].activity
      activity = activity.strip("[]")
      activity = activity.removeprefix(persona.scratch.get_str_firstname()).strip()
      activity = activity.removeprefix("is ")
      return activity
    else:
      activities = []
      for item in gpt_response.hourly_schedule:
        activity = item.activity.strip("[]")
        activity = activity.removeprefix(persona.scratch.get_str_firstname()).strip()
        activity = activity.removeprefix("is ")
        activities += [activity]
      return activities

  def __func_validate(gpt_response, prompt=""):
    try:
      __func_clean_up(gpt_response, prompt)
      return True
    except Exception as e:
      print("Validation failed: ", e)
      traceback.print_exc()
      return False

  def get_fail_safe(): 
    fs = "idle"
    return fs

  gpt_param = {"engine": openai_config["model"], "max_tokens": 5000, 
               "temperature": 0.5, "top_p": 1, "stream": False,
               "frequency_penalty": 0, "presence_penalty": 0, "stop": ["\n"]}
  prompt_template = "persona/prompt_template/v2/generate_hourly_schedule_v2.txt"
  prompt_input = create_prompt_input(persona, 
                                     curr_hour_str, 
                                     p_f_ds_hourly_org,
                                     hour_str, 
                                     intermission2,
                                     test_input)
  prompt = generate_prompt(prompt_input, prompt_template)
  fail_safe = get_fail_safe()
  
  output = safe_generate_structured_response(
    prompt,
    gpt_param,
    HourlySchedule,
    5,
    fail_safe,
    __func_validate,
    __func_clean_up
  )
  
  if debug or verbose: 
    print_run_prompts(prompt_template, persona, gpt_param, 
                      prompt_input, prompt, output)
    
  return output, [output, prompt, gpt_param, prompt_input, fail_safe]


class Subtask(BaseModel):
  task: str
  duration: int
  minutes_left: int

class TaskDecomposition(BaseModel):
  subtasks: list[Subtask]

def run_gpt_prompt_task_decomp(persona, 
                               task, 
                               duration, 
                               test_input=None, 
                               verbose=False): 
  def create_prompt_input(persona, task, duration, test_input=None):

    """
    Today is Saturday June 25. From 00:00 ~ 06:00am, Maeve is 
    planning on sleeping, 06:00 ~ 07:00am, Maeve is 
    planning on waking up and doing her morning routine, 
    and from 07:00am ~08:00am, Maeve is planning on having breakfast.  
    """
      
    curr_f_org_index = persona.scratch.get_f_daily_schedule_hourly_org_index()
    all_indices = []
    # if curr_f_org_index > 0: 
    #   all_indices += [curr_f_org_index-1]
    all_indices += [curr_f_org_index]
    if curr_f_org_index+1 <= len(persona.scratch.f_daily_schedule_hourly_org): 
      all_indices += [curr_f_org_index+1]
    if curr_f_org_index+2 <= len(persona.scratch.f_daily_schedule_hourly_org): 
      all_indices += [curr_f_org_index+2]

    curr_time_range = ""

    print ("DEBUG")
    print (persona.scratch.f_daily_schedule_hourly_org)
    print (all_indices)

    summ_str = f'Today is {persona.scratch.curr_time.strftime("%B %d, %Y")}. '
    summ_str += f'From '
    for index in all_indices: 
      print ("index", index)
      if index < len(persona.scratch.f_daily_schedule_hourly_org): 
        start_min = 0
        for i in range(index): 
          start_min += persona.scratch.f_daily_schedule_hourly_org[i][1]
        end_min = start_min + persona.scratch.f_daily_schedule_hourly_org[index][1]
        start_time = (datetime.datetime.strptime("00:00:00", "%H:%M:%S") 
                      + datetime.timedelta(minutes=start_min)) 
        end_time = (datetime.datetime.strptime("00:00:00", "%H:%M:%S") 
                      + datetime.timedelta(minutes=end_min)) 
        start_time_str = start_time.strftime("%H:%M%p")
        end_time_str = end_time.strftime("%H:%M%p")
        summ_str += f"{start_time_str} ~ {end_time_str}, {persona.name} is planning on {persona.scratch.f_daily_schedule_hourly_org[index][0]}, "
        if curr_f_org_index+1 == index:
          curr_time_range = f'{start_time_str} ~ {end_time_str}'
    summ_str = summ_str[:-2] + "."

    prompt_input = []
    prompt_input += [persona.scratch.get_str_iss()]
    prompt_input += [summ_str]
    # prompt_input += [persona.scratch.get_str_curr_date_str()]
    prompt_input += [persona.scratch.get_str_firstname()]
    prompt_input += [persona.scratch.get_str_firstname()]
    prompt_input += [task]
    prompt_input += [curr_time_range]
    prompt_input += [duration]
    prompt_input += [persona.scratch.get_str_firstname()]
    return prompt_input

  def __func_clean_up(gpt_response: TaskDecomposition, prompt=""):
    debug = True

    if debug:
      print (gpt_response)
      print ("-==- -==- -==- ")
      print("(cleanup func): Enter function")

    final_task_list = []

    for count, subtask in enumerate(gpt_response.subtasks):
      task = subtask.task.strip().strip('.')

      # Get rid of "1)", "2)", etc. at start of string if it exists
      if task[1] == ")":
        task = task[2:].strip()
      # Get rid of "Isabella is " at start of string if it exists
      if task.startswith(persona.scratch.get_str_firstname()):
        task = " is ".join(task.split(" is ")[1:])

      final_task_list += [[task, subtask.duration]]

    if debug:
      print("(cleanup func) Unpacked (final_task_list)): ", final_task_list)
      print("(cleanup func) Prompt:", prompt)

    total_expected_min = int(
      prompt.split(
        "(total duration in minutes"
      )[-1].split("):")[0].strip()
    )

    if debug:
      print("(cleanup func) Expected Minutes:", total_expected_min)

    # TODO -- now, you need to make sure that this is the same as the sum of 
    #         the current action sequence.
    curr_min_slot = [["dummy", -1],] # (task_name, task_index)
    for count, split_task in enumerate(final_task_list):
      i_task = split_task[0]
      i_duration = split_task[1]

      i_duration -= (i_duration % 5)
      if i_duration > 0:
        for _j in range(i_duration):
          curr_min_slot += [(i_task, count)]
    curr_min_slot = curr_min_slot[1:]

    if len(curr_min_slot) > total_expected_min:
      last_task = curr_min_slot[60]
      for i in range(1, 6):
        curr_min_slot[-1 * i] = last_task
    elif len(curr_min_slot) < total_expected_min:
      last_task = curr_min_slot[-1]
      for i in range(total_expected_min - len(curr_min_slot)):
        curr_min_slot += [last_task]

    return_task_list = [["dummy", -1],]
    for task, _task_index in curr_min_slot:
      if task != return_task_list[-1][0]:
        return_task_list += [[task, 1]]
      else:
        return_task_list[-1][1] += 1
    final_task_list = return_task_list[1:]

    return final_task_list

  def __func_validate(gpt_response, prompt=""): 
    try: 
      __func_clean_up(gpt_response, prompt)
    except Exception as e:
      print("Validation failed: ", e)
      traceback.print_exc()
      return False
    return gpt_response

  def get_fail_safe(): 
    fs = ["idle", 5]
    return fs

  gpt_param = {"engine": openai_config["model"], "max_tokens": 5000, 
             "temperature": 0, "top_p": 1, "stream": False,
             "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
  prompt_template = "persona/prompt_template/v2/task_decomp_v3.txt"
  prompt_input = create_prompt_input(persona, task, duration)
  prompt = generate_prompt(prompt_input, prompt_template)
  fail_safe = get_fail_safe()

  output = safe_generate_structured_response(
    prompt,
    gpt_param,
    TaskDecomposition,
    5,
    get_fail_safe(),
    __func_validate,
    __func_clean_up
  )

  # print ("DEBUG")  
  # print("PROMPT:")
  # print (prompt)
  # print("\nOUTPUT:")
  # print (output)

  fin_output = []
  time_sum = 0
  for i_task, i_duration in output: 
    time_sum += i_duration

    # if time_sum < duration: 
    if time_sum <= duration: 
      fin_output += [[i_task, i_duration]]
    else: 
      break
  ftime_sum = 0
  for _fi_task, fi_duration in fin_output: 
    ftime_sum += fi_duration
  
  fin_output[-1][1] += (duration - ftime_sum)
  output = fin_output 

  task_decomp = output
  ret = []
  for decomp_task, duration in task_decomp: 
    ret += [[f"{task} ({decomp_task})", duration]]
  output = ret

  if verbose: 
    print_run_prompts(prompt_template, persona, gpt_param, 
                      prompt_input, prompt, output)
    
  return output, [output, prompt, gpt_param, prompt_input, fail_safe]


class ActionLoc(BaseModel):
  '''
  Action Location class to be used for action sector and action arena
  Takes in "Answer: {name}" and reduces to just name.
  Also hanldes an input of {name}
  '''
  area: str

  # Validator to clean up input and ensure only arena name is stored
  @field_validator('area')
  @classmethod
  def extract_name(cls, value):
    if value.startswith("Answer:"):
      # Remove "Answer:" prefix and strip surrounding spaces
      value = value[len("Answer:"):].strip()
    # Remove surrounding curly brackets if present
    value = re.sub(r'^\{|\}$', '', value).strip()
    return value.strip()  # Ensure no leading or trailing spaces

def run_gpt_prompt_action_sector(
  action_description,
  persona,
  maze,
  test_input=None,
  verbose=False
):
  def create_prompt_input(action_description, persona, maze, test_input=None):
    act_world = f"{maze.access_tile(persona.scratch.curr_tile)['world']}"

    prompt_input = []

    prompt_input += [persona.scratch.get_str_name()]
    prompt_input += [persona.scratch.living_area.split(":")[1]]
    x = f"{act_world}:{persona.scratch.living_area.split(':')[1]}"
    prompt_input += [persona.s_mem.get_str_accessible_sector_arenas(x)]

    prompt_input += [persona.scratch.get_str_name()]
    prompt_input += [f"{maze.access_tile(persona.scratch.curr_tile)['sector']}"]
    x = f"{act_world}:{maze.access_tile(persona.scratch.curr_tile)['sector']}"
    prompt_input += [persona.s_mem.get_str_accessible_sector_arenas(x)]

    if persona.scratch.get_str_daily_plan_req() != "":
      prompt_input += [f"\n{persona.scratch.get_str_daily_plan_req()}"]
    else:
      prompt_input += [""]

    # MAR 11 TEMP
    accessible_sector_str = persona.s_mem.get_str_accessible_sectors(act_world)
    curr = accessible_sector_str.split(", ")
    fin_accessible_sectors = []
    for i in curr:
      if "'s house" in i:
        if persona.scratch.last_name in i:
          fin_accessible_sectors += [i]
      else:
        fin_accessible_sectors += [i]
    accessible_sector_str = ", ".join(fin_accessible_sectors)
    # END MAR 11 TEMP

    prompt_input += [accessible_sector_str]

    action_description_1 = action_description
    action_description_2 = action_description
    if "(" in action_description:
      action_description_1 = action_description.split("(")[0].strip()
      action_description_2 = action_description.split("(")[-1][:-1]
    prompt_input += [persona.scratch.get_str_name()]
    prompt_input += [action_description_1]

    prompt_input += [action_description_2]
    prompt_input += [persona.scratch.get_str_name()]
    return prompt_input


  def __func_clean_up(gpt_response: ActionLoc, prompt=""):
    return gpt_response.area

  def __func_validate(gpt_response, prompt=""):
    sector = __func_clean_up(gpt_response)
    if len(sector.strip()) < 1:
      return False
    if "}" in sector:
      return False
    if "," in sector:
      return False
    return True

  def get_fail_safe():
    fs = "main room"
    return fs

  # # ChatGPT Plugin ===========================================================
  # def __chat_func_clean_up(gpt_response, prompt=""): ############
  #   cr = gpt_response.strip()
  #   return cr

  # def __chat_func_validate(gpt_response, prompt=""): ############
  #   try: 
  #     gpt_response = __func_clean_up(gpt_response, prompt="")
  #   except: 
  #     return False
  #   return True 

  # print ("asdhfapsh8p9hfaiafdsi;ldfj as DEBUG 20") ########
  # gpt_param = {"engine": openai_config["model"], "max_tokens": 15, 
  #              "temperature": 0, "top_p": 1, "stream": False,
  #              "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
  # prompt_template = "persona/prompt_template/v3_ChatGPT/action_location_sector_v2.txt" ########
  # prompt_input = create_prompt_input(action_description, persona, maze)  ########
  # prompt = generate_prompt(prompt_input, prompt_template)
  # example_output = "Johnson Park" ########
  # special_instruction = "The value for the output must contain one of the area options above verbatim (including lower/upper case)." ########
  # fail_safe = get_fail_safe() ########
  # output = ChatGPT_safe_generate_response(prompt, example_output, special_instruction, 3, fail_safe,
  #                                         __chat_func_validate, __chat_func_clean_up, True)
  # if output != False: 
  #   return output, [output, prompt, gpt_param, prompt_input, fail_safe]
  # # ChatGPT Plugin ===========================================================

  gpt_param = {"engine": openai_config["model"], "max_tokens": 100,
               "temperature": 0, "top_p": 1, "stream": False,
               "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
  prompt_template = "persona/prompt_template/v1/action_location_sector_v1.txt"
  prompt_input = create_prompt_input(action_description, persona, maze)
  prompt = generate_prompt(prompt_input, prompt_template)
  fail_safe = get_fail_safe()
  output = safe_generate_structured_response(
    prompt,
    gpt_param,
    ActionLoc,
    5,
    fail_safe,
    __func_validate,
    __func_clean_up,
  )
  y = f"{maze.access_tile(persona.scratch.curr_tile)['world']}"
  x = [i.strip() for i in persona.s_mem.get_str_accessible_sectors(y).split(",")]
  if output not in x:
    # output = random.choice(x)
    output = persona.scratch.living_area.split(":")[1]

  # print ("DEBUG", random.choice(x), "------", output)

  if debug or verbose:
    print_run_prompts(prompt_template, persona, gpt_param,
                      prompt_input, prompt, output)

  return output, [output, prompt, gpt_param, prompt_input, fail_safe]


def run_gpt_prompt_action_arena(
  action_description,
  persona,
  maze, act_world, act_sector,
  test_input=None,
  verbose=False
):
  def create_prompt_input(action_description, persona, maze, act_world, act_sector, test_input=None):
    prompt_input = []
    # prompt_input += [persona.scratch.get_str_name()]
    # prompt_input += [maze.access_tile(persona.scratch.curr_tile)["arena"]]
    # prompt_input += [maze.access_tile(persona.scratch.curr_tile)["sector"]]
    prompt_input += [persona.scratch.get_str_name()]
    x = f"{act_world}:{act_sector}"
    prompt_input += [act_sector]

    # MAR 11 TEMP
    accessible_arena_str = persona.s_mem.get_str_accessible_sector_arenas(x)
    curr = accessible_arena_str.split(", ")
    fin_accessible_arenas = []
    for i in curr:
      if "'s room" in i:
        if persona.scratch.last_name in i:
          fin_accessible_arenas += [i]
      else:
        fin_accessible_arenas += [i]
    accessible_arena_str = ", ".join(fin_accessible_arenas)
    # END MAR 11 TEMP

    prompt_input += [accessible_arena_str]

    action_description_1 = action_description
    action_description_2 = action_description
    if "(" in action_description: 
      action_description_1 = action_description.split("(")[0].strip()
      action_description_2 = action_description.split("(")[-1][:-1]
    prompt_input += [persona.scratch.get_str_name()]
    prompt_input += [action_description_1]

    prompt_input += [action_description_2]
    prompt_input += [persona.scratch.get_str_name()]

    prompt_input += [act_sector]

    prompt_input += [accessible_arena_str]
    # prompt_input += [maze.access_tile(persona.scratch.curr_tile)["arena"]]
    # x = f"{maze.access_tile(persona.scratch.curr_tile)['world']}:{maze.access_tile(persona.scratch.curr_tile)['sector']}:{maze.access_tile(persona.scratch.curr_tile)['arena']}"
    # prompt_input += [persona.s_mem.get_str_accessible_arena_game_objects(x)]

    return prompt_input

  def __func_clean_up(gpt_response: ActionLoc, prompt=""):
    return gpt_response.area

  def __func_validate(gpt_response, prompt=""):
    arena = __func_clean_up(gpt_response)
    if len(arena.strip()) < 1:
      return False
    if "}" in arena:
      return False
    if "," in arena:
      return False
    return True

  def get_fail_safe():
    fs = "main room"
    return fs

  gpt_param = {"engine": openai_config["model"], "max_tokens": 100,
               "temperature": 0, "top_p": 1, "stream": False,
               "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
  prompt_template = "persona/prompt_template/v1/action_location_object_vMar11.txt"
  prompt_input = create_prompt_input(action_description, persona, maze, act_world, act_sector)
  prompt = generate_prompt(prompt_input, prompt_template)

  fail_safe = get_fail_safe()
  output = safe_generate_structured_response(
    prompt,
    gpt_param,
    ActionLoc,
    5,
    fail_safe,
    __func_validate,
    __func_clean_up,
    verbose=False,
  )
  print(output)
  # y = f"{act_world}:{act_sector}"
  # x = [i.strip() for i in persona.s_mem.get_str_accessible_sector_arenas(y).split(",")]
  # if output not in x:
  #   output = random.choice(x)

  if debug or verbose:
    print_run_prompts(prompt_template, persona, gpt_param,
                      prompt_input, prompt, output)

  return output, [output, prompt, gpt_param, prompt_input, fail_safe]


class GameObject(BaseModel):
  object: str

def run_gpt_prompt_action_game_object(
    action_description,
    persona,
    maze,
    temp_address,
    test_input=None,
    verbose=False
):
  def create_prompt_input(action_description,
                          persona,
                          temp_address,
                          test_input=None):
    prompt_input = []
    if "(" in action_description:
      action_description = action_description.split("(")[-1][:-1]
  
    prompt_input += [action_description]
    prompt_input += [persona.s_mem.get_str_accessible_arena_game_objects(temp_address)]
    return prompt_input

  def __func_validate(gpt_response, prompt=""):
    if len(gpt_response.object.strip()) < 1:
      return False
    return True

  def __func_clean_up(gpt_response: GameObject, prompt=""):
    return gpt_response.object

  def get_fail_safe():
    fs = "<random>"
    return fs

  gpt_param = {"engine": openai_config["model"], "max_tokens": 100,
               "temperature": 0, "top_p": 1, "stream": False,
               "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
  prompt_template = "persona/prompt_template/v1/action_object_v2.txt"
  prompt_input = create_prompt_input(action_description,
                                     persona,
                                     temp_address,
                                     test_input)
  prompt = generate_prompt(prompt_input, prompt_template)

  fail_safe = get_fail_safe()
  output = safe_generate_structured_response(
    prompt,
    gpt_param,
    GameObject,
    5,
    fail_safe,
    __func_validate,
    __func_clean_up
  )

  x = [
    i.strip() for i in persona.s_mem.get_str_accessible_arena_game_objects(temp_address).split(",")
  ]
  if output not in x:
    print("ERROR: Output is not an accessible game object:", output)
    print("Choosing a random accessible object instead.")
    output = random.choice(x)
    print("Randomly chosen object:", output)

  if debug or verbose:
    print_run_prompts(prompt_template, persona, gpt_param,
                      prompt_input, prompt, output)
  
  return output, [output, prompt, gpt_param, prompt_input, fail_safe]


class Pronunciatio(BaseModel):
  emoji: str

def run_gpt_prompt_pronunciatio(action_description, persona, verbose=False):
  def create_prompt_input(action_description):
    if "(" in action_description:
      action_description = action_description.split("(")[-1].split(")")[0]
    prompt_input = [action_description]
    return prompt_input

  def get_fail_safe():
    fs = "😋"
    return fs

  # ChatGPT Plugin ===========================================================
  def __chat_func_clean_up(gpt_response: Pronunciatio, prompt=""): ############
    pattern = r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F700-\U0001F77F\U0001F780-\U0001F7FF\U0001F800-\U0001F8FF\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF]'
    result = re.search(pattern, gpt_response.emoji)
    if result:
      return result.group()
    raise ValueError("No emoji found in the response.")

  def __chat_func_validate(gpt_response, prompt=""): ############
    try: 
      __chat_func_clean_up(gpt_response, prompt="")
      if len(gpt_response.emoji) == 0:
        return False
    except:
      traceback.print_exc()
      return False
    return True

  print ("DEBUG 4") ########
  gpt_param = {"engine": openai_config["model"], "max_tokens": 100,
               "temperature": 0, "top_p": 1, "stream": False,
               "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
  prompt_template = "persona/prompt_template/v3_ChatGPT/generate_pronunciatio_v1.txt" ########
  prompt_input = create_prompt_input(action_description)  ########
  prompt = generate_prompt(prompt_input, prompt_template)
  example_output = "🛁🧖‍♀️" ########
  special_instruction = "The value for the output must ONLY contain the emojis." ########
  fail_safe = get_fail_safe()
  output = ChatGPT_safe_generate_structured_response(
    prompt,
    Pronunciatio,
    example_output,
    special_instruction,
    3,
    fail_safe,
    __chat_func_validate,
    __chat_func_clean_up,
    True,
  )

  if verbose:
    print_run_prompts(
      prompt_template,
      persona,
      gpt_param,
      prompt_input,
      prompt,
      output
    )

  if output != False: 
    return output, [output, prompt, gpt_param, prompt_input, fail_safe]
  # ChatGPT Plugin ===========================================================

  # gpt_param = {"engine": openai_config["model"], "max_tokens": 15, 
  #              "temperature": 0, "top_p": 1, "stream": False,
  #              "frequency_penalty": 0, "presence_penalty": 0, "stop": ["\n"]}
  # prompt_template = "persona/prompt_template/v2/generate_pronunciatio_v1.txt"
  # prompt_input = create_prompt_input(action_description)

  # prompt = generate_prompt(prompt_input, prompt_template)

  # fail_safe = get_fail_safe()
  # output = safe_generate_response(prompt, gpt_param, 5, fail_safe,
  #                                  __func_validate, __func_clean_up)

  # if debug or verbose: 
  #   print_run_prompts(prompt_template, persona, gpt_param, 
  #                     prompt_input, prompt, output)
  
  # return output, [output, prompt, gpt_param, prompt_input, fail_safe]


class EventTriple(BaseModel):
  subject: str
  predicate: str
  object: str

def run_gpt_prompt_event_triple(action_description, persona, verbose=False): 
  def create_prompt_input(action_description, persona): 
    if "(" in action_description: 
      action_description = action_description.split("(")[-1].split(")")[0]
    prompt_input = [persona.name, 
                    action_description,
                    persona.name]
    return prompt_input
  
  def __func_clean_up(gpt_response: EventTriple, prompt=""):
    cr = [gpt_response.predicate, gpt_response.object]
    return [x.strip() for x in cr]

  def __func_validate(gpt_response, prompt=""): 
    try: 
      gpt_response = __func_clean_up(gpt_response, prompt="")
      if len(gpt_response) != 2: 
        return False
    except:
      traceback.print_exc()
      return False
    return True 

  def get_fail_safe(persona): 
    fs = ["is", "idle"]
    return fs

  # ChatGPT Plugin ===========================================================
  # def __chat_func_clean_up(gpt_response, prompt=""): ############
  #   cr = gpt_response.strip()
  #   cr = [i.strip() for i in cr.split(")")[0].split(",")]
  #   return cr

  # def __chat_func_validate(gpt_response, prompt=""): ############
  #   try: 
  #     gpt_response = __func_clean_up(gpt_response, prompt="")
  #     if len(gpt_response) != 2: 
  #       return False
  #   except: return False
  #   return True 

  # print ("asdhfapsh8p9hfaiafdsi;ldfj as DEBUG 5") ########
  # gpt_param = {"engine": openai_config["model"], "max_tokens": 15, 
  #              "temperature": 0, "top_p": 1, "stream": False,
  #              "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
  # prompt_template = "persona/prompt_template/v3_ChatGPT/generate_event_triple_v1.txt" ########
  # prompt_input = create_prompt_input(action_description, persona)  ########
  # prompt = generate_prompt(prompt_input, prompt_template)
  # example_output = "(Jane Doe, cooking, breakfast)" ########
  # special_instruction = "The value for the output must ONLY contain the triple. If there is an incomplete element, just say 'None' but there needs to be three elements no matter what." ########
  # fail_safe = get_fail_safe(persona) ########
  # output = ChatGPT_safe_generate_response(prompt, example_output, special_instruction, 3, fail_safe,
  #                                         __chat_func_validate, __chat_func_clean_up, True)
  # if output != False: 
  #   return output, [output, prompt, gpt_param, prompt_input, fail_safe]
  # ChatGPT Plugin ===========================================================

  gpt_param = {"engine": openai_config["model"], "max_tokens": 200, 
               "temperature": 0, "top_p": 1, "stream": False,
               "frequency_penalty": 0, "presence_penalty": 0, "stop": ["\n"]}
  prompt_template = "persona/prompt_template/v2/generate_event_triple_v1.txt"
  prompt_input = create_prompt_input(action_description, persona)
  prompt = generate_prompt(prompt_input, prompt_template)
  fail_safe = get_fail_safe(persona) ########
  output = safe_generate_structured_response(
    prompt,
    gpt_param,
    EventTriple,
    5,
    fail_safe,
    __func_validate,
    __func_clean_up
  )
  output = (persona.name, output[0], output[1])

  if debug or verbose: 
    print_run_prompts(prompt_template, persona, gpt_param, 
                      prompt_input, prompt, output)
  
  return output, [output, prompt, gpt_param, prompt_input, fail_safe]


class ObjDesc(BaseModel):
  description: str

def run_gpt_prompt_act_obj_desc(act_game_object, act_desp, persona, verbose=False):
  def create_prompt_input(act_game_object, act_desp, persona):
    prompt_input = [act_game_object,
                    persona.name,
                    act_desp,
                    act_game_object,
                    act_game_object]
    return prompt_input

  # def __func_clean_up(gpt_response, prompt=""):
  #   return ''.join(gpt_response.split("\n")[0].split(".")[0]).strip()

  # def __func_validate(gpt_response, prompt=""):
  #   try:
  #     gpt_response = __func_clean_up(gpt_response, prompt="")
  #   except:
  #     return False
  #   return True

  def get_fail_safe(act_game_object):
    fs = f"{act_game_object} is idle"
    return fs

  # ChatGPT Plugin ===========================================================
  def __chat_func_clean_up(gpt_response: ObjDesc, prompt=""): ############
    cr = gpt_response.description.strip()
    if cr[-1] == ".":
      cr = cr[:-1]
    return cr

  def __chat_func_validate(gpt_response, prompt=""): ############
    try:
      gpt_response = __chat_func_clean_up(gpt_response, prompt="")
    except:
      traceback.print_exc()
      return False
    return True

  print ("DEBUG 6") ########
  gpt_param = {"engine": openai_config["model"], "max_tokens": 200,
               "temperature": 0, "top_p": 1, "stream": False,
               "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
  prompt_template = "persona/prompt_template/v3_ChatGPT/generate_obj_event_v1.txt" ########
  prompt_input = create_prompt_input(act_game_object, act_desp, persona)  ########
  prompt = generate_prompt(prompt_input, prompt_template)
  example_output = "being fixed" ########
  special_instruction = "The output should ONLY contain the phrase that should go in <fill in>. It should be 15 tokens or less." ########
  fail_safe = get_fail_safe(act_game_object) ########
  output = ChatGPT_safe_generate_structured_response(
    prompt,
    ObjDesc,
    example_output,
    special_instruction,
    3,
    fail_safe,
    __chat_func_validate,
    __chat_func_clean_up,
    True,
  )

  if output != False:
    return output, [output, prompt, gpt_param, prompt_input, fail_safe]

  # ChatGPT Plugin ===========================================================

  # gpt_param = {"engine": openai_config["model"], "max_tokens": 30,
  #              "temperature": 0, "top_p": 1, "stream": False,
  #              "frequency_penalty": 0, "presence_penalty": 0, "stop": ["\n"]}
  # prompt_template = "persona/prompt_template/v2/generate_obj_event_v1.txt"
  # prompt_input = create_prompt_input(act_game_object, act_desp, persona)
  # prompt = generate_prompt(prompt_input, prompt_template)
  # fail_safe = get_fail_safe(act_game_object)
  # output = safe_generate_response(prompt, gpt_param, 5, fail_safe,
  #                                  __func_validate, __func_clean_up)

  # if debug or verbose:
  #   print_run_prompts(prompt_template, persona, gpt_param,
  #                     prompt_input, prompt, output)
  
  # return output, [output, prompt, gpt_param, prompt_input, fail_safe]


def run_gpt_prompt_act_obj_event_triple(act_game_object, act_obj_desc, persona, verbose=False): 
  def create_prompt_input(act_game_object, act_obj_desc): 
    prompt_input = [act_game_object, 
                    act_obj_desc,
                    act_game_object]
    return prompt_input
  
  def __func_clean_up(gpt_response: EventTriple, prompt=""):
    cr = [gpt_response.predicate, gpt_response.object]
    return [x.strip() for x in cr]

  def __func_validate(gpt_response, prompt=""): 
    try: 
      gpt_response = __func_clean_up(gpt_response, prompt="")
      if len(gpt_response) != 2: 
        return False
    except:
      traceback.print_exc()
      return False
    return True 

  def get_fail_safe(act_game_object): 
    fs = ["is", "idle"]
    return fs

  gpt_param = {"engine": openai_config["model"], "max_tokens": 200, 
               "temperature": 0, "top_p": 1, "stream": False,
               "frequency_penalty": 0, "presence_penalty": 0, "stop": ["\n"]}
  prompt_template = "persona/prompt_template/v2/generate_event_triple_v1.txt"
  prompt_input = create_prompt_input(act_game_object, act_obj_desc)
  prompt = generate_prompt(prompt_input, prompt_template)
  fail_safe = get_fail_safe(act_game_object)
  output = safe_generate_structured_response(
    prompt,
    gpt_param,
    EventTriple,
    5,
    fail_safe,
    __func_validate,
    __func_clean_up
  )
  output = (act_game_object, output[0], output[1])

  if debug or verbose: 
    print_run_prompts(prompt_template, persona, gpt_param, 
                      prompt_input, prompt, output)
  
  return output, [output, prompt, gpt_param, prompt_input, fail_safe]


class NewActivity(BaseModel):
  start_time: str
  end_time: str
  main_task: str
  subtask: str

class NewSchedule(BaseModel):
  schedule: list[NewActivity]

def run_gpt_prompt_new_decomp_schedule(persona, 
                                       main_act_dur, 
                                       truncated_act_dur, 
                                       start_time_hour,
                                       end_time_hour, 
                                       inserted_act,
                                       inserted_act_dur,
                                       test_input=None, 
                                       verbose=False): 
  def create_prompt_input(persona, 
                           main_act_dur, 
                           truncated_act_dur, 
                           start_time_hour,
                           end_time_hour, 
                           inserted_act,
                           inserted_act_dur,
                           test_input=None): 
    persona_name = persona.name
    start_hour_str = start_time_hour.strftime("%H:%M %p")
    end_hour_str = end_time_hour.strftime("%H:%M %p")

    original_plan = ""
    for_time = start_time_hour
    for i in main_act_dur: 
      original_plan += f'{for_time.strftime("%H:%M")} ~ {(for_time + datetime.timedelta(minutes=int(i[1]))).strftime("%H:%M")} -- ' + i[0]
      original_plan += "\n"
      for_time += datetime.timedelta(minutes=int(i[1]))

    new_plan_init = ""
    for_time = start_time_hour
    for count, i in enumerate(truncated_act_dur): 
      new_plan_init += f'{for_time.strftime("%H:%M")} ~ {(for_time + datetime.timedelta(minutes=int(i[1]))).strftime("%H:%M")} -- ' + i[0]
      new_plan_init += "\n"
      if count < len(truncated_act_dur) - 1: 
        for_time += datetime.timedelta(minutes=int(i[1]))

    new_plan_init += (for_time + datetime.timedelta(minutes=int(i[1]))).strftime("%H:%M") + " ~"

    prompt_input = [persona_name, 
                    start_hour_str,
                    end_hour_str,
                    original_plan,
                    persona_name,
                    inserted_act,
                    inserted_act_dur,
                    persona_name,
                    start_hour_str,
                    end_hour_str,
                    end_hour_str,
                    new_plan_init]
    return prompt_input
  
  def __func_clean_up(gpt_response: NewSchedule, prompt=""):
    new_schedule = []

    for activity in gpt_response.schedule:
      start_time = activity.start_time
      end_time = activity.end_time
      delta = datetime.datetime.strptime(end_time, "%H:%M") - datetime.datetime.strptime(start_time, "%H:%M")
      delta_min = int(delta.total_seconds() / 60)
      if delta_min < 0:
        delta_min = 0
      action = activity.main_task + f" ({activity.subtask})"
      new_schedule += [[action, delta_min]]

    return new_schedule

  def __func_validate(gpt_response, prompt=""): 
    try: 
      gpt_response = __func_clean_up(gpt_response, prompt)
      dur_sum = 0
      for act, dur in gpt_response: 
        dur_sum += dur
        if str(type(act)) != "<class 'str'>":
          return False 
        if str(type(dur)) != "<class 'int'>":
          return False
      x = prompt.split("\n")[0].split("originally planned schedule from")[-1].strip()[:-1]
      x = [datetime.datetime.strptime(i.strip(), "%H:%M %p") for i in x.split(" to ")]
      delta_min = int((x[1] - x[0]).total_seconds()/60)

      if int(dur_sum) != int(delta_min): 
        return False

    except:
      traceback.print_exc()
      return False
    return True 

  def get_fail_safe(main_act_dur, truncated_act_dur): 
    dur_sum = 0
    for act, dur in main_act_dur: dur_sum += dur

    ret = truncated_act_dur[:]
    ret += main_act_dur[len(ret)-1:]

    # If there are access, we need to trim... 
    ret_dur_sum = 0
    count = 0
    over = None
    for act, dur in ret: 
      ret_dur_sum += dur
      if ret_dur_sum == dur_sum: 
        break
      if ret_dur_sum > dur_sum: 
        over = ret_dur_sum - dur_sum
        break
      count += 1 

    if over: 
      ret = ret[:count+1]
      ret[-1][1] -= over

    return ret

  gpt_param = {"engine": openai_config["model"], "max_tokens": 10000, 
               "temperature": 0, "top_p": 1, "stream": False,
               "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
  prompt_template = "persona/prompt_template/v2/new_decomp_schedule_v1.txt"
  prompt_input = create_prompt_input(persona, 
                                     main_act_dur, 
                                     truncated_act_dur, 
                                     start_time_hour,
                                     end_time_hour, 
                                     inserted_act,
                                     inserted_act_dur,
                                     test_input)
  prompt = generate_prompt(prompt_input, prompt_template)
  fail_safe = get_fail_safe(main_act_dur, truncated_act_dur)
  output = safe_generate_structured_response(
    prompt,
    gpt_param,
    NewSchedule,
    5,
    fail_safe,
    __func_validate,
    __func_clean_up
  )

  # print ("* * * * output")
  # print (output)
  # print ('* * * * fail_safe')
  # print (fail_safe)

  if debug or verbose: 
    print_run_prompts(prompt_template, persona, gpt_param, 
                      prompt_input, prompt, output)
  
  return output, [output, prompt, gpt_param, prompt_input, fail_safe]


class DecideToTalk(BaseModel):
  decision: bool

def run_gpt_prompt_decide_to_talk(persona, target_persona, retrieved,test_input=None, 
                                       verbose=False): 
  def create_prompt_input(init_persona, target_persona, retrieved, 
                          test_input=None): 
    last_chat = init_persona.a_mem.get_last_chat(target_persona.name)
    last_chatted_time = ""
    last_chat_about = ""
    if last_chat: 
      last_chatted_time = last_chat.created.strftime("%B %d, %Y, %H:%M:%S")
      last_chat_about = last_chat.description

    context = ""
    for c_node in retrieved["events"]: 
      curr_desc = c_node.description.split(" ")
      curr_desc[2:3] = ["was"]
      curr_desc = " ".join(curr_desc)
      context +=  f"{curr_desc}. "
    context += "\n"
    for c_node in retrieved["thoughts"]: 
      context +=  f"{c_node.description}. "

    curr_time = init_persona.scratch.curr_time.strftime("%B %d, %Y, %H:%M:%S %p")
    init_act_desc = init_persona.scratch.act_description
    if "(" in init_act_desc: 
      init_act_desc = init_act_desc.split("(")[-1][:-1]
    
    if len(init_persona.scratch.planned_path) == 0 and "waiting" not in init_act_desc: 
      init_p_desc = f"{init_persona.name} is already {init_act_desc}"
    elif "waiting" in init_act_desc:
      init_p_desc = f"{init_persona.name} is {init_act_desc}"
    else: 
      init_p_desc = f"{init_persona.name} is on the way to {init_act_desc}"

    target_act_desc = target_persona.scratch.act_description
    if "(" in target_act_desc: 
      target_act_desc = target_act_desc.split("(")[-1][:-1]
    
    if len(target_persona.scratch.planned_path) == 0 and "waiting" not in init_act_desc: 
      target_p_desc = f"{target_persona.name} is already {target_act_desc}"
    elif "waiting" in init_act_desc:
      target_p_desc = f"{init_persona.name} is {init_act_desc}"
    else: 
      target_p_desc = f"{target_persona.name} is on the way to {target_act_desc}"


    prompt_input = []
    prompt_input += [context]

    prompt_input += [curr_time]

    prompt_input += [init_persona.name]
    prompt_input += [target_persona.name]
    prompt_input += [last_chatted_time]
    prompt_input += [last_chat_about]


    prompt_input += [init_p_desc]
    prompt_input += [target_p_desc]
    prompt_input += [init_persona.name]
    prompt_input += [target_persona.name]
    return prompt_input
  
  def __func_clean_up(gpt_response: DecideToTalk, prompt=""):
    return "yes" if gpt_response.decision is True else "no"

  def __func_validate(gpt_response, prompt=""):
    try:
      if (
        isinstance(gpt_response, DecideToTalk)
        and __func_clean_up(gpt_response, prompt) in ["yes", "no"]
      ):
        return True
      return False
    except:
      traceback.print_exc()
      return False

  def get_fail_safe():
    fs = "yes"
    return fs

  gpt_param = {"engine": openai_config["model"], "max_tokens": 100, 
               "temperature": 0, "top_p": 1, "stream": False,
               "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
  prompt_template = "persona/prompt_template/v2/decide_to_talk_v2.txt"
  prompt_input = create_prompt_input(persona, target_persona, retrieved,
                                     test_input)
  prompt = generate_prompt(prompt_input, prompt_template)

  fail_safe = get_fail_safe()
  output = safe_generate_structured_response(
    prompt,
    gpt_param,
    DecideToTalk,
    5,
    fail_safe,
    __func_validate,
    __func_clean_up
  )

  if debug or verbose: 
    print_run_prompts(prompt_template, persona, gpt_param, 
                      prompt_input, prompt, output)
  
  return output, [output, prompt, gpt_param, prompt_input, fail_safe]


class DecideToReactEnum(IntEnum):
  one = 1
  two = 2
  three = 3

class DecideToReact(BaseModel):
  '''
  Should be a decision 1, 2, or 3
  '''
  decision: DecideToReactEnum

def run_gpt_prompt_decide_to_react(
    persona,
    target_persona,
    retrieved,
    test_input=None,
    verbose=False,
):
  def create_prompt_input(init_persona, target_persona, retrieved,
                          test_input=None):
    context = ""
    for c_node in retrieved["events"]:
      curr_desc = c_node.description.split(" ")
      curr_desc[2:3] = ["was"]
      curr_desc = " ".join(curr_desc)
      context +=  f"{curr_desc}. "
    context += "\n"
    for c_node in retrieved["thoughts"]:
      context +=  f"{c_node.description}. "

    curr_time = init_persona.scratch.curr_time.strftime("%B %d, %Y, %H:%M:%S %p")
    init_act_desc = init_persona.scratch.act_description
    if "(" in init_act_desc:
      init_act_desc = init_act_desc.split("(")[-1][:-1]
    if len(init_persona.scratch.planned_path) == 0:
      loc = ""
      if ":" in init_persona.scratch.act_address:
        loc = init_persona.scratch.act_address.split(":")[-1] + " in " + init_persona.scratch.act_address.split(":")[-2]
      init_p_desc = f"{init_persona.name} is already {init_act_desc} at {loc}"
    else:
      loc = ""
      if ":" in init_persona.scratch.act_address:
        loc = init_persona.scratch.act_address.split(":")[-1] + " in " + init_persona.scratch.act_address.split(":")[-2]
      init_p_desc = f"{init_persona.name} is on the way to {init_act_desc} at {loc}"

    target_act_desc = target_persona.scratch.act_description
    if "(" in target_act_desc:
      target_act_desc = target_act_desc.split("(")[-1][:-1]
    if len(target_persona.scratch.planned_path) == 0:
      loc = ""
      if ":" in target_persona.scratch.act_address:
        loc = target_persona.scratch.act_address.split(":")[-1] + " in " + target_persona.scratch.act_address.split(":")[-2]
      target_p_desc = f"{target_persona.name} is already {target_act_desc} at {loc}"
    else:
      loc = ""
      if ":" in target_persona.scratch.act_address:
        loc = target_persona.scratch.act_address.split(":")[-1] + " in " + target_persona.scratch.act_address.split(":")[-2]
      target_p_desc = f"{target_persona.name} is on the way to {target_act_desc} at {loc}"

    prompt_input = []
    prompt_input += [context]
    prompt_input += [curr_time]
    prompt_input += [init_p_desc]
    prompt_input += [target_p_desc]

    prompt_input += [init_persona.name]
    prompt_input += [init_act_desc]
    prompt_input += [target_persona.name]
    prompt_input += [target_act_desc]

    prompt_input += [init_act_desc]
    return prompt_input

  def __func_validate(gpt_response, prompt=""):
    try:
      if gpt_response.decision in [1, 2, 3]:
        return True
      return False
    except:
      traceback.print_exc()
      return False

  def __func_clean_up(gpt_response: DecideToReact, prompt=""):
    return str(gpt_response.decision)

  def get_fail_safe():
    fs = "3"
    return fs

  gpt_param = {"engine": openai_config["model"], "max_tokens": 100,
               "temperature": 0, "top_p": 1, "stream": False,
               "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
  prompt_template = "persona/prompt_template/v2/decide_to_react_v1.txt"
  prompt_input = create_prompt_input(persona, target_persona, retrieved,
                                     test_input)
  prompt = generate_prompt(prompt_input, prompt_template)

  fail_safe = get_fail_safe()
  output = safe_generate_structured_response(
    prompt,
    gpt_param,
    DecideToReact,
    5,
    fail_safe,
    __func_validate,
    __func_clean_up,
  )
  if debug or verbose:
    print_run_prompts(prompt_template, persona, gpt_param,
                      prompt_input, prompt, output)
  
  return output, [output, prompt, gpt_param, prompt_input, fail_safe]


# def run_gpt_prompt_create_conversation(persona, target_persona, curr_loc,
#                                        test_input=None, verbose=False): 
#   def create_prompt_input(init_persona, target_persona, curr_loc, 
#                           test_input=None): 

#     prev_convo_insert = "\n"
#     if init_persona.a_mem.seq_chat: 
#       for i in init_persona.a_mem.seq_chat: 
#         if i.object == target_persona.scratch.name: 
#           v1 = int((init_persona.scratch.curr_time - i.created).total_seconds()/60)
#           prev_convo_insert += f'{str(v1)} minutes ago, they had the following conversation.\n'
#           for row in i.filling: 
#             prev_convo_insert += f'{row[0]}: "{row[1]}"\n'
#           break
#     if prev_convo_insert == "\n": 
#       prev_convo_insert = ""
#     if init_persona.a_mem.seq_chat: 
#       if int((init_persona.scratch.curr_time - init_persona.a_mem.seq_chat[-1].created).total_seconds()/60) > 480: 
#         prev_convo_insert = ""

#     init_persona_thought_nodes = init_persona.a_mem.retrieve_relevant_thoughts(target_persona.scratch.act_event[0],
#                                 target_persona.scratch.act_event[1],
#                                 target_persona.scratch.act_event[2])
#     init_persona_thought = ""
#     for i in init_persona_thought_nodes: 
#       init_persona_thought += f"-- {i.description}\n"

#     target_persona_thought_nodes = target_persona.a_mem.retrieve_relevant_thoughts(init_persona.scratch.act_event[0],
#                                 init_persona.scratch.act_event[1],
#                                 init_persona.scratch.act_event[2])
#     target_persona_thought = ""
#     for i in target_persona_thought_nodes: 
#       target_persona_thought += f"-- {i.description}\n"

#     init_persona_curr_desc = ""
#     if init_persona.scratch.planned_path: 
#       init_persona_curr_desc = f"{init_persona.name} is on the way to {init_persona.scratch.act_description}"
#     else: 
#       init_persona_curr_desc = f"{init_persona.name} is {init_persona.scratch.act_description}"

#     target_persona_curr_desc = ""
#     if target_persona.scratch.planned_path: 
#       target_persona_curr_desc = f"{target_persona.name} is on the way to {target_persona.scratch.act_description}"
#     else: 
#       target_persona_curr_desc = f"{target_persona.name} is {target_persona.scratch.act_description}"
 
#     curr_loc = curr_loc["arena"]

#     prompt_input = []
#     prompt_input += [init_persona.scratch.get_str_iss()]
#     prompt_input += [target_persona.scratch.get_str_iss()]

#     prompt_input += [init_persona.name]
#     prompt_input += [target_persona.name]
#     prompt_input += [init_persona_thought]

#     prompt_input += [target_persona.name]
#     prompt_input += [init_persona.name]
#     prompt_input += [target_persona_thought]

#     prompt_input += [init_persona.scratch.curr_time.strftime("%B %d, %Y, %H:%M:%S")]

#     prompt_input += [init_persona_curr_desc]
#     prompt_input += [target_persona_curr_desc]

#     prompt_input += [prev_convo_insert]

#     prompt_input += [init_persona.name]
#     prompt_input += [target_persona.name]

#     prompt_input += [curr_loc]
#     prompt_input += [init_persona.name]
#     return prompt_input
  
#   def __func_clean_up(gpt_response, prompt=""):
#     # print ("???")
#     # print (gpt_response)

#     gpt_response = (prompt + gpt_response).split("What would they talk about now?")[-1].strip()
#     content = re.findall('"([^"]*)"', gpt_response)

#     speaker_order = []
#     for i in gpt_response.split("\n"): 
#       name = i.split(":")[0].strip() 
#       if name: 
#         speaker_order += [name]

#     ret = []
#     for count, speaker in enumerate(speaker_order): 
#       ret += [[speaker, content[count]]]

#     return ret

#   def __func_validate(gpt_response, prompt=""): 
#     try: 
#       __func_clean_up(gpt_response, prompt)
#       return True
#     except:
#       traceback.print_exc()
#       return False 

#   def get_fail_safe(init_persona, target_persona): 
#     convo = [[init_persona.name, "Hi!"], 
#              [target_persona.name, "Hi!"]]
#     return convo


#   gpt_param = {"engine": openai_config["model"], "max_tokens": 1000, 
#                "temperature": 0.7, "top_p": 1, "stream": False,
#                "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
#   prompt_template = "persona/prompt_template/v2/create_conversation_v2.txt"
#   prompt_input = create_prompt_input(persona, target_persona, curr_loc, 
#                                      test_input)
#   prompt = generate_prompt(prompt_input, prompt_template)

#   fail_safe = get_fail_safe(persona, target_persona)
#   output = safe_generate_response(prompt, gpt_param, 5, fail_safe,
#                                    __func_validate, __func_clean_up)

#   if debug or verbose: 
#     print_run_prompts(prompt_template, persona, gpt_param, 
#                       prompt_input, prompt, output)
  
#   return output, [output, prompt, gpt_param, prompt_input, fail_safe]


class ConversationSummary(BaseModel):
  summary: str

def run_gpt_prompt_summarize_conversation(persona, conversation, test_input=None, verbose=False):
  def create_prompt_input(conversation, test_input=None):
    convo_str = ""
    for row in conversation:
      convo_str += f'{row[0]}: "{row[1]}"\n'

    prompt_input = [convo_str]
    return prompt_input
  
  # def __func_clean_up(gpt_response: ConversationSummary, prompt=""):
  #   ret = "conversing about " + gpt_response.conversation.strip()
  #   return ret

  # def __func_validate(gpt_response, prompt=""): 
  #   try: 
  #     __func_clean_up(gpt_response, prompt)
  #     return True
  #   except:
  #     traceback.print_exc()
  #     return False

  def get_fail_safe():
    return "conversing with a housemate about morning greetings"

  # ChatGPT Plugin ===========================================================
  def __chat_func_clean_up(gpt_response: ConversationSummary, prompt=""): ############
    ret = "conversing about " + gpt_response.summary.strip()
    return ret

  def __chat_func_validate(gpt_response, prompt=""): ############
    try: 
      __chat_func_clean_up(gpt_response, prompt)
      return True
    except:
      traceback.print_exc()
      return False

  print ("DEBUG 11") ########
  gpt_param = {"engine": openai_config["model"], "max_tokens": 300,
               "temperature": 0, "top_p": 1, "stream": False,
               "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
  prompt_template = "persona/prompt_template/v3_ChatGPT/summarize_conversation_v1.txt" ########
  prompt_input = create_prompt_input(conversation, test_input)  ########
  prompt = generate_prompt(prompt_input, prompt_template)
  example_output = "conversing about what to eat for lunch" ########
  special_instruction = "The output must continue the sentence above by filling in the <fill in> tag. Don't start with 'this is a conversation about...' Just finish the sentence but do not miss any important details (including who are chatting)." ########
  fail_safe = get_fail_safe() ########
  output = ChatGPT_safe_generate_structured_response(
    prompt,
    ConversationSummary,
    example_output,
    special_instruction,
    3,
    fail_safe,
    __chat_func_validate,
    __chat_func_clean_up,
    True,
  )

  if output != False:
    return output, [output, prompt, gpt_param, prompt_input, fail_safe]

  # ChatGPT Plugin ===========================================================

  # gpt_param = {"engine": openai_config["model"], "max_tokens": 50,
  #              "temperature": 0, "top_p": 1, "stream": False,
  #              "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
  # prompt_template = "persona/prompt_template/v2/summarize_conversation_v1.txt"
  # prompt_input = create_prompt_input(conversation, test_input)
  # prompt = generate_prompt(prompt_input, prompt_template)

  # fail_safe = get_fail_safe()
  # output = safe_generate_response(prompt, gpt_param, 5, fail_safe,
  #                                  __func_validate, __func_clean_up)

  # if debug or verbose:
  #   print_run_prompts(prompt_template, persona, gpt_param,
  #                     prompt_input, prompt, output)
  
  # return output, [output, prompt, gpt_param, prompt_input, fail_safe]


# class Keywords(BaseModel):
#   emotive_keywords: list[str]
#   factual_keywords: list[str]
#   all_keywords: list[list]

# def run_gpt_prompt_extract_keywords(persona, description, test_input=None, verbose=False): 
#   def create_prompt_input(description, test_input=None): 
#     if "\n" in description: 
#       description = description.replace("\n", " <LINE_BREAK> ")
#     prompt_input = [description]
#     return prompt_input
  
#   def __func_clean_up(gpt_response, prompt=""):
#     print ("???")
#     print (gpt_response)
#     gpt_response = gpt_response.strip().split("Emotive keywords:")
#     factual = [i.strip() for i in gpt_response[0].split(",")]
#     emotive = [i.strip() for i in gpt_response[1].split(",")]
#     all_keywords = factual + emotive
#     ret = []
#     for i in all_keywords: 
#       if i: 
#         i = i.lower()
#         if i[-1] == ".": 
#           i = i[:-1]
#         ret += [i]
#     print (ret)
#     return set(ret)

#   def __func_validate(gpt_response, prompt=""): 
#     try: 
#       __func_clean_up(gpt_response, prompt)
#       return True
#     except:
#       traceback.print_exc()
#       return False 

#   def get_fail_safe(): 
#     return []

#   gpt_param = {"engine": openai_config["model"], "max_tokens": 50, 
#                "temperature": 0, "top_p": 1, "stream": False,
#                "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
#   prompt_template = "persona/prompt_template/v2/get_keywords_v1.txt"
#   prompt_input = create_prompt_input(description, test_input)
#   prompt = generate_prompt(prompt_input, prompt_template)

#   fail_safe = get_fail_safe()
#   output = safe_generate_response(prompt, gpt_param, 5, fail_safe,
#                                    __func_validate, __func_clean_up)

#   if debug or verbose: 
#     print_run_prompts(prompt_template, persona, gpt_param, 
#                       prompt_input, prompt, output)
  
#   return output, [output, prompt, gpt_param, prompt_input, fail_safe]


# def run_gpt_prompt_keyword_to_thoughts(persona, keyword, concept_summary, test_input=None, verbose=False): 
#   def create_prompt_input(persona, keyword, concept_summary, test_input=None): 
#     prompt_input = [keyword, concept_summary, persona.name]
#     return prompt_input
  
#   def __func_clean_up(gpt_response, prompt=""):
#     gpt_response = gpt_response.strip()
#     return gpt_response

#   def __func_validate(gpt_response, prompt=""): 
#     try: 
#       __func_clean_up(gpt_response, prompt)
#       return True
#     except:
#       traceback.print_exc()
#       return False 

#   def get_fail_safe(): 
#     return ""

#   gpt_param = {"engine": openai_config["model"], "max_tokens": 40, 
#                "temperature": 0.7, "top_p": 1, "stream": False,
#                "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
#   prompt_template = "persona/prompt_template/v2/keyword_to_thoughts_v1.txt"
#   prompt_input = create_prompt_input(persona, keyword, concept_summary)
#   prompt = generate_prompt(prompt_input, prompt_template)

#   fail_safe = get_fail_safe()
#   output = safe_generate_response(prompt, gpt_param, 5, fail_safe,
#                                    __func_validate, __func_clean_up)

#   if debug or verbose: 
#     print_run_prompts(prompt_template, persona, gpt_param, 
#                       prompt_input, prompt, output)
  
#   return output, [output, prompt, gpt_param, prompt_input, fail_safe]


# def run_gpt_prompt_convo_to_thoughts(persona, 
#                                     init_persona_name,  
#                                     target_persona_name,
#                                     convo_str,
#                                     fin_target, test_input=None, verbose=False): 
#   def create_prompt_input(init_persona_name,  
#                                     target_persona_name,
#                                     convo_str,
#                                     fin_target, test_input=None): 
#     prompt_input = [init_persona_name,
#                     target_persona_name,
#                     convo_str,
#                     init_persona_name,
#                     fin_target]
#     return prompt_input
  
#   def __func_clean_up(gpt_response, prompt=""):
#     gpt_response = gpt_response.strip()
#     return gpt_response

#   def __func_validate(gpt_response, prompt=""): 
#     try: 
#       __func_clean_up(gpt_response, prompt)
#       return True
#     except:
#       traceback.print_exc()
#       return False 

#   def get_fail_safe(): 
#     return ""

#   gpt_param = {"engine": openai_config["model"], "max_tokens": 40, 
#                "temperature": 0.7, "top_p": 1, "stream": False,
#                "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
#   prompt_template = "persona/prompt_template/v2/convo_to_thoughts_v1.txt"
#   prompt_input = create_prompt_input(init_persona_name,  
#                                     target_persona_name,
#                                     convo_str,
#                                     fin_target)
#   prompt = generate_prompt(prompt_input, prompt_template)

#   fail_safe = get_fail_safe()
#   output = safe_generate_response(prompt, gpt_param, 5, fail_safe,
#                                    __func_validate, __func_clean_up)

#   if debug or verbose: 
#     print_run_prompts(prompt_template, persona, gpt_param, 
#                       prompt_input, prompt, output)
  
#   return output, [output, prompt, gpt_param, prompt_input, fail_safe]


class Poignancy(BaseModel):
  poignancy: int

def run_gpt_prompt_event_poignancy(persona, event_description, test_input=None, verbose=False):
  def create_prompt_input(persona, event_description, test_input=None):
    prompt_input = [persona.scratch.name,
                    persona.scratch.get_str_iss(),
                    persona.scratch.name,
                    event_description]
    return prompt_input

  # def __func_clean_up(gpt_response: Poignancy, prompt=""):
  #   response = gpt_response.poignancy
  #   return response

  # def __func_validate(gpt_response, prompt=""):
  #   try:
  #     __func_clean_up(gpt_response, prompt)
  #     return True
  #   except:
  #     traceback.print_exc()
  #     return False

  def get_fail_safe():
    return 4

  # ChatGPT Plugin ===========================================================
  def __chat_func_clean_up(gpt_response: Poignancy, prompt=""): ############
    response = gpt_response.poignancy
    return response

  def __chat_func_validate(gpt_response, prompt=""): ############
    try:
      poignancy = __chat_func_clean_up(gpt_response, prompt)
      return poignancy is not None
    except:
      traceback.print_exc()
      return False

  print ("DEBUG 7") ########
  gpt_param = {"engine": openai_config["model"], "max_tokens": 100,
               "temperature": 0, "top_p": 1, "stream": False,
               "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
  prompt_template = "persona/prompt_template/v3_ChatGPT/poignancy_event_v1.txt" ########
  prompt_input = create_prompt_input(persona, event_description)  ########
  prompt = generate_prompt(prompt_input, prompt_template)
  example_output = "5" ########
  special_instruction = "The output should ONLY contain ONE integer value on the scale of 1 to 10." ########
  fail_safe = get_fail_safe() ########
  output = ChatGPT_safe_generate_structured_response(
    prompt,
    Poignancy,
    example_output,
    special_instruction,
    3,
    fail_safe,
    __chat_func_validate,
    __chat_func_clean_up,
    True,
  )
  if output != False:
    return output, [output, prompt, gpt_param, prompt_input, fail_safe]

  # ChatGPT Plugin ===========================================================

  # gpt_param = {"engine": openai_config["model"], "max_tokens": 3, 
  #              "temperature": 0, "top_p": 1, "stream": False,
  #              "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
  # prompt_template = "persona/prompt_template/v2/poignancy_event_v1.txt"
  # prompt_input = create_prompt_input(persona, event_description)
  # prompt = generate_prompt(prompt_input, prompt_template)

  # fail_safe = get_fail_safe()
  # output = safe_generate_response(prompt, gpt_param, 5, fail_safe,
  #                                  __func_validate, __func_clean_up)

  # if debug or verbose: 
  #   print_run_prompts(prompt_template, persona, gpt_param, 
  #                     prompt_input, prompt, output)
  
  # return output, [output, prompt, gpt_param, prompt_input, fail_safe]


# def run_gpt_prompt_thought_poignancy(persona, event_description, test_input=None, verbose=False): 
#   def create_prompt_input(persona, event_description, test_input=None): 
#     prompt_input = [persona.scratch.name,
#                     persona.scratch.get_str_iss(),
#                     persona.scratch.name,
#                     event_description]
#     return prompt_input
  
#   def __func_clean_up(gpt_response, prompt=""):
#     gpt_response = int(gpt_response.strip())
#     return gpt_response

#   def __func_validate(gpt_response, prompt=""): 
#     try: 
#       __func_clean_up(gpt_response, prompt)
#       return True
#     except:
#       traceback.print_exc()
#       return False 

#   def get_fail_safe(): 
#     return 4

#   # ChatGPT Plugin ===========================================================
#   def __chat_func_clean_up(gpt_response, prompt=""): ############
#     gpt_response = int(gpt_response)
#     return gpt_response

#   def __chat_func_validate(gpt_response, prompt=""): ############
#     try: 
#       __func_clean_up(gpt_response, prompt)
#       return True
#     except:
#       traceback.print_exc()
#       return False 

#   print ("DEBUG 8") ########
#   gpt_param = {"engine": openai_config["model"], "max_tokens": 15, 
#                "temperature": 0, "top_p": 1, "stream": False,
#                "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
#   prompt_template = "persona/prompt_template/v3_ChatGPT/poignancy_thought_v1.txt" ########
#   prompt_input = create_prompt_input(persona, event_description)  ########
#   prompt = generate_prompt(prompt_input, prompt_template)
#   example_output = "5" ########
#   special_instruction = "The output should ONLY contain ONE integer value on the scale of 1 to 10." ########
#   fail_safe = get_fail_safe() ########
#   output = ChatGPT_safe_generate_response(prompt, example_output, special_instruction, 3, fail_safe,
#                                           __chat_func_validate, __chat_func_clean_up, True)
#   if output != False: 
#     return output, [output, prompt, gpt_param, prompt_input, fail_safe]
#   # ChatGPT Plugin ===========================================================

#   # gpt_param = {"engine": openai_config["model"], "max_tokens": 3, 
#   #              "temperature": 0, "top_p": 1, "stream": False,
#   #              "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
#   # prompt_template = "persona/prompt_template/v2/poignancy_thought_v1.txt"
#   # prompt_input = create_prompt_input(persona, event_description)
#   # prompt = generate_prompt(prompt_input, prompt_template)

#   # fail_safe = get_fail_safe()
#   # output = safe_generate_response(prompt, gpt_param, 5, fail_safe,
#   #                                  __func_validate, __func_clean_up)

#   # if debug or verbose: 
#   #   print_run_prompts(prompt_template, persona, gpt_param, 
#   #                     prompt_input, prompt, output)
  
#   # return output, [output, prompt, gpt_param, prompt_input, fail_safe]


class IntPoignancy(BaseModel):
  poignancy: int

def run_gpt_prompt_chat_poignancy(persona, event_description, test_input=None, verbose=False):
  def create_prompt_input(persona, event_description, test_input=None):
    prompt_input = [persona.scratch.name,
                    persona.scratch.get_str_iss(),
                    persona.scratch.name,
                    event_description]
    return prompt_input

  # def __func_clean_up(gpt_response: IntPoignancy, prompt=""):
  #   gpt_response = int(gpt_response.strip())
  #   return gpt_response

  # def __func_validate(gpt_response, prompt=""): 
  #   try: 
  #     __func_clean_up(gpt_response, prompt)
  #     return True
  #   except:
  #     traceback.print_exc()
  #     return False 

  def get_fail_safe():
    return 4

  # ChatGPT Plugin ===========================================================
  def __chat_func_clean_up(gpt_response: IntPoignancy, prompt=""): ############
    return gpt_response.poignancy

  def __chat_func_validate(gpt_response, prompt=""): ############
    try:
      if not isinstance(gpt_response, IntPoignancy):
        return False
      __chat_func_clean_up(gpt_response, prompt)
      return True
    except:
      traceback.print_exc()
      return False

  print ("DEBUG 9") ########
  gpt_param = {"engine": openai_config["model"], "max_tokens": 100,
               "temperature": 0, "top_p": 1, "stream": False,
               "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
  prompt_template = "persona/prompt_template/v3_ChatGPT/poignancy_chat_v1.txt" ########
  prompt_input = create_prompt_input(persona, event_description)  ########
  prompt = generate_prompt(prompt_input, prompt_template)
  example_output = "5" ########
  special_instruction = "The output should ONLY contain ONE integer value on the scale of 1 to 10." ########
  fail_safe = get_fail_safe() ########
  output = ChatGPT_safe_generate_structured_response(
    prompt,
    IntPoignancy,
    example_output,
    special_instruction,
    3,
    fail_safe,
    __chat_func_validate,
    __chat_func_clean_up,
    True,
  )
  if output != False: 
    return output, [output, prompt, gpt_param, prompt_input, fail_safe]
  # ChatGPT Plugin ===========================================================

  # gpt_param = {"engine": openai_config["model"], "max_tokens": 3, 
  #              "temperature": 0, "top_p": 1, "stream": False,
  #              "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
  # prompt_template = "persona/prompt_template/v2/poignancy_chat_v1.txt"
  # prompt_input = create_prompt_input(persona, event_description)
  # prompt = generate_prompt(prompt_input, prompt_template)

  # fail_safe = get_fail_safe()
  # output = safe_generate_response(prompt, gpt_param, 5, fail_safe,
  #                                  __func_validate, __func_clean_up)

  # if debug or verbose: 
  #   print_run_prompts(prompt_template, persona, gpt_param, 
  #                     prompt_input, prompt, output)
  
  # return output, [output, prompt, gpt_param, prompt_input, fail_safe]


class FocalPoint(BaseModel):
  questions: list[str]

def run_gpt_prompt_focal_pt(persona, statements, n, test_input=None, verbose=False): 
  def create_prompt_input(persona, statements, n, test_input=None): 
    prompt_input = [statements, str(n)]
    return prompt_input
  
  # def __func_clean_up(gpt_response: FocalPoint, prompt=""):
  #   gpt_response = "1) " + gpt_response.strip()
  #   ret = []
  #   for i in gpt_response.split("\n"): 
  #     ret += [i.split(") ")[-1]]
  #   return ret

  # def __func_validate(gpt_response, prompt=""): 
  #   try: 
  #     __func_clean_up(gpt_response, prompt)
  #     return True
  #   except:
  #     traceback.print_exc()
  #     return False 

  def get_fail_safe(n): 
    return ["Who am I"] * n

  # ChatGPT Plugin ===========================================================
  def __chat_func_clean_up(gpt_response: FocalPoint, prompt=""): ############
    ret = gpt_response.questions
    return ret

  def __chat_func_validate(gpt_response, prompt=""): ############
    try: 
      if not isinstance(gpt_response, FocalPoint):
        return False
      __chat_func_clean_up(gpt_response, prompt)
      return True
    except:
      traceback.print_exc()
      return False 

  print ("DEBUG 12") ########
  gpt_param = {"engine": openai_config["model"], "max_tokens": 300,
               "temperature": 0, "top_p": 1, "stream": False,
               "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
  prompt_template = "persona/prompt_template/v3_ChatGPT/generate_focal_pt_v1.txt" ########
  prompt_input = create_prompt_input(persona, statements, n)  ########
  prompt = generate_prompt(prompt_input, prompt_template)
  example_output = '["What should Jane do for lunch", "Does Jane like strawberry", "Who is Jane"]' ########
  special_instruction = "Output must be a list of str." ########
  fail_safe = get_fail_safe(n) ########
  output = ChatGPT_safe_generate_structured_response(
    prompt,
    FocalPoint,
    example_output,
    special_instruction,
    3, 
    fail_safe,
    __chat_func_validate,
    __chat_func_clean_up,
    True,
  )

  if output != False:
    return output, [output, prompt, gpt_param, prompt_input, fail_safe]
  # ChatGPT Plugin ===========================================================

  gpt_param = {"engine": openai_config["model"], "max_tokens": 300,
               "temperature": 0, "top_p": 1, "stream": False,
               "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
  prompt_template = "persona/prompt_template/v2/generate_focal_pt_v1.txt"
  prompt_input = create_prompt_input(persona, statements, n)
  prompt = generate_prompt(prompt_input, prompt_template)

  fail_safe = get_fail_safe(n)
  output = safe_generate_structured_response(
    prompt,
    gpt_param,
    IntPoignancy,
    5,
    fail_safe,
    __func_validate,
    __func_clean_up
  )

  if debug or verbose:
    print_run_prompts(prompt_template, persona, gpt_param,
                      prompt_input, prompt, output)
  
  return output, [output, prompt, gpt_param, prompt_input, fail_safe]


class Insight(BaseModel):
  insight: str
  because_of: list[int]

class InsightGuidance(BaseModel):
  insights: list[Insight]

def run_gpt_prompt_insight_and_guidance(persona, statements, n, test_input=None, verbose=False):
  def create_prompt_input(persona, statements, n, test_input=None):
    prompt_input = [statements, str(n)]
    return prompt_input

  def __func_clean_up(gpt_response: InsightGuidance, prompt=""):
    ret = {item.insight:item.because_of for item in gpt_response.insights}
    return ret

  def __func_validate(gpt_response, prompt=""):
    try:
      if not isinstance(gpt_response, InsightGuidance):
        return False
      __func_clean_up(gpt_response, prompt)
      return True
    except:
      traceback.print_exc()
      return False

  def get_fail_safe(n):
    return {"I am okay": [1, 2, 3]}

  gpt_param = {"engine": openai_config["model"], "max_tokens": 500,
               "temperature": 0.5, "top_p": 1, "stream": False,
               "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
  prompt_template = "persona/prompt_template/v2/insight_and_evidence_v1.txt"
  prompt_input = create_prompt_input(persona, statements, n)
  prompt = generate_prompt(prompt_input, prompt_template)

  fail_safe = get_fail_safe(n)
  output = safe_generate_structured_response(
    prompt, 
    gpt_param,
    InsightGuidance, 
    5, 
    fail_safe,
    __func_validate,
    __func_clean_up)

  if debug or verbose: 
    print_run_prompts(prompt_template, persona, gpt_param, 
                      prompt_input, prompt, output)
  
  return output, [output, prompt, gpt_param, prompt_input, fail_safe]


class IdeaSummary(BaseModel):
  idea_summary: str

def run_gpt_prompt_agent_chat_summarize_ideas(
    persona,
    target_persona,
    statements,
    curr_context,
    test_input=None,
    verbose=False
):
  def create_prompt_input(persona, target_persona, statements, curr_context, test_input=None):
    prompt_input = [persona.scratch.get_str_curr_date_str(), curr_context, persona.scratch.currently,
                    statements, persona.scratch.name, target_persona.scratch.name]
    return prompt_input
  
  # def __func_clean_up(gpt_response: Idea_Summary, prompt=""):
  #   return gpt_response.idea_summary

  # def __func_validate(gpt_response, prompt=""):
  #   try:
  #     __func_clean_up(gpt_response, prompt)
  #     return True
  #   except:
  #     traceback.print_exc()
  #     return False

  def get_fail_safe():
    return "..."

  # ChatGPT Plugin ===========================================================
  def __chat_func_clean_up(gpt_response: IdeaSummary, prompt=""): ############
    return gpt_response.idea_summary

  def __chat_func_validate(gpt_response, prompt=""): ############
    try:
      if not isinstance(gpt_response, IdeaSummary):
        return False
      return True
    except:
      traceback.print_exc()
      return False

  print ("DEBUG 17") ########
  gpt_param = {"engine": openai_config["model"], "max_tokens": 300, 
               "temperature": 0, "top_p": 1, "stream": False,
               "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
  prompt_template = "persona/prompt_template/v3_ChatGPT/summarize_chat_ideas_v1.txt" ########
  prompt_input = create_prompt_input(persona, target_persona, statements, curr_context)  ########
  prompt = generate_prompt(prompt_input, prompt_template)
  example_output = 'Jane Doe is working on a project' ########
  special_instruction = 'The output should be a string that responds to the question.' ########
  fail_safe = get_fail_safe() ########
  output = ChatGPT_safe_generate_structured_response(
    prompt,
    IdeaSummary,
    example_output,
    special_instruction,
    3,
    fail_safe,
    __chat_func_validate,
    __chat_func_clean_up,
    True
  )

  if output != False:
    return output, [output, prompt, gpt_param, prompt_input, fail_safe]
  # ChatGPT Plugin ===========================================================

  # gpt_param = {"engine": openai_config["model"], "max_tokens": 150, 
  #              "temperature": 0.5, "top_p": 1, "stream": False,
  #              "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
  # prompt_template = "persona/prompt_template/v2/summarize_chat_ideas_v1.txt"
  # prompt_input = create_prompt_input(persona, target_persona, statements, curr_context)
  # prompt = generate_prompt(prompt_input, prompt_template)

  # fail_safe = get_fail_safe()
  # output = safe_generate_response(prompt, gpt_param, 5, fail_safe,
  #                                  __func_validate, __func_clean_up)

  # if debug or verbose: 
  #   print_run_prompts(prompt_template, persona, gpt_param, 
  #                     prompt_input, prompt, output)
  
  # return output, [output, prompt, gpt_param, prompt_input, fail_safe]


class ChatSummarizeRelationship(BaseModel):
  summary: str

def run_gpt_prompt_agent_chat_summarize_relationship(
    persona,
    target_persona,
    statements,
    test_input=None,
    verbose=False
):
  def create_prompt_input(persona, target_persona, statements, test_input=None):
    prompt_input = [statements, persona.scratch.name, target_persona.scratch.name]
    return prompt_input

  # def __func_clean_up(gpt_response: ChatSummarizeRelationship, prompt=""):
  #   return gpt_response.summary

  # def __func_validate(gpt_response, prompt=""):
  #   try:
  #     if not isinstance(gpt_response, ChatSummarizeRelationship):
  #       return False
  #     __func_clean_up(gpt_response, prompt)
  #     return True
  #   except:
  #     traceback.print_exc()
  #     return False

  def get_fail_safe():
    return "..."

  # ChatGPT Plugin ===========================================================
  def __chat_func_clean_up(gpt_response: ChatSummarizeRelationship, prompt=""): ############
    return gpt_response.summary

  def __chat_func_validate(gpt_response, prompt=""): ############
    try:
      if not isinstance(gpt_response, ChatSummarizeRelationship):
        return False
      __chat_func_clean_up(gpt_response, prompt)
      return True
    except:
      traceback.print_exc()
      return False

  print ("DEBUG 18") ########
  gpt_param = {"engine": openai_config["model"], "max_tokens": 200,
               "temperature": 0, "top_p": 1, "stream": False,
               "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
  prompt_template = "persona/prompt_template/v3_ChatGPT/summarize_chat_relationship_v2.txt" ########
  prompt_input = create_prompt_input(persona, target_persona, statements)  ########
  prompt = generate_prompt(prompt_input, prompt_template)
  example_output = 'Jane Doe is working on a project' ########
  special_instruction = 'The output should be a string that responds to the question.' ########
  fail_safe = get_fail_safe() ########
  output = ChatGPT_safe_generate_structured_response(
    prompt,
    ChatSummarizeRelationship,
    example_output,
    special_instruction,
    3, 
    fail_safe,
    __chat_func_validate,
    __chat_func_clean_up,
    True,
  )
  if output != False:
    return output, [output, prompt, gpt_param, prompt_input, fail_safe]
  # ChatGPT Plugin ===========================================================

  # gpt_param = {"engine": openai_config["model"], "max_tokens": 150, 
  #              "temperature": 0.5, "top_p": 1, "stream": False,
  #              "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
  # prompt_template = "persona/prompt_template/v2/summarize_chat_relationship_v1.txt"
  # prompt_input = create_prompt_input(persona, target_persona, statements)
  # prompt = generate_prompt(prompt_input, prompt_template)

  # fail_safe = get_fail_safe()
  # output = safe_generate_response(prompt, gpt_param, 5, fail_safe,
  #                                  __func_validate, __func_clean_up)

  # if debug or verbose: 
  #   print_run_prompts(prompt_template, persona, gpt_param, 
  #                     prompt_input, prompt, output)
  
  # return output, [output, prompt, gpt_param, prompt_input, fail_safe]


# class PromptAgentChat(BaseModel):
#   convo: list[list[str]]

# def run_gpt_prompt_agent_chat(maze, persona, target_persona,
#                                curr_context, 
#                                init_summ_idea, 
#                                target_summ_idea, test_input=None, verbose=False): 
#   def create_prompt_input(persona, target_persona, curr_context, init_summ_idea, target_summ_idea, test_input=None): 
#     prev_convo_insert = "\n"
#     if persona.a_mem.seq_chat: 
#       for i in persona.a_mem.seq_chat: 
#         if i.object == target_persona.scratch.name: 
#           v1 = int((persona.scratch.curr_time - i.created).total_seconds()/60)
#           prev_convo_insert += f'{str(v1)} minutes ago, {persona.scratch.name} and {target_persona.scratch.name} were already {i.description} This context takes place after that conversation.'
#           break
#     if prev_convo_insert == "\n": 
#       prev_convo_insert = ""
#     if persona.a_mem.seq_chat: 
#       if int((persona.scratch.curr_time - persona.a_mem.seq_chat[-1].created).total_seconds()/60) > 480: 
#         prev_convo_insert = ""
#     print (prev_convo_insert)

#     curr_sector = f"{maze.access_tile(persona.scratch.curr_tile)['sector']}"
#     curr_arena= f"{maze.access_tile(persona.scratch.curr_tile)['arena']}"
#     curr_location = f"{curr_arena} in {curr_sector}"

#     prompt_input = [persona.scratch.currently, 
#                     target_persona.scratch.currently, 
#                     prev_convo_insert,
#                     curr_context, 
#                     curr_location,

#                     persona.scratch.name,
#                     init_summ_idea, 
#                     persona.scratch.name,
#                     target_persona.scratch.name,

#                     target_persona.scratch.name,
#                     target_summ_idea, 
#                     target_persona.scratch.name,
#                     persona.scratch.name,

#                     persona.scratch.name]
#     return prompt_input
  
#   def __func_clean_up(gpt_response: PromptAgentChat, prompt=""):
#     print (gpt_response)

#     gpt_response = (prompt + gpt_response).split("Here is their conversation.")[-1].strip()
#     content = re.findall('"([^"]*)"', gpt_response)

#     speaker_order = []
#     for i in gpt_response.split("\n"): 
#       name = i.split(":")[0].strip() 
#       if name: 
#         speaker_order += [name]

#     ret = []
#     for count, speaker in enumerate(speaker_order): 
#       ret += [[speaker, content[count]]]

#     return ret

#   def __func_validate(gpt_response, prompt=""): 
#     try: 
#       __func_clean_up(gpt_response, prompt)
#       return True
#     except:
#       traceback.print_exc()
#       return False 

#   def get_fail_safe(): 
#     return "..."

#   # ChatGPT Plugin ===========================================================
#   def __chat_func_clean_up(gpt_response, prompt=""): ############
#     # ret = ast.literal_eval(gpt_response)

#     print ("DEBUG HERE (run_gpt_prompt_agent_chat)")
#     for row in gpt_response: 
#       print (row)

#     return gpt_response

#   def __chat_func_validate(gpt_response, prompt=""): ############
#     return True

#   gpt_param = {"engine": openai_config["model"], "max_tokens": 15, 
#                "temperature": 0, "top_p": 1, "stream": False,
#                "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
#   prompt_template = "persona/prompt_template/v3_ChatGPT/agent_chat_v1.txt" ########
#   prompt_input = create_prompt_input(persona, target_persona, curr_context, init_summ_idea, target_summ_idea)  ########
#   prompt = generate_prompt(prompt_input, prompt_template)
#   example_output = '[["Jane Doe", "Hi!"], ["John Doe", "Hello there!"] ... ]' ########
#   special_instruction = 'The output should be a list of list where the inner lists are in the form of ["<Name>", "<Utterance>"].' ########
#   fail_safe = get_fail_safe() ########
#   output = generate_structured_response(
#     prompt, 
#     gpt_param, 
#     PromptAgentChat, 
#     3, 
#     fail_safe,
#     __func_validate, 
#     __func_clean_up
#     )

#   if output != False: 
#     return output, [output, prompt, gpt_param, prompt_input, fail_safe]
#   # ChatGPT Plugin ===========================================================

#   # gpt_param = {"engine": openai_config["model"], "max_tokens": 2000, 
#   #              "temperature": 0.7, "top_p": 1, "stream": False,
#   #              "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
#   # prompt_template = "persona/prompt_template/v2/agent_chat_v1.txt"
#   # prompt_input = create_prompt_input(persona, target_persona, curr_context, init_summ_idea, target_summ_idea)
#   # prompt = generate_prompt(prompt_input, prompt_template)

#   # fail_safe = get_fail_safe()
#   # output = safe_generate_response(prompt, gpt_param, 5, fail_safe,
#   #                                  __func_validate, __func_clean_up)

#   # if debug or verbose: 
#   #   print_run_prompts(prompt_template, persona, gpt_param, 
#   #                     prompt_input, prompt, output)
  
#   # return output, [output, prompt, gpt_param, prompt_input, fail_safe]

# # =======================
# # =======================
# # =======================
# # =======================


def run_gpt_prompt_summarize_ideas(persona, statements, question, test_input=None, verbose=False):
  def create_prompt_input(persona, statements, question, test_input=None):
    prompt_input = [statements, persona.scratch.name, question]
    return prompt_input
  
  # def __func_clean_up(gpt_response: Idea_Summary, prompt=""):
  #   return gpt_response.idea_summary.strip()

  # def __func_validate(gpt_response, prompt=""): 
  #   try: 
  #     gpt_response = __func_clean_up(gpt_response, prompt)
  #     if gpt_response is None:
  #       return False
  #   except:
  #     traceback.print_exc()
  #     return False 
  #   return True

  def get_fail_safe(): 
    return "..."

  # ChatGPT Plugin ===========================================================
  def __chat_func_clean_up(gpt_response: IdeaSummary, prompt=""): ############
    return gpt_response.idea_summary.strip()

  def __chat_func_validate(gpt_response, prompt=""): ############
    try:
      response = __chat_func_clean_up(gpt_response, prompt)
      if response is None or response == "":
        return False
      return True
    except:
      traceback.print_exc()
      return False

  print ("DEBUG 16") ########
  gpt_param = {"engine": openai_config["model"], "max_tokens": 300,
               "temperature": 0, "top_p": 1, "stream": False,
               "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
  prompt_template = "persona/prompt_template/v3_ChatGPT/summarize_ideas_v1.txt" ########
  prompt_input = create_prompt_input(persona, statements, question)  ########
  prompt = generate_prompt(prompt_input, prompt_template)
  example_output = 'Jane Doe is working on a project' ########
  special_instruction = 'The output should be a string that responds to the question.' ########
  fail_safe = get_fail_safe() ########
  output = ChatGPT_safe_generate_structured_response(
    prompt,
    IdeaSummary,
    example_output,
    special_instruction,
    3,
    fail_safe,
    __chat_func_validate,
    __chat_func_clean_up,
    True,
  )

  if output != False:
    return output, [output, prompt, gpt_param, prompt_input, fail_safe]

  # ChatGPT Plugin ===========================================================

  # gpt_param = {"engine": openai_config["model"], "max_tokens": 150, 
  #              "temperature": 0.5, "top_p": 1, "stream": False,
  #              "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
  # prompt_template = "persona/prompt_template/v2/summarize_ideas_v1.txt"
  # prompt_input = create_prompt_input(persona, statements, question)
  # prompt = generate_prompt(prompt_input, prompt_template)

  # fail_safe = get_fail_safe()
  # output = safe_generate_response(prompt, gpt_param, 5, fail_safe,
  #                                  __func_validate, __func_clean_up)

  # if debug or verbose: 
  #   print_run_prompts(prompt_template, persona, gpt_param, 
  #                     prompt_input, prompt, output)
  
  # return output, [output, prompt, gpt_param, prompt_input, fail_safe]


class NextConversationLine(BaseModel):
  next_conversation_line: str

def run_gpt_prompt_generate_next_convo_line(persona, interlocutor_desc, prev_convo, retrieved_summary, test_input=None, verbose=False): 
  def create_prompt_input(persona, interlocutor_desc, prev_convo, retrieved_summary, test_input=None): 
    prompt_input = [persona.scratch.name, 
                    persona.scratch.get_str_iss(),
                    persona.scratch.name, 
                    interlocutor_desc, 
                    prev_convo, 
                    persona.scratch.name,
                    retrieved_summary, 
                    persona.scratch.name,]
    return prompt_input
  
  def __func_clean_up(gpt_response: NextConversationLine, prompt=""):
    return gpt_response.next_conversation_line

  def __func_validate(gpt_response, prompt=""): 
    try: 
      if not isinstance(gpt_response, NextConversationLine):
        return False
      __func_clean_up(gpt_response, prompt)
      return True
    except:
      traceback.print_exc()
      return False 

  def get_fail_safe(): 
    return "..."

  # # ChatGPT Plugin ===========================================================
  # def __chat_func_clean_up(gpt_response, prompt=""): ############
  #   return gpt_response.split('"')[0].strip()

  # def __chat_func_validate(gpt_response, prompt=""): ############
  #   try: 
  #     __func_clean_up(gpt_response, prompt)
  #     return True
  #   except:
  #     return False 

  # print ("asdhfapsh8p9hfaiafdsi;ldfj as DEBUG 15") ########
  # gpt_param = {"engine": openai_config["model"], "max_tokens": 15, 
  #              "temperature": 0, "top_p": 1, "stream": False,
  #              "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
  # prompt_template = "persona/prompt_template/v3_ChatGPT/generate_next_convo_line_v1.txt" ########
  # prompt_input = create_prompt_input(persona, interlocutor_desc, prev_convo, retrieved_summary)  ########
  # prompt = generate_prompt(prompt_input, prompt_template)
  # example_output = 'Hello' ########
  # special_instruction = 'The output should be a string that responds to the question. Again, only use the context included in the "Note" to generate the response' ########
  # fail_safe = get_fail_safe() ########
  # output = ChatGPT_safe_generate_response(prompt, example_output, special_instruction, 3, fail_safe,
  #                                         __chat_func_validate, __chat_func_clean_up, True)
  # if output != False: 
  #   return output, [output, prompt, gpt_param, prompt_input, fail_safe]
  # # ChatGPT Plugin ===========================================================

  gpt_param = {"engine": openai_config["model"], "max_tokens": 500,
               "temperature": 1, "top_p": 1, "stream": False,
               "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
  prompt_template = "persona/prompt_template/v2/generate_next_convo_line_v1.txt"
  prompt_input = create_prompt_input(persona, interlocutor_desc, prev_convo, retrieved_summary)
  prompt = generate_prompt(prompt_input, prompt_template)

  fail_safe = get_fail_safe()
  output = safe_generate_structured_response(
    prompt,
    gpt_param,
    NextConversationLine,
    5,
    fail_safe,
    __func_validate,
    __func_clean_up
  )
  if debug or verbose: 
    print_run_prompts(prompt_template, persona, gpt_param, 
                      prompt_input, prompt, output)
  
  return output, [output, prompt, gpt_param, prompt_input, fail_safe]


class InnerThought(BaseModel):
  thought: str

def run_gpt_prompt_generate_whisper_inner_thought(persona, whisper, test_input=None, verbose=False):
  def create_prompt_input(persona, whisper, test_input=None):
    prompt_input = [persona.scratch.name, whisper]
    return prompt_input

  def __func_clean_up(gpt_response: InnerThought, prompt=""):
    return gpt_response.thought.split('"')[0].strip()

  def __func_validate(gpt_response, prompt=""):
    try:
      __func_clean_up(gpt_response, prompt)
      return True
    except:
      traceback.print_exc()
      return False

  def get_fail_safe():
    return "..."

  gpt_param = {"engine": openai_config["model"], "max_tokens": 300,
               "temperature": 0, "top_p": 1, "stream": False,
               "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
  prompt_template = "persona/prompt_template/v2/whisper_inner_thought_v1.txt"
  prompt_input = create_prompt_input(persona, whisper)
  prompt = generate_prompt(prompt_input, prompt_template)

  fail_safe = get_fail_safe()
  output = safe_generate_structured_response(
    prompt,
    gpt_param,
    InnerThought,
    5,
    fail_safe,
    __func_validate,
    __func_clean_up,
    True,
  )

  if debug or verbose:
    print_run_prompts(prompt_template, persona, gpt_param,
                      prompt_input, prompt, output)
  
  return output, [output, prompt, gpt_param, prompt_input, fail_safe]


class PlanningThought(BaseModel):
  planning_thought: str

def run_gpt_prompt_planning_thought_on_convo(persona, all_utt, test_input=None, verbose=False):
  def create_prompt_input(persona, all_utt, test_input=None):
    prompt_input = [all_utt, persona.scratch.name, persona.scratch.name, persona.scratch.name]
    return prompt_input
  
  def __func_clean_up(gpt_response: PlanningThought, prompt=""):
    return gpt_response.planning_thought

  def __func_validate(gpt_response, prompt=""):
    try:
      if not isinstance(gpt_response, PlanningThought):
        return False
      __func_clean_up(gpt_response, prompt)
      return True
    except:
      traceback.print_exc()
      return False

  def get_fail_safe():
    return "..."

  gpt_param = {"engine": openai_config["model"], "max_tokens": 300,
               "temperature": 0, "top_p": 1, "stream": False,
               "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
  prompt_template = "persona/prompt_template/v2/planning_thought_on_convo_v1.txt"
  prompt_input = create_prompt_input(persona, all_utt)
  prompt = generate_prompt(prompt_input, prompt_template)

  fail_safe = get_fail_safe()
  output = safe_generate_structured_response(
    prompt,
    gpt_param,
    PlanningThought,
    5,
    fail_safe,
    __func_validate,
    __func_clean_up,
  )

  if debug or verbose: 
    print_run_prompts(prompt_template, persona, gpt_param,
                      prompt_input, prompt, output)
  
  return output, [output, prompt, gpt_param, prompt_input, fail_safe]


class ConvoTakeaways(BaseModel):
  takeaway: str

def run_gpt_prompt_memo_on_convo(persona, all_utt, test_input=None, verbose=False):
  def create_prompt_input(persona, all_utt, test_input=None):
    prompt_input = [all_utt, persona.scratch.name, persona.scratch.name, persona.scratch.name]
    return prompt_input
  
  # def __func_clean_up(gpt_response, prompt=""):
  #   return gpt_response.split('"')[0].strip()

  # def __func_validate(gpt_response, prompt=""):
  #   try:
  #     __func_clean_up(gpt_response, prompt)
  #     return True
  #   except:
  #     traceback.print_exc()
  #     return False

  def get_fail_safe(): 
    return "..."

  # ChatGPT Plugin ===========================================================
  def __chat_func_clean_up(gpt_response: ConvoTakeaways, prompt=""): ############
    return gpt_response.takeaway

  def __chat_func_validate(gpt_response, prompt=""): ############
    try: 
      if not isinstance(gpt_response, ConvoTakeaways):
        return False
      __chat_func_clean_up(gpt_response, prompt)
      return True
    except:
      traceback.print_exc()
      return False 

  print ("DEBUG 15") ########
  gpt_param = {"engine": openai_config["model"], "max_tokens": 300,
               "temperature": 0, "top_p": 1, "stream": False,
               "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
  prompt_template = "persona/prompt_template/v3_ChatGPT/memo_on_convo_v1.txt" ########
  prompt_input = create_prompt_input(persona, all_utt)  ########
  prompt = generate_prompt(prompt_input, prompt_template)
  example_output = 'Jane Doe was interesting to talk to.' ########
  special_instruction = 'The output should ONLY contain a string that summarizes anything interesting that the agent may have noticed' ########
  fail_safe = get_fail_safe() ########
  output = ChatGPT_safe_generate_structured_response(
    prompt,
    ConvoTakeaways,
    example_output,
    special_instruction,
    3,
    fail_safe,
    __chat_func_validate,
    __chat_func_clean_up,
    True
  )
  if output != False: 
    return output, [output, prompt, gpt_param, prompt_input, fail_safe]
  # ChatGPT Plugin ===========================================================

  gpt_param = {"engine": openai_config["model"], "max_tokens": 300,
               "temperature": 0, "top_p": 1, "stream": False,
               "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
  prompt_template = "persona/prompt_template/v2/memo_on_convo_v1.txt"
  prompt_input = create_prompt_input(persona, all_utt)
  prompt = generate_prompt(prompt_input, prompt_template)

  fail_safe = get_fail_safe()
  output = safe_generate_structured_response(
    prompt,
    gpt_param,
    ConvoTakeaways,
    5,
    fail_safe,
    __chat_func_validate,
    __chat_func_clean_up,
  )

  if debug or verbose: 
    print_run_prompts(prompt_template, persona, gpt_param, 
                      prompt_input, prompt, output)
  
  return output, [output, prompt, gpt_param, prompt_input, fail_safe]


class SafetyScore(BaseModel):
  # Safety score should range 1-10
  safety_score: int

def run_gpt_generate_safety_score(persona, comment, test_input=None, verbose=False):
  def create_prompt_input(comment, test_input=None):
    prompt_input = [comment]
    return prompt_input

  def __chat_func_clean_up(gpt_response: SafetyScore, prompt=""):
    score = gpt_response.safety_score
    if isinstance(score, int) and 1 <= score <= 10:
      return score
    raise ValueError("Output is not a valid integer between 1 and 10")

  def __chat_func_validate(gpt_response, prompt=""):
    try:
      __chat_func_clean_up(gpt_response)
    except:
      traceback.print_exc()
      return False

  def get_fail_safe():
    return None

  print ("11")
  prompt_template = "persona/prompt_template/safety/anthromorphosization_v1.txt"
  prompt_input = create_prompt_input(comment)
  print ("22")
  prompt = generate_prompt(prompt_input, prompt_template)
  print (prompt)
  fail_safe = get_fail_safe()
  output = ChatGPT_safe_generate_structured_response(
    prompt,
    SafetyScore,
    repeat=3,
    fail_safe_response=fail_safe,
    func_validate=__chat_func_validate,
    func_clean_up=__chat_func_clean_up,
    verbose=verbose,
  )
  print(output)

  gpt_param = {"engine": openai_config["model"], "max_tokens": 100,
               "temperature": 0, "top_p": 1, "stream": False,
               "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
  return output, [output, prompt, gpt_param, prompt_input, fail_safe]


def extract_first_json_dict(data_str):
  # Find the first occurrence of a JSON object within the string
  start_idx = data_str.find('{')
  end_idx = data_str.find('}', start_idx) + 1

  # Check if both start and end indices were found
  if start_idx == -1 or end_idx == 0:
    return None

  # Extract the first JSON dictionary
  json_str = data_str[start_idx:end_idx]

  try:
    # Attempt to parse the JSON data
    json_dict = json.loads(json_str)
    return json_dict
  except json.JSONDecodeError:
    traceback.print_exc()
    # If parsing fails, return None
    return None


class ChatUtterance(BaseModel):
  utterance: str
  did_conversation_end: bool

def run_gpt_generate_iterative_chat_utt(
  maze,
  init_persona,
  target_persona,
  retrieved,
  curr_context,
  curr_chat,
  test_input=None,
  verbose=False,
):
  def create_prompt_input(
    maze,
    init_persona,
    target_persona,
    retrieved,
    curr_context,
    curr_chat,
    test_input=None,
  ):
    persona = init_persona
    prev_convo_insert = "\n"
    if persona.a_mem.seq_chat:
      for i in persona.a_mem.seq_chat:
        if i.object == target_persona.scratch.name:
          v1 = int(
            (persona.scratch.curr_time - i.created).total_seconds() / 60
          )
          prev_convo_insert += f"{str(v1)} minutes ago, {persona.scratch.name} and {target_persona.scratch.name} were already {i.description} This context takes place after that conversation."
          break
    if prev_convo_insert == "\n":
      prev_convo_insert = ""
    if persona.a_mem.seq_chat:
      if (
        int(
          (
            persona.scratch.curr_time - persona.a_mem.seq_chat[-1].created
          ).total_seconds()
          / 60
        )
        > 480
      ):
        prev_convo_insert = ""
    print(prev_convo_insert)

    curr_sector = f"{maze.access_tile(persona.scratch.curr_tile)['sector']}"
    curr_arena = f"{maze.access_tile(persona.scratch.curr_tile)['arena']}"
    curr_location = f"{curr_arena} in {curr_sector}"

    retrieved_str = ""
    for key, vals in retrieved.items():
      for v in vals:
        retrieved_str += f"- {v.description}\n"

    convo_str = ""
    for i in curr_chat:
      convo_str += ": ".join(i) + "\n"
    if convo_str == "":
      convo_str = "[The conversation has not started yet -- start it!]"

    init_iss = f"Here is Here is a brief description of {init_persona.scratch.name}.\n{init_persona.scratch.get_str_iss()}"
    prompt_input = [
      init_iss,
      init_persona.scratch.name,
      retrieved_str,
      prev_convo_insert,
      curr_location,
      curr_context,
      init_persona.scratch.name,
      target_persona.scratch.name,
      convo_str,
      init_persona.scratch.name,
      target_persona.scratch.name,
    ]
    return prompt_input

  def __chat_func_clean_up(gpt_response: ChatUtterance, prompt=""):
    cleaned_dict = {
      "utterance": gpt_response.utterance,
      "end": gpt_response.did_conversation_end,
    }
    return cleaned_dict

  def __chat_func_validate(gpt_response, prompt=""):
    try:
      if not isinstance(gpt_response, ChatUtterance):
        return False
      return True
    except:
      traceback.print_exc()
      return False

  def get_fail_safe():
    cleaned_dict = {
      "utterance": "...",
      "end": False,
    }
    return cleaned_dict

  print("11")
  prompt_template = "persona/prompt_template/v3_ChatGPT/iterative_convo_v1.txt"
  prompt_input = create_prompt_input(
    maze, init_persona, target_persona, retrieved, curr_context, curr_chat
  )
  print("22")
  prompt = generate_prompt(prompt_input, prompt_template)
  print(prompt)
  fail_safe = get_fail_safe()
  output = ChatGPT_safe_generate_structured_response(
    prompt,
    ChatUtterance,
    repeat=3,
    fail_safe_response=fail_safe,
    func_validate=__chat_func_validate,
    func_clean_up=__chat_func_clean_up,
    verbose=verbose,
  )
  print(output)

  gpt_param = {
    "engine": openai_config["model"],
    "max_tokens": 4096,
    "temperature": 0,
    "top_p": 1,
    "stream": False,
    "frequency_penalty": 0,
    "presence_penalty": 0,
    "stop": None,
  }

  return output, [output, prompt, gpt_param, prompt_input, fail_safe]


# Takes a plugin prompt template filepath and returns an LLM response string
def run_plugin(
  plugin_template,
  current_movements,
  personas,
  verbose=False,
):
  def create_prompt_input(
    persona1,
    persona2,
    movements,
    test_input=None,
  ):
    if test_input:
      return test_input

    game_state = copy.deepcopy(movements)
    personas = game_state["persona"]
    for persona in personas:
      persona_state = personas[persona]
      del persona_state["chat"]
      personas[persona] = persona_state
    game_state["persona"] = personas

    conversation = list(movements["persona"].values())[0]["chat"]

    prompt_input = [
      persona1.scratch.get_str_learned(),
      persona2.scratch.get_str_learned(),
      game_state,
      conversation,
      persona1.scratch.get_str_firstname(),
      persona2.scratch.get_str_firstname(),
    ]

    return prompt_input

  def __chat_func_clean_up(gpt_response, prompt=""):
    gpt_response = extract_first_json_dict(gpt_response)
    cleaned_dict = dict()

    for key, val in gpt_response.items():
      cleaned_dict[key] = False

      if "t" in str(val) or "T" in str(val):
        cleaned_dict[key] = True

    return cleaned_dict

  def __chat_func_validate(gpt_response, prompt=""):
    print("Validating...")

    try:
      print(extract_first_json_dict(gpt_response))
      return True
    except:
      traceback.print_exc()
      return False

  def get_fail_safe():
    cleaned_dict = {"error": "error"}
    return cleaned_dict

  persona_list = list(personas.values())

  prompt_input = create_prompt_input(
    persona1=persona_list[0],
    persona2=persona_list[1],
    movements=current_movements,
  )
  prompt = generate_prompt(prompt_input, plugin_template)
  print(prompt)
  fail_safe = get_fail_safe()
  output = ChatGPT_safe_generate_response(
    prompt,
    repeat=3,
    fail_safe_response=fail_safe,
    func_validate=__chat_func_validate,
    func_clean_up=__chat_func_clean_up,
    verbose=verbose,
  )
  print(output)

  gpt_param = {
    "engine": openai_config["model"],
    "max_tokens": 4096,
    "temperature": 0,
    "top_p": 1,
    "stream": False,
    "frequency_penalty": 0,
    "presence_penalty": 0,
    "stop": None,
  }

  return output, [output, prompt, gpt_param, prompt_input, fail_safe]
