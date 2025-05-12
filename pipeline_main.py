import os
from datetime import datetime

import pandas as pd
from langchain_openai import OpenAI
from langchain_openai import ChatOpenAI

from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory


def run_pipeline(models_folder, output_folder, combined_output_csv, api_key):
    """
        Iterate over BPMN prompts, cross-examine the LLM and write per-process and combined results to CSV.
    """
    #Initialize the LLM
    llm = ChatOpenAI(model="<YOUR MODEL>", temperature=0, openai_api_key=api_key)

    #Results storage
    combined_results = []

    #Iterate through all levels within the models/main/ folder
    main_folder = os.path.join(models_folder, "anonymized")  # -type testing
    for level_name in os.listdir(main_folder):
        level_path = os.path.join(main_folder, level_name)
        if os.path.isdir(level_path):
            print(f"Processing level: {level_name}")

            #Iterate through all processes in the current level
            for process_name in os.listdir(level_path):
                process_path = os.path.join(level_path, process_name)
                if os.path.isdir(process_path):
                    print(f"Processing process: {process_name}")

                    #Memory for combined
                    process_output = []

                    #process-specific questions
                    questions_file = os.path.join(process_path, "questions.csv")
                    if not os.path.exists(questions_file):
                        print(f"Questions file {questions_file} does not exist. Skipping process.")
                        continue

                    questions_df = pd.read_csv(questions_file, sep=';')

                    #Prompts
                    prompts_folder = os.path.join(process_path, "prompts")
                    if not os.path.exists(prompts_folder):
                        print(f"Prompts folder {prompts_folder} does not exist. Skipping process.")
                        continue

                    for prompt_type in ["raw", "simplified", "humanified", "dfg"]:
                        prompt_file = os.path.join(prompts_folder, f"{prompt_type}.txt")
                        if not os.path.exists(prompt_file):
                            print(f"Prompt file {prompt_file} does not exist. Skipping.")
                            continue

                        #Read prompt
                        with open(prompt_file, 'r') as f:
                            prompt_text = f.read()

                        #Initialize new conversation chain with new memory
                        memory = ConversationBufferMemory()
                        conversation = ConversationChain(llm=llm, memory=memory)

                        #Combine start prompt with the specific type of prompt
                        starting_prompt = f"""You are a BPMN (Business Process Model and Notation) expert. I will give you a textual BPMN process description.
                                                Your task is to read and fully understand it. After that, I will ask you YES/NO questions.
                                                For each following question, you can only answer "YES" or "NO" — no explanations, no extra words. Just the single word.
                                                If you fully understand this instruction and are ready to receive the BPMN description, reply with "GO".
                                                Now, here's the BPMN description: {prompt_text}"""

                        # Initialize session
                        prompt = PromptTemplate(input_variables=["input"], template="{input}")
                        chain = prompt | llm

                        #Send starting prompt
                        response = conversation.run(input=starting_prompt)

                        print(response)
                        if "GO" in response:
                            #Begin asking questions if LLM replies "GO"
                            for _, question_row in questions_df.iterrows():
                                question_text = question_row['question_text']
                                ground_truth = question_row['ground_truth']
                                question_group = question_row['question_group']

                                # Ask the question
                                llm_response = conversation.run(input=question_text).strip()

                                print(llm_response)

                                #results
                                is_correct = (llm_response.upper() == ground_truth.upper())
                                process_output.append({
                                    "prompt_type": prompt_type,
                                    "bpmn_model_id": process_name,
                                    "difficulty_level": level_name,
                                    "model_type": "process",
                                    "question_group": question_group,  #From the CSV
                                    "question_text": question_text,
                                    "llm_answer": llm_response,
                                    "ground_truth": ground_truth,
                                    "is_correct": is_correct
                                })
                        else:
                            print(f"LLM did not reply GO for {prompt_type} in {process_name}")

                    #Save process results
                    process_output_path = os.path.join(output_folder, level_name)
                    os.makedirs(process_output_path, exist_ok=True)
                    output_file = os.path.join(process_output_path, f"{process_name}_output.csv")
                    process_df = pd.DataFrame(process_output)
                    process_df.to_csv(output_file, index=False)

                    #Add process's results to the combined results
                    combined_results.extend(process_output)

    #Save results
    combined_output_path = os.path.join(output_folder, combined_output_csv)
    combined_df = pd.DataFrame(combined_results)
    combined_df.to_csv(combined_output_path, index=False)
    print(f"Pipeline completed. Combined results saved at {combined_output_path}")


if __name__ == "__main__":
    OPENAI_API_KEY = "<YOUR API KEY>"

    #Paths
    models_folder = "models"
    output_folder = "outputs"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    output_csv_path = f"combined_output_{timestamp}.csv"

    os.makedirs(output_folder, exist_ok=True)

    #Run the pipeline
    run_pipeline(models_folder, output_folder, output_csv_path, OPENAI_API_KEY)
