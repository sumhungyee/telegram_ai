import copy
from app.utils import *
from duckduckgo_search import DDGS


def decide_websearch(llm_model, query):

    start = time.time()
    logger.info("Begin websearch routing")
    sys_prompt = [{
        "role": "system", "content": f"""You are an expert at routing a query to a web search or the generation stage, where an AI will simply generate a reply.
        The query is given here:\n{query}
        Use the web search for questions that require more context for a better answer, or recent events.
        Give a binary choice "web_search" or "generate" based on the question. 
        Return a JSON object (dictionary) with a single key "choice" and the value "web_search" or "generate" within a code chunk.
        Please adhere to the format below strictly:
        ```json
        {{"choice": "generate"}}
        ```
        """
    }]
    
    stringified_conversation = llm_model.apply_prompt_template(sys_prompt, role="assistant")
    input_ids = llm_model.tokenizer.encode(stringified_conversation)
    truncated_input_ids, _ = truncate_conversation(input_ids, sys_prompt, llm_model)

    try:
        output = try_parse(generate_quick, llm=llm_model, input_ids=truncated_input_ids, max_new_tokens=30)
        logger.info(f"Websearch routing output {output} finished in {round(time.time() - start, 3)}")
        return output['choice'] == "web_search"
    except Exception as e:
        logger.error("Error while routing! Error: {e}")
        return False
        
def perform_websearch(llm_model, query):
    ddgs = DDGS()
    logger.info("Begin keyword generation")
    start = time.time()
    sys_prompt = [{
        "role": "system", "content": f"""You are an expert at generating google search terms for a given question/topic. 
        These search terms will be used to search the internet for more information about the question/topic.
        Return a JSON array of at most 2 search terms in a code chunk. Your reply should adhere to the format in the example below.
        Example:
        ```json
        ["Oxynase", "What is Oxymetazoline"]
        ```
        The question/topic is given here: {query}
        """
    }]
    stringified_conversation = llm_model.apply_prompt_template(sys_prompt, role="assistant")
    input_ids = llm_model.tokenizer.encode(stringified_conversation)
    truncated_input_ids, _ = truncate_conversation(input_ids, sys_prompt, llm_model)

    try:
        output = try_parse(generate_quick, llm=llm_model, input_ids=truncated_input_ids, max_new_tokens=30)
        logger.info(f"Websearch terms {output} finished in {round(time.time() - start, 3)}")
        results = []
        for term in output:
            result = ddgs.text(term, max_results=3)
            results.extend(result)
        return format_results(results)
    except Exception as e:
        logger.error("Error while searching! Error: {e}")
        return ""


def format_results(results: list):
    return "\n\n".join([x['href'] + '\n' + x['body'] for x in results])
    
def search_generate_pipeline(llm, conversation):
    adapted_conversation = copy.deepcopy(conversation)
    query = adapted_conversation[-1]["content"]
    do_generate = decide_websearch(llm, query)
    if do_generate:
        results = perform_websearch(llm, query)
    else:
        results = ""

    if results:
        adapted_conversation[-1]["content"] = f"""{query}\n\nPretend you performed a search over the and obtained the following results. \
            you may or may not choose to use them in your answer. Reference links (write down the URLs) used in your reply with footnotes.\n\n{results}"""
    return adapted_conversation