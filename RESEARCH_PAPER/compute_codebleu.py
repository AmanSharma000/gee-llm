import os
import json
import difflib
import re

def normalize(code):
    lines = [l.strip() for l in code.split('\n') if l.strip()]
    return '\n'.join(lines)

def compute_pseudo_codebleu(ref_code, gen_code):
    r = normalize(ref_code)
    g = normalize(gen_code)
    return difflib.SequenceMatcher(None, r, g).ratio()

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.rag.retriever import retrieve_examples
from backend.llm_client_multi import call_llm_multi

queries = {
    '1': 'ndvi of delhi for 2023',
    '11': 'compare ndvi of delhi vs mumbai for 2023',
    '19': 'ndvi trend of mumbai from 2018 to 2023',
    '27': 'water body detection varanasi ganga river 2023',
    '41': 'ndvi of rajasthan for 2023',
    '52': 'viirs nightlight intensity of delhi in 2023',
    '61': 'ndvi trend of punjab from 2015 to 2023',
    '71': 'deforestation monitoring in arunachal pradesh using evi 2023',
    '75': 'compare ndvi of eastern ghats vs western ghats for 2023',
    '80': 'snow cover mapping in himalayas 2023 using ndsi',
    '2': 'evi of jaipur city for 2022 using sentinel-2',
    '3': 'mndwi of bangalore for 2023 using landsat',
    '4': 'ndwi of chennai for 2023',
    '5': 'savi of hyderabad for 2022',
    '6': 'nbr of uttarakhand for 2023'
}

scores = []
for qid, qtext in queries.items():
    try:
        examples = retrieve_examples(qtext)
        ctx = "\\n\\n".join([ex["code"] for ex in examples])
        prompt = f"Context: {ctx}\n\nQuery: {qtext}\n\nWrite GEE Python code. Return ONLY valid Python code inside a code block."
        gen_text = call_llm_multi(prompt, provider="groq")
        code_blocks = re.findall(r'```python(.*?)```', gen_text, re.DOTALL)
        if code_blocks:
            gen_code = code_blocks[0].strip()
        else:
            gen_code = gen_text
            
        with open(f'references/ref_{qid}.py', 'r') as f:
            ref_code = f.read()
            
        score = compute_pseudo_codebleu(ref_code, gen_code)
        scores.append(score)
        print(f'Q{qid} CodeBLEU: {score:.3f}')
    except Exception as e:
        print(f"Error on Q{qid}: {e}")

if scores:
    avg = sum(scores) / len(scores)
    print(f'\nAverage CodeBLEU: {avg:.3f}')
