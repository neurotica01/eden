"""
Author: Joon Sung Park (joonspk@stanford.edu)

File: print_prompt.py
Description: For printing prompts when the setting for verbose is set to True.
"""

##############################################################################
#                    PERSONA Chapter 1: Prompt Structures                    #
##############################################################################


from global_methods import log
def print_run_prompts(
    prompt_template=None,
    persona=None,
    gpt_param=None,
    prompt_input=None,
    prompt=None,
    output=None,
):
    log(f"=== {prompt_template}", tee_to_console=True)
    log("~~~ persona    ---------------------------------------------------")
    log(persona.name if persona else "None")
    log("~~~ gpt_param ----------------------------------------------------")
    log(gpt_param)
    log("~~~ prompt_input    ----------------------------------------------")
    log(prompt_input)
    log("~~~ prompt    ----------------------------------------------------")
    log(prompt)
    log("~~~ processed final output    ----------------------------------------------------")
    log(output, tee_to_console=True)
    log("=== END ==========================================================")
    log("\n\n\n")
