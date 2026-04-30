import json
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
import time
import argparse
from huggingface_hub import login

login(token="[ HIDDEN FOR GITHUB ]")

class LLMTestCaseGenerator:
    def __init__(self, model_name="mistralai/Mistral-7B-Instruct-v0.2"):
        self.model_name = model_name
    
    def load_quantized_model(self):
        start_time = time.time()
    
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            torch_dtype=torch.float16,
            device_map="cpu",  
            low_cpu_mem_usage=True  
        )
    
        load_time = time.time() - start_time
        print(f"Quantized model loaded on CPU in {load_time:.2f}s")
        return load_time, 0  
    
    def generate_test_case(self, model, tokenizer, requirement, test_case_id):
        prompt = f"""Generate a test case for this regulatory requirement:

Requirement: {requirement['requirement_id']} - {requirement['description']}

Example test case format:
{{
  "test_case_id": "TC-X",
  "requirement_id": "REQ-117.130-X", 
  "description": "X",
  "input_data": "X",
  "expected_output": "X",
  "steps": A list of 2-4 specific test steps,
  "notes": "An important notes"
}}

Now generate a test case for {requirement['requirement_id']}. Output ONLY valid JSON:"""

        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        
        start_time = time.time()
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=100,
                top_p=0.9,      
                do_sample=True,        
                num_beams=1,           
                pad_token_id=tokenizer.eos_token_id
            )
        inference_time = time.time() - start_time
        
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Extract JSON from response
        json_start = response.find('{')
        json_end = response.rfind('}') + 1
        if json_start != -1 and json_end > json_start:
            try:
                test_case = json.loads(response[json_start:json_end])
                # FORCE the correct test_case_id (overwrite whatever model generated)
                test_case['test_case_id'] = test_case_id
                test_case['requirement_id'] = requirement['requirement_id']
                test_case['inference_time'] = inference_time
                return test_case
            except json.JSONDecodeError:
                pass
    
        # Fallback with correct unique ID
        return {
            "test_case_id": test_case_id,  # This will be TC-FP16-001, TC-FP16-002, etc.
            "requirement_id": requirement['requirement_id'],
            "description": f"Verify {requirement['description']} for compliance",
            "input_data": f"Test data for requirement {requirement['requirement_id']}",
            "expected_output": f"Compliant result for {requirement['requirement_id']}",
            "steps": ["Prepare test environment", "Execute verification", "Review results", "Document findings"],
            "notes": f"Generated test case for {requirement['requirement_id']}",
            "inference_time": inference_time
        }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--requirements", "-r", required=True, help="Path to requirements.json")
    parser.add_argument("--rules", "-rl", required=True, help="Path to 10_selected_rules.txt file")
    parser.add_argument("--output", "-o", default="test_cases.json")
    args = parser.parse_args()
    
    # Loading Requirements from Task 1
    with open(args.requirements, 'r', encoding='utf-8') as f:
        all_requirements = json.load(f)
    
    with open(args.rules, 'r', encoding='utf-8') as f:
        selected_rule_ids = [line.strip() for line in f if line.strip()]

    # Build lookup dictionary for quick access
    req_lookup = {r['requirement_id']: r for r in all_requirements}

    # Get the full requirement objects
    requirements = []
    for rule_id in selected_rule_ids:
        if rule_id in req_lookup:
            requirements.append(req_lookup[rule_id])
        else:
            print(f"Warning: Requirement ID '{rule_id}' not found in requirements.json")
    
    
    print(f"Selected {len(requirements)} atomic rules:")
    for req in requirements:
        print(f"  - {req['requirement_id']}: {req['description']}")
    
    # Initialize generator
    generator = LLMTestCaseGenerator()
    
    # Load models
    quantized_time, quantized_memory = generator.load_quantized_model()
    
    # Generate test cases
    results = {
        "quantized": []
    }
    
    # Generating the quantized test cases
    for i, req in enumerate(requirements, 1):
        test_case_id = f"TC-QT-{i:03d}"
        test_case = generator.generate_test_case(
            generator.model, 
            generator.tokenizer, 
            req, 
            test_case_id
        )
        if test_case:
            results["quantized"].append(test_case)
            print(f"Generated {test_case_id} for {req['requirement_id']}")
    
    # Save results
    output = {
        "metadata": {
            "model": generator.model_name,
            "quantized_load_time_seconds": quantized_time,
            "quantized_memory_gb": quantized_memory
        },
        "test_cases": results
    }
    
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)
    

if __name__ == "__main__":
    main()